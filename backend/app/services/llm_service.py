from langchain_openai import ChatOpenAI
from app.core.config import settings

class DashScopeLLM:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                temperature=0.7
            )
        return cls._instance

    @property
    def client(self) -> ChatOpenAI:
        return self._client

    def invoke(self, messages, **kwargs):
        return self._client.invoke(messages, **kwargs)

def get_llm_service() -> DashScopeLLM:
    return DashScopeLLM()
