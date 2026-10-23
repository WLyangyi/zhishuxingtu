"""评估裁判工厂：按 JUDGE_PROVIDER 选择裁判实现。"""
from app.core.config import settings
from app.services.llm.base import BaseLLMProvider


def get_judge_provider() -> BaseLLMProvider:
    provider = (settings.JUDGE_PROVIDER or "glm").strip().lower()
    if provider == "glm":
        from app.services.llm.glm_judge_provider import get_glm_judge_provider
        return get_glm_judge_provider()
    if provider == "qwen":
        from app.services.llm.qwen_judge_provider import get_qwen_judge_provider
        return get_qwen_judge_provider()
    raise ValueError(f"未知 JUDGE_PROVIDER: {settings.JUDGE_PROVIDER}（可选 glm / qwen）")


def judge_label() -> str:
    """报告与日志用的裁判口径标签。"""
    provider = (settings.JUDGE_PROVIDER or "glm").strip().lower()
    if provider == "glm":
        return f"glm / {settings.GLM_JUDGE_MODEL}"
    if provider == "qwen":
        return f"qwen / {settings.QWEN_JUDGE_MODEL}"
    return f"{provider} / unknown"
