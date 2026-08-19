"""M3: MCP Server（FastMCP）— 知识库对外 MCP 服务。

- 6 个只读工具与 LangGraph agent 共享同一份 @tool 定义（统一工具层，不重复维护）
- 挂载到 FastAPI /mcp 端点（Streamable HTTP），见 app.main
- API Key 认证：Authorization: Bearer <MCP_API_KEY>（纯 ASGI 中间件，不缓冲流式响应）
"""

import secrets

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


def create_mcp_server():
    """创建 FastMCP 实例并注册与 agent 共享的 6 个只读工具。"""
    from fastmcp import FastMCP

    from app.services.tools import (
        get_graph_neighbors,
        get_note,
        list_folders,
        list_tags,
        search_notes,
        web_search,
    )

    mcp = FastMCP(
        name="zhishuxingtu-knowledge-base",
        instructions=(
            "知枢星图个人知识库。用 search_notes 检索笔记（混合检索：向量+BM25+重排序），"
            "get_note 读取笔记全文（前2000字），get_graph_neighbors 查询笔记间的双向链接关系，"
            "list_tags / list_folders 浏览标签与文件夹组织结构，"
            "web_search 联网搜索知识库外的时效性信息（Tavily，需配置 key）。所有工具均为只读。"
        ),
    )

    # 统一工具层：注册 LangChain @tool 的底层原始函数（lc_tool.func），
    # 工具签名/文档与 agent 完全同源，避免双份维护。
    for lc_tool in (search_notes, get_note, get_graph_neighbors, list_tags, list_folders, web_search):
        mcp.tool(lc_tool.func)

    return mcp
