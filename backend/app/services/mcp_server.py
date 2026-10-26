"""M3: MCP Server（FastMCP）— 知识库对外 MCP 服务。

- 只读工具与 LangGraph agent 共享同一份 @tool 定义（统一工具层，不重复维护）
- Phase 4: 工具权限三级 + 注解 + dry-run —— 只读直接暴露、写操作需显式开启、
  未登记工具一律不暴露（见 services/tools/permissions.py）
- 挂载到 FastAPI /mcp 端点（Streamable HTTP），见 app.main
- API Key 认证：Authorization: Bearer <MCP_API_KEY>（纯 ASGI 中间件，不缓冲流式响应）
"""

import json
import secrets
from typing import Optional

from starlette.responses import JSONResponse

from app.core.config import settings


class MCPAuthMiddleware:
    """MCP /mcp 端点的 API Key 认证中间件（纯 ASGI 实现）。

    - 校验 Authorization: Bearer <MCP_API_KEY> 请求头（timing-safe 比较）
    - MCP_API_KEY 未配置时拒绝所有请求（fail-closed：无认证 = 私密笔记裸奔，设计文档 P7）
    - 用纯 ASGI 而非 BaseHTTPMiddleware，避免对 Streamable HTTP 的 SSE 流式响应产生缓冲干扰
    """

    def __init__(self, app, api_key: str):
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self._is_mcp_path(scope.get("path", "")):
            if not self._is_authorized(scope.get("headers", [])):
                response = JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "MCP 认证失败：请在请求头携带 Authorization: Bearer <MCP_API_KEY>",
                        },
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    def _is_mcp_path(path: str) -> bool:
        return path == "/mcp" or path.startswith("/mcp/")

    def _is_authorized(self, headers: list) -> bool:
        if not self.api_key:
            return False
        auth_header = None
        for key, value in headers:
            if key == b"authorization":
                auth_header = value.decode("latin-1")
                break
        if not auth_header:
            return False
        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer":
            return False
        return secrets.compare_digest(token.strip(), self.api_key)


def mcp_create_note(title: str, content: str, folder_id: Optional[str] = None) -> str:
    """创建一篇知识库笔记(MCP 写权限已开启)。归属 MCP_WRITE_USER_ID 对应的用户。"""
    from app.services.tools import create_note
    from app.services.tools.context import ToolContext, reset_tool_context, set_tool_context

    token = set_tool_context(
        ToolContext(user_id=settings.MCP_WRITE_USER_ID, session_id="mcp")
    )
    try:
        return create_note.func(title, content, folder_id)
    finally:
        reset_tool_context(token)


def mcp_create_note_dry_run(
    title: str, content: str, folder_id: Optional[str] = None
) -> str:
    """dry-run:只回写入预览,不落库。

    默认开启(MCP_DRY_RUN=True):写权限是一次性放开还是长期放开,应该由人看过
    "到底会写什么"再决定,而不是先写进去再发现格式不对。
    """
    return json.dumps(
        {
            "dry_run": True,
            "would_create": {
                "title": (title or "").strip()[:500],
                "content_preview": (content or "")[:500],
                "folder_id": folder_id,
            },
            "hint": "MCP_DRY_RUN 已开启,未写入知识库;确认预览无误后关闭该开关才会真正创建。",
        },
        ensure_ascii=False,
    )


def _register_read_tools(mcp) -> list:
    """按权限表注册只读工具,返回实际注册的名字(供 instructions 动态生成)。"""
    from app.services.tools import (
        get_graph_neighbors,
        get_note,
        list_folders,
        list_tags,
        search_notes,
        web_search,
    )
    from app.services.tools.permissions import should_register_on_mcp, tool_annotations

    read_tools = (
        search_notes,
        get_note,
        get_graph_neighbors,
        list_tags,
        list_folders,
        web_search,
    )
    registered = []
    for lc_tool in read_tools:
        if not should_register_on_mcp(
            lc_tool.name, enable_write=False, has_write_user=False
        ):
            continue
        mcp.tool(lc_tool.func, annotations=tool_annotations(lc_tool.name))
        registered.append(lc_tool.name)
    return registered


def create_mcp_server():
    """创建 FastMCP 实例:只读工具常驻,写工具按权限开关选择性注册。"""
    from fastmcp import FastMCP

    from app.services.tools.permissions import should_register_on_mcp, tool_annotations

    mcp = FastMCP(
        name="zhishuxingtu-knowledge-base",
        instructions=(
            "知枢星图个人知识库。用 search_notes 检索笔记（混合检索：向量+BM25+重排序），"
            "get_note 读取笔记全文（前2000字），get_graph_neighbors 查询笔记间的双向链接关系，"
            "list_tags / list_folders 浏览标签与文件夹组织结构，"
            "web_search 联网搜索知识库外的时效性信息（Tavily，需配置 key）。"
        ),
    )

    registered = _register_read_tools(mcp)

    write_user = (settings.MCP_WRITE_USER_ID or "").strip()
    if should_register_on_mcp(
        "create_note",
        enable_write=bool(settings.MCP_ENABLE_WRITE),
        has_write_user=bool(write_user),
    ):
        fn = mcp_create_note_dry_run if settings.MCP_DRY_RUN else mcp_create_note
        mcp.tool(
            fn,
            name="create_note",
            annotations=tool_annotations("create_note"),
        )
        registered.append("create_note")

    mode = "只读" if "create_note" not in registered else (
        "写入演练(dry-run)" if settings.MCP_DRY_RUN else "写入"
    )
    mcp.instructions = (
        (mcp.instructions or "")
        + f"\n当前暴露工具:{'、'.join(registered)};权限模式:{mode}。"
    )
    return mcp
