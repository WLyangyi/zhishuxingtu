from langchain_community.embeddings import DashScopeEmbeddings
from app.core.config import settings

class LangChainEmbeddings(DashScopeEmbeddings):
    def __init__(self):
        super().__init__(
            model=settings.DASHSCOPE_EMBEDDING_MODEL,
            dashscope_api_key=settings.DASHSCOPE_API_KEY
        )

_embedding_service = None

def get_langchain_embeddings() -> LangChainEmbeddings:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = LangChainEmbeddings()
    return _embedding_service
