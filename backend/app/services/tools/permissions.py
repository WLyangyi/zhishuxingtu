# -*- coding: utf-8 -*-
"""Phase 4:工具权限三级 + MCP 暴露策略。

为什么要一张显式策略表,而不是在 MCP 里逐个手写工具名:
"哪些工具能对外"是安全边界,不是便利函数。散落在注册代码里的工具名,
新增工具时很容易被顺手加进去;集中成表之后,未登记的工具一律按最危险处理
(unknown → dangerous → 不暴露),新增工具必须先表态。
"""

from dataclasses import dataclass
from typing import Dict

READ = "read"          # 只读,无副作用
WRITE = "write"        # 有副作用(写库),默认不对外
DANGEROUS = "dangerous"  # 破坏性/未登记,永不对外


@dataclass(frozen=True)
class ToolPolicy:
    level: str
    mcp_exposed: bool = True   # 是否允许通过 MCP 暴露(会话绑定工具不可)
    open_world: bool = False   # 是否访问外部世界(联网搜索)


TOOL_POLICIES: Dict[str, ToolPolicy] = {
    "search_notes": ToolPolicy(READ),
    "get_note": ToolPolicy(READ),
    "get_graph_neighbors": ToolPolicy(READ),
    "list_tags": ToolPolicy(READ),
    "list_folders": ToolPolicy(READ),
    # 联网出站,但对知识库本身只读
    "web_search": ToolPolicy(READ, open_world=True),
    # 会话绑定的存档取回:换到 MCP 没有 session_id,读了也只会报错,故不对外
    "read_tool_artifact": ToolPolicy(READ, mcp_exposed=False),
    # 写操作:默认不对外,需 MCP_ENABLE_WRITE + MCP_WRITE_USER_ID
    "create_note": ToolPolicy(WRITE),
}


def policy_for(name: str) -> ToolPolicy:
    """未登记的工具按 dangerous 处理(fail-closed)。"""
    return TOOL_POLICIES.get(name, ToolPolicy(DANGEROUS, mcp_exposed=False))


def tool_annotations(name: str) -> dict:
    """按 MCP ToolAnnotations 的四个 hint 描述工具语义。

    destructiveHint 与 readOnlyHint 互补:未登记的 dangerous 工具同时标
    readOnly=False / destructive=True,客户端据此可以选择二次确认或直接拒绝。
    """
    policy = policy_for(name)
    read_only = policy.level == READ
    return {
        "readOnlyHint": read_only,
        "destructiveHint": policy.level == DANGEROUS,
        "idempotentHint": read_only,
        "openWorldHint": policy.open_world,
    }


def should_register_on_mcp(
    name: str, *, enable_write: bool, has_write_user: bool
) -> bool:
    """MCP 注册闸门:只读直接放行;写操作要同时满足"显式开启 + 有写入用户"。"""
    policy = policy_for(name)
    if not policy.mcp_exposed:
        return False
    if policy.level == READ:
        return True
    if policy.level == WRITE:
        return enable_write and has_write_user
    return False
