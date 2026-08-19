"""M2-6 Langfuse 可观测接入(fail-silent)。

key 缺失或初始化失败时静默降级(返回 None),绝不影响 agent 主流程。
"""
from typing import Any, Optional

from app.core.config import settings

_handler: Optional[Any] = None
_attempted = False


def get_langfuse_handler() -> Optional[Any]:
    """返回 Langfuse LangChain CallbackHandler,未配置/失败时返回 None。"""
    global _handler, _attempted
    if _attempted:
        return _handler
    _attempted = True

    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        print("[Langfuse] 未配置 key,跳过(不影响主流程)")
        return None
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        # langfuse 4.x: handler 只收 public_key,client 需先显式实例化注册(secret_key/base_url 由 client 持有)。
        # 依赖干净 .venv(.venv-clean):旧 .venv 用 --system-site-packages 混入 Anaconda 旧版 opentelemetry,
        # 导致 TraceFlags 缺 RANDOM_TRACE_ID(P17),故须用干净环境跑含 langfuse 的进程。
        Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            base_url=settings.LANGFUSE_BASE_URL,
        )
        _handler = CallbackHandler(public_key=settings.LANGFUSE_PUBLIC_KEY)
        print("[Langfuse] 已启用(fail-silent)")
    except Exception as e:  # noqa: BLE001 任何异常都降级
        print(f"[Langfuse] 初始化失败,静默降级: {e}")
        _handler = None
    return _handler


def build_stream_config(thread_id: str, user_id: str = "", run_name: str = "agent-chat") -> dict:
    """构造 LangGraph stream config，并把用户/会话映射到 Langfuse trace。"""
    cfg = {
        "configurable": {"thread_id": thread_id},
        "run_name": run_name,
        "metadata": {
            "langfuse_session_id": thread_id,
            "langfuse_user_id": user_id,
            "langfuse_tags": ["agentic-rag", "m4-m5"],
        },
    }
    handler = get_langfuse_handler()
    if handler:
        cfg["callbacks"] = [handler]
    return cfg
