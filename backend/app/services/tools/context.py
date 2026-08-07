from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolContext:
    """每次 agent 调用时注入的上下文,工具据此做用户隔离与审计。"""

    user_id: str
    session_id: str


_tool_context: ContextVar[Optional[ToolContext]] = ContextVar("agent_tool_context", default=None)


def set_tool_context(ctx: Optional[ToolContext]) -> Token:
    return _tool_context.set(ctx)


def reset_tool_context(token: Token) -> None:
    _tool_context.reset(token)


def get_tool_context() -> Optional[ToolContext]:
    return _tool_context.get()
