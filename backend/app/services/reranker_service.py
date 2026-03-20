"""
Reranker 重排序服务

使用阿里云 DashScope Reranker API 对检索结果进行精细排序。
Reranker 使用 Cross-Encoder 模型，比向量检索更准确地计算 Query-Document 相关性。

技术原理：
- 向量检索：Query 和 Document 分别编码，计算向量相似度（Bi-Encoder）
- Reranker：Query 和 Document 一起输入模型，直接计算相关性分数

适用场景：
- 对向量检索的 Top-K 结果进行重排序
- 提升检索精度，将最相关的结果排到最前面
"""

import httpx
from typing import List, Tuple, Optional
from app.core.config import settings


class RerankerService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/rerank"
        self.model = "gte-rerank"
        self._available = bool(self.api_key)
    
    @property
    def available(self) -> bool:
        return self._available
    
    def rerank(
        self, 
        query: str, 
        documents: List[Tuple[str, str, float]],
        top_k: int = 5,
        return_documents: bool = False
    ) -> List[dict]:
        """
        对文档进行重排序
        
        Args:
            query: 用户查询
            documents: 文档列表，格式为 [(id, content, original_score), ...]
            top_k: 返回前 K 个结果
            return_documents: 是否返回文档内容
        
        Returns:
            重排序后的结果列表，格式为 [{"id": ..., "score": ..., "content": ...}, ...]
        """
        if not self._available:
            return self._fallback_rerank(documents, top_k)
        
        if not documents:
            return []
        
        texts = [doc[1] for doc in documents]
        ids = [doc[0] for doc in documents]
        original_scores = [doc[2] for doc in documents]
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": {
                            "query": query,
                            "documents": texts
                        },
                        "parameters": {
                            "top_n": min(top_k, len(documents)),
                            "return_documents": return_documents
                        }
                    }
                )
                
                if response.status_code != 200:
                    print(f"Reranker API error: {response.status_code} - {response.text}")
                    return self._fallback_rerank(documents, top_k)
                
                result = response.json()
                
                reranked = []
                for item in result.get("output", {}).get("results", []):
                    idx = item.get("index", 0)
                    score = item.get("relevance_score", 0.0)
                    
                    reranked.append({
                        "id": ids[idx] if idx < len(ids) else None,
                        "content": texts[idx] if return_documents and idx < len(texts) else None,
                        "rerank_score": round(score, 4),
                        "original_score": round(original_scores[idx], 4) if idx < len(original_scores) else 0.0,
                        "index": idx
                    })
                
                return reranked[:top_k]
                
        except Exception as e:
            print(f"Reranker service error: {e}")
            return self._fallback_rerank(documents, top_k)
    
    def _fallback_rerank(
        self, 
        documents: List[Tuple[str, str, float]], 
        top_k: int
    ) -> List[dict]:
        """
        降级方案：当 Reranker 不可用时，使用原始分数排序
        """
        sorted_docs = sorted(documents, key=lambda x: x[2], reverse=True)
        
        return [
            {
                "id": doc[0],
                "content": doc[1],
                "rerank_score": doc[2],
                "original_score": doc[2],
                "index": i
            }
            for i, doc in enumerate(sorted_docs[:top_k])
        ]
    
    def rerank_with_notes(
        self,
        query: str,
        note_results: List[Tuple],
        top_k: int = 5
    ) -> List[Tuple]:
        """
        对笔记检索结果进行重排序
        
        Args:
            query: 用户查询
            note_results: 笔记检索结果，格式为 [(Note对象, score), ...]
            top_k: 返回前 K 个结果
        
        Returns:
            重排序后的结果列表，格式为 [(Note对象, rerank_score), ...]
        """
        if not note_results:
            return []
        
        documents = []
        for note, score in note_results:
            content = f"{note.title}\n{note.content or ''}"
            documents.append((note.id, content[:2000], score))
        
        reranked = self.rerank(query, documents, top_k=top_k)
        
        note_map = {note.id: note for note, _ in note_results}
        
        result = []
        for item in reranked:
            note_id = item["id"]
            if note_id in note_map:
                result.append((note_map[note_id], item["rerank_score"]))
        
        return result


_reranker_instance = None


def get_reranker() -> RerankerService:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = RerankerService()
    return _reranker_instance
