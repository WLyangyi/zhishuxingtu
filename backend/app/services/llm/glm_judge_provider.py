from typing import Any, List, Optional

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider


class GLMJudgeProvider(BaseLLMProvider):
    """智谱 GLM-5.3-Flash 评估裁判（OpenAI 兼容端点，与 DeepSeek 推理模型不同源）。

    GLM-5.3-Flash 的工具调用仅支持 tool_choice=auto，无法强制指定函数，
    因此结构化评分走 JSON mode（response_format=json_object），不走 function_calling。
    """

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.GLM_JUDGE_MODEL or "glm-5.3-flash",
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL,
            temperature=0,
            # 裁判调用必须有上界：不设 timeout 时 openai 客户端默认等 600s，
            # 一次端点卡住就能让整轮批跑停在某条用例上（实测 4 分钟无进展）。
            timeout=30,
            max_retries=2,
        )

    def get_chat_model(self) -> ChatOpenAI:
        return self._llm

    @property
    def available(self) -> bool:
        return bool(settings.GLM_API_KEY)

    def bind_tools(self, tools: List[Any]) -> ChatOpenAI:
        return self._llm.bind_tools(tools)

    def with_structured_output(self, model: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("method", "json_mode")
        return self._llm.with_structured_output(model, **kwargs)


_instance: Optional[GLMJudgeProvider] = None


def get_glm_judge_provider() -> GLMJudgeProvider:
    global _instance
    if _instance is None:
        _instance = GLMJudgeProvider()
    return _instance
