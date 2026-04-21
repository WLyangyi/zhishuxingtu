import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.services.langchain_embeddings import get_langchain_embeddings
from app.core.config import settings


class ChatMemoryStore:
    def __init__(self, index_path: str = None, top_k: int = None, min_score: float = None):
        self.embeddings = get_langchain_embeddings()
        self.index_path = index_path or settings.CHAT_MEMORY_INDEX_PATH
        self.top_k = top_k or settings.CHAT_MEMORY_TOP_K
        self.min_score = min_score or settings.CHAT_MEMORY_MIN_SCORE
        self._vectorstore: Optional[FAISS] = None
        self._ensure_index_path()
    
    def _ensure_index_path(self):
        os.makedirs(self.index_path, exist_ok=True)
    
    def _get_vectorstore(self) -> FAISS:
        if self._vectorstore is None:
            index_file = os.path.join(self.index_path, "index.faiss")
            if os.path.exists(index_file):
                try:
                    self._vectorstore = FAISS.load_local(
                        self.index_path,
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                except Exception as e:
                    print(f"[ChatMemoryStore] 加载向量索引失败: {e}")
                    self._vectorstore = self._create_empty_vectorstore()
            else:
                self._vectorstore = self._create_empty_vectorstore()
        return self._vectorstore
    
    def _create_empty_vectorstore(self) -> FAISS:
        return FAISS.from_texts(
            ["初始化对话记忆"],
            self.embeddings,
            metadatas=[{"type": "init", "timestamp": datetime.now().isoformat()}]
        )
    
    def add_conversation(
        self,
        user_message: str,
        assistant_message: str,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        combined_text = f"用户: {user_message}\n助手: {assistant_message}"
        
        doc_metadata = {
            "conversation_id": conversation_id,
            "session_id": session_id or "default",
            "timestamp": timestamp,
            "user_message": user_message[:500],
            "assistant_message": assistant_message[:500],
            "type": "conversation"
        }
        
        if metadata:
            doc_metadata.update(metadata)
        
        vectorstore = self._get_vectorstore()
        vectorstore.add_texts(
            [combined_text],
            metadatas=[doc_metadata]
        )
        
        self._save_vectorstore()
        
        return conversation_id
    
    def search_relevant_history(
        self,
        query: str,
        top_k: int = None,
        min_score: float = None,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        k = top_k or self.top_k
        threshold = min_score or self.min_score
        
        vectorstore = self._get_vectorstore()
        
        try:
            results_with_scores = vectorstore.similarity_search_with_score(query, k=k * 2)
        except Exception as e:
            print(f"[ChatMemoryStore] 检索失败: {e}")
            return []
        
        filtered_results = []
        for doc, score in results_with_scores:
            if doc.metadata.get("type") == "init":
                continue
            
            similarity = 1 - score
            
            if similarity < threshold:
                continue
            
            if session_id and doc.metadata.get("session_id") != session_id:
                continue
            
            filtered_results.append({
                "conversation_id": doc.metadata.get("conversation_id"),
                "session_id": doc.metadata.get("session_id"),
                "user_message": doc.metadata.get("user_message"),
                "assistant_message": doc.metadata.get("assistant_message"),
                "timestamp": doc.metadata.get("timestamp"),
                "similarity": similarity,
                "content": doc.page_content
            })
        
        return filtered_results[:k]
    
    def get_context_for_query(
        self,
        query: str,
        session_id: str = None,
        max_tokens: int = 1500
    ) -> str:
        relevant_history = self.search_relevant_history(
            query,
            session_id=session_id
        )
        
        if not relevant_history:
            return ""
        
        context_parts = []
        total_length = 0
        
        for item in relevant_history:
            part = f"【历史对话】\n用户: {item['user_message']}\n助手: {item['assistant_message']}"
            
            if total_length + len(part) > max_tokens:
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        if not context_parts:
            return ""
        
        return "\n\n".join(context_parts)
    
    def _save_vectorstore(self):
        if self._vectorstore is not None:
            try:
                self._vectorstore.save_local(self.index_path)
            except Exception as e:
                print(f"[ChatMemoryStore] 保存向量索引失败: {e}")
    
    def clear_session(self, session_id: str = None):
        if session_id:
            pass
        else:
            self._vectorstore = self._create_empty_vectorstore()
            self._save_vectorstore()
    
    def get_stats(self) -> Dict[str, Any]:
        try:
            vectorstore = self._get_vectorstore()
            return {
                "index_path": self.index_path,
                "total_documents": vectorstore.index.ntotal if hasattr(vectorstore, 'index') else 0,
                "top_k": self.top_k,
                "min_score": self.min_score
            }
        except Exception as e:
            return {
                "index_path": self.index_path,
                "error": str(e)
            }


_chat_memory_store_instance: Optional[ChatMemoryStore] = None


def get_chat_memory_store() -> ChatMemoryStore:
    global _chat_memory_store_instance
    if _chat_memory_store_instance is None:
        _chat_memory_store_instance = ChatMemoryStore()
    return _chat_memory_store_instance
