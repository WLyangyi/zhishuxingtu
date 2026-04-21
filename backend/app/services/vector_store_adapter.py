from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict
from app.core.config import settings
import numpy as np

_vector_store_adapter_instance = None

class VectorStoreAdapter:
    def __init__(self):
        self._use_langchain = settings.USE_LANGCHAIN_VECTORSTORE
        self._original_store = None
        self._langchain_store = None
        self._note_chunks_map: Dict[str, List[str]] = {}
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

    def add_note_chunks(
        self,
        note_id: str,
        chunks: List[Any],
        vectors: np.ndarray
    ) -> Dict[str, Any]:
        chunk_ids = []

        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            chunk_id = f"{note_id}_chunk_{i}"

            if self._use_langchain:
                self._langchain_store.add_texts(
                    texts=[chunk.content],
                    metadatas=[{
                        "note_id": note_id,
                        "chunk_index": i,
                        "chunk_total": chunk.total_chunks
                    }]
                )
            else:
                self._original_store.add_vector(chunk_id, vector)

            chunk_ids.append(chunk_id)

        self._note_chunks_map[note_id] = chunk_ids
        return {"success": len(chunk_ids), "chunk_ids": chunk_ids}

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        threshold: float = 0.3,
        aggregate_by_note: bool = True
    ) -> List[Tuple[str, float]]:
        raw_k = k * 3 if aggregate_by_note else k

        if self._use_langchain:
            query_text = f"query_{np.argmax(query_vector)}"
            results = self._langchain_store.similarity_search_with_score(query_text, k=raw_k)
            filtered = [(doc.metadata.get("note_id", ""), float(score))
                       for doc, score in results if score >= (1 - threshold)]
            raw_results = filtered
        else:
            raw_results = self._original_store.search(query_vector, raw_k, threshold)

        if not aggregate_by_note or not raw_results:
            return raw_results[:k]

        return self._aggregate_by_note(raw_results, k)

    def _aggregate_by_note(
        self,
        raw_results: List[Tuple[str, float]],
        k: int
    ) -> List[Tuple[str, float]]:
        note_scores: Dict[str, List[float]] = defaultdict(list)

        for item_id, score in raw_results:
            if "_chunk_" in str(item_id):
                note_id = str(item_id).rsplit("_chunk_", 1)[0]
            else:
                note_id = str(item_id)

            note_scores[note_id].append(score)

        aggregated = [
            (note_id, max(scores))
            for note_id, scores in note_scores.items()
        ]
        aggregated.sort(key=lambda x: x[1], reverse=True)

        return aggregated[:k]

    def clear(self) -> bool:
        self._note_chunks_map.clear()

        if self._use_langchain:
            print("Warning: LangChain backend does not support clear()")
            return False

        return self._original_store.clear()

    def get_note_chunk_count(self, note_id: str) -> int:
        return len(self._note_chunks_map.get(note_id, []))

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

    def hybrid_search(self, query: str, db, k: int = 10) -> List[Tuple[str, float]]:
        """通过适配器调用混合检索"""
        from app.services.hybrid_search import get_hybrid_search_service
        
        hybrid_service = get_hybrid_search_service()
        if hybrid_service.is_ready:
            results = hybrid_service.hybrid_search(query, db, k=k)
            return [(note.id if hasattr(note, 'id') else str(note), score) 
                   for note, score in results]
        
        # 降级到纯向量检索
        from app.services.embedding_service import embedding_service
        
        if not embedding_service.available:
            return []
            
        query_vector = embedding_service.embed_text(query)
        return self.search(query_vector, k=k)

def get_vector_store_adapter() -> VectorStoreAdapter:
    global _vector_store_adapter_instance
    if _vector_store_adapter_instance is None:
        _vector_store_adapter_instance = VectorStoreAdapter()
    return _vector_store_adapter_instance
