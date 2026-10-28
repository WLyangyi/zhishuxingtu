from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolContext:
    """每次 agent 调用时注入的上下文,工具据此做用户隔离与审计。

    tool_call_id 是模型本轮工具调用的 id,写工具用它派生幂等键:
    同一 session 的同一个 tool_call 被重放(resume/重试)时不会重复落库。
    """

    user_id: str
    session_id: str
    tool_call_id: Optional[str] = None


_tool_context: ContextVar[Optional[ToolContext]] = ContextVar("agent_tool_context", default=None)


def set_tool_context(ctx: Optional[ToolContext]) -> Token:
    return _tool_context.set(ctx)


def reset_tool_context(token: Token) -> None:
    _tool_context.reset(token)


def get_tool_context() -> Optional[ToolContext]:
    return _tool_context.get()
