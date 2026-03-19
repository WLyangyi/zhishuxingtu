from typing import List, Tuple, Dict, Any, Optional
from app.core.config import settings
import numpy as np

_vector_store_adapter_instance = None

class VectorStoreAdapter:
    def __init__(self):
        self._use_langchain = settings.USE_LANGCHAIN_VECTORSTORE
        self._original_store = None
        self._langchain_store = None
        self._init_stores()

    def _init_stores(self):
        if not self._use_langchain:
            from app.services.vector_store import VectorStore
            self._original_store = VectorStore(
                index_path=settings.FAISS_INDEX_PATH,
                dimension=1024
            )
        else:
            from app.services.langchain_vectorstore import get_langchain_vectorstore
            self._langchain_store = get_langchain_vectorstore()

    def add_vector(self, note_id: str, vector: np.ndarray) -> bool:
        if self._use_langchain:
            docs = self._langchain_store.add_texts(
                texts=[f"note_{note_id}"],
                metadatas=[{"note_id": note_id}]
            )
            return len(docs) > 0
        return self._original_store.add_vector(note_id, vector)

    def add_vectors(self, note_ids: List[str], vectors: np.ndarray) -> Dict[str, Any]:
        if self._use_langchain:
            metadatas = [{"note_id": nid} for nid in note_ids]
            texts = [f"note_{nid}" for nid in note_ids]
            self._langchain_store.add_texts(texts=texts, metadatas=metadatas)
            return {"success": len(note_ids), "failed": 0, "errors": []}
        return self._original_store.add_vectors(note_ids, vectors)

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        if self._use_langchain:
            query_text = f"query_{np.argmax(query_vector)}"
            results = self._langchain_store.similarity_search_with_score(query_text, k=k)
            filtered = [(doc.metadata.get("note_id", ""), float(score))
                       for doc, score in results if score >= (1 - threshold)]
            return filtered
        return self._original_store.search(query_vector, k, threshold)

    def save(self) -> bool:
        if self._use_langchain:
            return self._langchain_store.save()
        return self._original_store.save()

    def get_stats(self) -> Dict[str, Any]:
        if self._use_langchain:
            return {
                "total_vectors": len(self._langchain_store.index) if self._langchain_store.index else 0,
                "dimension": 1024,
                "index_path": settings.FAISS_INDEX_PATH,
                "backend": "langchain"
            }
        return self._original_store.get_stats()

    @property
    def is_ready(self) -> bool:
        if self._use_langchain:
            return self._langchain_store is not None and self._langchain_store.is_ready
        return self._original_store is not None and self._original_store.is_ready

def get_vector_store_adapter() -> VectorStoreAdapter:
    global _vector_store_adapter_instance
    if _vector_store_adapter_instance is None:
        _vector_store_adapter_instance = VectorStoreAdapter()
    return _vector_store_adapter_instance
