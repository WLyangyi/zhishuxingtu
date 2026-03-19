from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

embedding_service = EmbeddingService()
vector_store = None

def init_vector_store(index_path: str):
    global vector_store
    dimension = embedding_service.dimension if embedding_service.available else 1024
    vector_store = VectorStore(index_path, dimension=dimension)
    return vector_store

def get_vector_store():
    return vector_store
