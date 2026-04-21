import threading
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.bm25_service import BM25Service, get_bm25_service
from app.services.vector_store_adapter import get_vector_store_adapter
from app.models.note import Note


class HybridSearchService:
    """混合检索服务 - 向量语义检索 + BM25 关键词检索"""

    def __init__(self):
        self.bm25_service: Optional[BM25Service] = None
        self._initialized = False

    def initialize(self) -> None:
        """初始化混合检索服务"""
        try:
            self.bm25_service = get_bm25_service()
            self._initialized = True
            print("HybridSearch service initialized successfully")
        except Exception as e:
            print(f"Failed to initialize HybridSearch: {e}")
            self._initialized = False

    @property
    def is_ready(self) -> bool:
        """检查服务是否可用"""
        return self._initialized and settings.USE_HYBRID_SEARCH

    def hybrid_search(
        self,
        query: str,
        db: Session,
        k: int = 10,
        vector_weight: Optional[float] = None,
        bm25_weight: Optional[float] = None,
        rrf_k: Optional[int] = None,
        use_reranker: bool = False
    ) -> List[Tuple[Any, float]]:
        """
        执行混合检索（向量 + BM25 融合）
        
        Args:
            query: 查询文本
            db: 数据库会话
            k: 返回结果数量
            vector_weight: 向量检索权重（默认使用配置）
            bm25_weight: BM25权重（默认使用配置）
            rrf_k: RRF平滑参数（默认使用配置）
            use_reranker: 是否使用Reranker重排序
            
        Returns:
            [(Note对象, 融合分数), ...]
        """
        # 使用配置默认值
        vector_weight = vector_weight or settings.VECTOR_WEIGHT
        bm25_weight = bm25_weight or settings.BM25_WEIGHT
        rrf_k = rrf_k or settings.RRF_K

        # 1. 执行向量检索
        vector_results = self._vector_search(query, db, k=settings.BM25_TOP_K)

        # 2. 执行BM25检索
        bm25_results = self._bm25_search(query, k=settings.BM25_TOP_K)

        # 3. 如果其中一种检索失败，降级处理
        if not vector_results and not bm25_results:
            return []

        if not vector_results:
            return self._bm25_to_notes(bm25_results[:k], db)
        if not bm25_results:
            return self._vector_results_to_notes(vector_results[:k], db)

        # 4. RRF融合
        fused_ids_scores = self._rrf_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            rrf_k=rrf_k
        )

        # 5. 转换为Note对象并返回
        results = []
        for doc_id, score in fused_ids_scores[:k]:
            note = db.query(Note).filter(Note.id == doc_id).first()
            if note:
                results.append((note, score))

        return results

    def _vector_search(
        self,
        query: str,
        db: Session,
        k: int = 15
    ) -> List[Tuple[str, float]]:
        """
        执行向量检索
        
        Returns:
            [(doc_id, score), ...]
        """
        try:
            from app.services.embedding_service import embedding_service
            from app.services import get_vector_store

            if not embedding_service.available:
                return []

            vector_store = get_vector_store()
            if not vector_store or vector_store.total_vectors == 0:
                return []

            query_vector = embedding_service.embed_text(query)
            results = vector_store.search(query_vector, k=k, threshold=0.3)

            return results

        except Exception as e:
            print(f"Vector search error in hybrid: {e}")
            return []

    def _bm25_search(
        self,
        query: str,
        k: int = 15
    ) -> List[Tuple[str, float]]:
        """
        执行BM25检索
            
        Returns:
            [(doc_id, score), ...]
        """
        try:
            if not self.bm25_service or not self.bm25_service.is_ready:
                return []

            return self.bm25_service.search(query, top_k=k)

        except Exception as e:
            print(f"BM25 search error in hybrid: {e}")
            return []

    def _rrf_fusion(
        self,
        vector_results: List[Tuple[str, float]],
        bm25_results: List[Tuple[str, float]],
        vector_weight: float,
        bm25_weight: float,
        rrf_k: int
    ) -> List[Tuple[str, float]]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法
        
        公式: RRF Score = Σ weight * (1 / (k + rank))
        
        Args:
            vector_results: 向量检索结果 [(doc_id, score)]
            bm25_results: BM25检索结果 [(doc_id, score)]
            vector_weight: 向量权重
            bm25_weight: BM25权重
            rrf_k: 平滑参数
            
        Returns:
            融合后的结果 [(doc_id, rrf_score)] 按分数降序排列
        """
        rrf_scores: Dict[str, float] = {}

        # 向量检索结果 - 使用排名而非原始分数
        for rank, (doc_id, _) in enumerate(vector_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + \
                               vector_weight * (1 / (rrf_k + rank + 1))

        # BM25 结果 - 使用排名而非原始分数
        for rank, (doc_id, _) in enumerate(bm25_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + \
                               bm25_weight * (1 / (rrf_k + rank + 1))

        # 按分数降序排序
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return sorted_results

    def pure_bm25_search(
        self,
        query: str,
        db: Session,
        top_k: int = 15
    ) -> List[Tuple[Any, float]]:
        """
        纯 BM25 检索，返回Note对象列表
        
        Args:
            query: 查询文本
            db: 数据库会话
            top_k: 返回数量
            
        Returns:
            [(Note对象, score), ...]
        """
        if not self.bm25_service or not self.bm25_service.is_ready:
            return []

        bm25_results = self.bm25_service.search(query, top_k=top_k)
        return self._bm25_to_notes(bm25_results, db)

    def _bm25_to_notes(
        self,
        bm25_results: List[Tuple[str, float]],
        db: Session
    ) -> List[Tuple[Any, float]]:
        """将BM25结果转换为Note对象"""
        results = []
        for doc_id, score in bm25_results:
            note = db.query(Note).filter(Note.id == doc_id).first()
            if note:
                results.append((note, score))
        return results

    def _vector_results_to_notes(
        self,
        vector_results: List[Tuple[str, float]],
        db: Session
    ) -> List[Tuple[Any, float]]:
        """将向量检索结果转换为Note对象"""
        results = []
        for doc_id, score in vector_results:
            note = db.query(Note).filter(Note.id == doc_id).first()
            if note:
                results.append((note, score))
        return results

    def get_status(self) -> Dict:
        """
        获取混合检索状态信息
        
        Returns:
            状态字典
        """
        status = {
            "hybrid_enabled": settings.USE_HYBRID_SEARCH,
            "vector_weight": settings.VECTOR_WEIGHT,
            "bm25_weight": settings.BM25_WEIGHT,
            "rrf_k": settings.RRF_K,
            "hybrid_top_k": settings.HYBRID_TOP_K,
            "bm25_ready": False,
            "bm25_stats": {},
            "service_initialized": self._initialized
        }

        if self.bm25_service:
            status["bm25_ready"] = self.bm25_service.is_ready
            status["bm25_stats"] = self.bm25_service.get_stats()

        return status


# 全局单例
_hybrid_search_instance: Optional[HybridSearchService] = None
_hybrid_lock = threading.Lock()


def get_hybrid_search_service() -> HybridSearchService:
    """获取混合检索服务单例"""
    global _hybrid_search_instance
    
    if _hybrid_search_instance is None:
        with _hybrid_lock:
            if _hybrid_search_instance is None:
                _hybrid_search_instance = HybridSearchService()
    
    return _hybrid_search_instance


def init_hybrid_search() -> HybridSearchService:
    """初始化混合检索服务"""
    service = get_hybrid_search_service()
    service.initialize()
    return service
