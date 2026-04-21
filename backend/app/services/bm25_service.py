import threading
import re
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
import jieba
from sqlalchemy.orm import Session
from app.models.note import Note


@dataclass
class BM25Document:
    doc_id: str
    title: str
    content: str
    text: str = ""  # 预处理后的文本


class BM25Service:
    """BM25 关键词检索服务"""

    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.documents: Dict[str, BM25Document] = {}
        self._lock = threading.RLock()
        self._initialized = False

    @property
    def is_ready(self) -> bool:
        return self._initialized and self.bm25 is not None

    def _preprocess_text(self, title: str, content: str) -> str:
        """
        文本预处理：合并标题和内容，去除特殊字符
        
        Args:
            title: 笔记标题
            content: 笔记内容
            
        Returns:
            预处理后的文本
        """
        parts = []
        if title:
            parts.append(title)
        if content:
            parts.append(content)
        
        combined = " ".join(parts)
        
        # 去除多余空白，但保留中文
        combined = re.sub(r'[ \t]+', ' ', combined)
        combined = re.sub(r'\n+', ' ', combined)
        combined = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', combined)
        
        return combined.strip()

    def _tokenize(self, text: str) -> List[str]:
        """
        中文分词 + 英文分词
        
        Args:
            text: 输入文本
            
        Returns:
            分词结果列表
        """
        if not text or not text.strip():
            return []
            
        # 使用jieba进行中文分词
        tokens = list(jieba.cut(text))
        
        # 过滤空字符串、单字符（保留中文字符）
        filtered_tokens = []
        for token in tokens:
            token = token.strip()
            if len(token) == 0:
                continue
            # 保留中文字符、英文单词（长度>1）、数字
            if re.match(r'^[\u4e00-\u9fff]+$', token):
                filtered_tokens.append(token)
            elif re.match(r'^[a-zA-Z]{2,}$', token):
                filtered_tokens.append(token.lower())
            elif re.match(r'^[0-9]+$', token):
                filtered_tokens.append(token)
                
        return filtered_tokens

    def index_documents(self, docs: List[Dict[str, str]]) -> None:
        """
        构建/重建 BM25 索引
        
        Args:
            docs: 文档列表，每个文档包含 id, title, content
        """
        with self._lock:
            self.doc_ids = []
            self.tokenized_corpus = []
            self.documents = {}

            for doc in docs:
                doc_id = doc['id']
                title = doc.get('title', '')
                content = doc.get('content', '')
                
                preprocessed_text = self._preprocess_text(title, content)
                tokens = self._tokenize(preprocessed_text)
                
                if tokens:
                    bm25_doc = BM25Document(
                        doc_id=doc_id,
                        title=title,
                        content=content,
                        text=preprocessed_text
                    )
                    self.documents[doc_id] = bm25_doc
                    self.doc_ids.append(doc_id)
                    self.tokenized_corpus.append(tokens)

            if self.tokenized_corpus:
                self.bm25 = BM25Okapi(self.tokenized_corpus)
                self._initialized = True
            else:
                self.bm25 = None
                self._initialized = False

    def add_document(self, doc_id: str, title: str, content: str) -> None:
        """
        添加单个文档到索引
        
        Args:
            doc_id: 文档ID
            title: 标题
            content: 内容
        """
        with self._lock:
            # 如果已存在，先移除
            if doc_id in self.documents:
                self.remove_document(doc_id)

            preprocessed_text = self._preprocess_text(title, content)
            tokens = self._tokenize(preprocessed_text)

            if tokens:
                bm25_doc = BM25Document(
                    doc_id=doc_id,
                    title=title,
                    content=content,
                    text=preprocessed_text
                )
                self.documents[doc_id] = bm25_doc
                self.doc_ids.append(doc_id)
                self.tokenized_corpus.append(tokens)

                # 重建索引
                if self.tokenized_corpus:
                    self.bm25 = BM25Okapi(self.tokenized_corpus)
                    self._initialized = True

    def remove_document(self, doc_id: str) -> None:
        """
        从索引中移除文档
        
        Args:
            doc_id: 文档ID
        """
        with self._lock:
            if doc_id not in self.documents:
                return

            idx = None
            for i, did in enumerate(self.doc_ids):
                if did == doc_id:
                    idx = i
                    break

            if idx is not None:
                self.doc_ids.pop(idx)
                self.tokenized_corpus.pop(idx)
                del self.documents[doc_id]

                # 重建索引
                if self.tokenized_corpus:
                    self.bm25 = BM25Okapi(self.tokenized_corpus)
                else:
                    self.bm25 = None
                    self._initialized = False

    def search(self, query: str, top_k: int = 15) -> List[Tuple[str, float]]:
        """
        执行 BM25 检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            [(doc_id, score), ...] 按分数降序排列
        """
        if not self.is_ready:
            return []

        try:
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return []

            scores = self.bm25.get_scores(query_tokens)

            # 组合 (doc_id, score)
            doc_scores = [(doc_id, float(score)) 
                         for doc_id, score in zip(self.doc_ids, scores)]

            # 过滤负分，按分数降序排序
            doc_scores = [(did, s) for did, s in doc_scores if s > 0]
            doc_scores.sort(key=lambda x: x[1], reverse=True)

            return doc_scores[:top_k]

        except Exception as e:
            print(f"BM25 search error: {e}")
            return []

    def rebuild_index(self, db: Session) -> Dict:
        """
        从数据库重建完整 BM25 索引
        
        Args:
            db: 数据库会话
            
        Returns:
            重建结果统计
        """
        try:
            notes = db.query(Note).all()
            
            docs = [
                {
                    'id': note.id,
                    'title': note.title or '',
                    'content': note.content or ''
                }
                for note in notes
                if note.title or note.content
            ]

            self.index_documents(docs)

            return {
                "success": True,
                "total": len(docs),
                "indexed": len(self.doc_ids),
                "message": f"BM25 索引重建完成，共 {len(self.doc_ids)} 个文档"
            }

        except Exception as e:
            return {
                "success": False,
                "total": 0,
                "indexed": 0,
                "error": str(e),
                "message": f"BM25 索引重建失败: {str(e)}"
            }

    def get_stats(self) -> Dict:
        """
        获取索引统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "initialized": self._initialized,
            "total_documents": len(self.doc_ids),
            "total_tokens": sum(len(t) for t in self.tokenized_corpus),
            "is_ready": self.is_ready
        }


# 全局单例
_bm25_service_instance: Optional[BM25Service] = None
_bm25_lock = threading.Lock()


def get_bm25_service() -> BM25Service:
    """获取 BM25 服务单例"""
    global _bm25_service_instance
    
    if _bm25_service_instance is None:
        with _bm25_lock:
            if _bm25_service_instance is None:
                _bm25_service_instance = BM25Service()
    
    return _bm25_service_instance
