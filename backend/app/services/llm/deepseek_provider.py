import random
import time
from typing import Any, List, Optional

import openai
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

# DeepSeek V4 不支持 response_format(JSON mode),结构化输出必须走 function-calling。
STRUCTURED_METHOD = "function_calling"

# 只重试瞬时错误:网络超时/连接失败/限流/5xx。400 这类请求格式错误重试也没用,
# 重试只会把一次失败放大成三次。
TRANSIENT_ERRORS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


def is_transient_llm_error(exc: BaseException) -> bool:
    """判断异常是否值得退避重试。"""
    if isinstance(exc, TRANSIENT_ERRORS):
        return True
    # 未覆盖到的 APIStatusError(如各家网关返回的 502/503)按状态码判断
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code >= 500 or exc.status_code == 429
    return False


def invoke_with_retry(runnable: Any, inputs: Any, *, label: str = "llm") -> Any:
    """带指数退避的 invoke。

    仅对瞬时错误重试;非瞬时错误(参数非法、结构化输出解析失败等)立刻抛出,
    避免把一次确定性失败放大成三次调用并拖长用户等待。
    """
    attempts = max(1, int(settings.LLM_MAX_ATTEMPTS))
    base_delay = max(0.0, float(settings.LLM_RETRY_BASE_DELAY))
    for attempt in range(1, attempts + 1):
        try:
            return runnable.invoke(inputs)
        except Exception as exc:  # noqa: BLE001
            if attempt >= attempts or not is_transient_llm_error(exc):
                raise
            # 指数退避 + 抖动:1s / 2s / 4s…,抖动避免多个请求同一时刻重试
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            print(
                f"[llm] {label} 第 {attempt}/{attempts} 次调用失败"
                f"({type(exc).__name__}: {exc}),{delay:.1f}s 后重试"
            )
            time.sleep(delay)
    raise AssertionError("unreachable")


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek 官方通道(thinking 显式关闭,工具调用全兼容)。"""

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL or "deepseek-v4-flash",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com",
            temperature=0,
            max_tokens=2000,
            extra_body={"thinking": {"type": "disabled"}},
            # 客户端自身不重试:退避策略统一由 invoke_with_retry 掌控,否则两层重试
            # 叠乘(3 × 3)会让一次端点抖动变成九次调用。
            timeout=float(settings.LLM_TIMEOUT_SECONDS),
            max_retries=0,
        )

    def get_chat_model(self) -> ChatOpenAI:
        return self._llm

    @property
    def available(self) -> bool:
        return bool(settings.DEEPSEEK_API_KEY)

    def bind_tools(self, tools: List[Any]) -> ChatOpenAI:
        return self._llm.bind_tools(tools)

    def with_structured_output(self, model: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("method", STRUCTURED_METHOD)
        return self._llm.with_structured_output(model, **kwargs)


_instance: Optional[DeepSeekProvider] = None


def get_deepseek_provider() -> DeepSeekProvider:
    global _instance
    if _instance is None:
        _instance = DeepSeekProvider()
    return _instance
