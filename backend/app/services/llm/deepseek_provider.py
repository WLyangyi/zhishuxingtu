from typing import Any, List, Optional

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

# DeepSeek V4 不支持 response_format(JSON mode),结构化输出必须走 function-calling。
STRUCTURED_METHOD = "function_calling"


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
