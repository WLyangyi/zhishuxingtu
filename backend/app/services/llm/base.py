from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """LLM Provider 抽象。当前只有 DeepSeek 实现,按需扩展。"""

    @abstractmethod
    def get_chat_model(self):
        """返回支持 bind_tools / with_structured_output 的 ChatModel。"""

    @property
    @abstractmethod
    def available(self) -> bool:
        """是否配置了可用凭据。"""
