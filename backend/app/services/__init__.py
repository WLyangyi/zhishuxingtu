from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.llm_service import DashScopeLLM, get_llm_service
from app.services.langchain_embeddings import LangChainEmbeddings, get_langchain_embeddings
from app.services.langchain_vectorstore import LangChainVectorStore, get_langchain_vectorstore
from app.services.vector_store_adapter import VectorStoreAdapter, get_vector_store_adapter

embedding_service = EmbeddingService()
vector_store = None
llm_service = None

def init_vector_store(index_path: str):
    global vector_store
    dimension = embedding_service.dimension if embedding_service.available else 1024
    vector_store = VectorStore(index_path, dimension=dimension)
    return vector_store

def get_vector_store():
    return vector_store
