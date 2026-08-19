from typing import Any, List, Optional

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

# qwen3.8-max 走 DashScope OpenAI 兼容端点
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# P16: qwen3.8-max 默认 thinking mode 拒绝强制 tool_choice(400),必须显式关思考
JUDGE_EXTRA = {"enable_thinking": False}


class QwenJudgeProvider(BaseLLMProvider):
    """评估独立裁判(qwen3.8-max, 与推理模型不同源, 避免同源偏差)。"""

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.QWEN_JUDGE_MODEL or "qwen3.8-max",
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            temperature=0,
            extra_body=JUDGE_EXTRA,
        )

    def get_chat_model(self) -> ChatOpenAI:
        return self._llm

    @property
    def available(self) -> bool:
        return bool(settings.DASHSCOPE_API_KEY)

    def bind_tools(self, tools: List[Any]) -> ChatOpenAI:
        return self._llm.bind_tools(tools)

    def with_structured_output(self, model: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("method", "function_calling")
        return self._llm.with_structured_output(model, **kwargs)


_instance: Optional[QwenJudgeProvider] = None


def get_qwen_judge_provider() -> QwenJudgeProvider:
    global _instance
    if _instance is None:
        _instance = QwenJudgeProvider()
    return _instance
