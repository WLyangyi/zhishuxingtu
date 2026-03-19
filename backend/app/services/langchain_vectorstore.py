from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing import List, Tuple, Optional, Dict, Any
from app.services.langchain_embeddings import get_langchain_embeddings
from app.core.config import settings
import os

class LangChainVectorStore:
    def __init__(self, index_path: str, embeddings=None):
        self.index_path = index_path
        self.embeddings = embeddings or get_langchain_embeddings()
        self._vectorstore: Optional[FAISS] = None
        self._load_or_create()

    def _load_or_create(self):
        if os.path.exists(self.index_path) and os.path.exists(os.path.join(self.index_path, "index.faiss")):
            try:
                self._vectorstore = FAISS.load_local(
                    self.index_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"Loaded LangChain FAISS index from {self.index_path}")
            except Exception as e:
                print(f"Failed to load index, creating new one: {e}")
                self._vectorstore = None
        else:
            self._vectorstore = None

    def add_texts(self, texts: List[str], metadatas: List[Dict] = None) -> List[str]:
        if not texts:
            return []
        if self._vectorstore is None:
            self._vectorstore = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
        else:
            self._vectorstore.add_texts(texts=texts, metadatas=metadatas)
        return [f"doc_{i}" for i in range(len(texts))]

    def add_documents(self, documents: List[Document]) -> List[str]:
        if not documents:
            return []
        if self._vectorstore is None:
            self._vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
        else:
            self._vectorstore.add_documents(documents=documents)
        return [f"doc_{i}" for i in range(len(documents))]

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Dict = None
    ) -> List[Tuple[Document, float]]:
        if self._vectorstore is None:
            return []
        return self._vectorstore.similarity_search_with_score(query, k=k, filter=filter)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Dict = None
    ) -> List[Document]:
        if self._vectorstore is None:
            return []
        return self._vectorstore.similarity_search(query, k=k, filter=filter)

    def similarity_search_by_vector(
        self,
        embedding: List[float],
        k: int = 5,
        filter: Dict = None
    ) -> List[Document]:
        if self._vectorstore is None:
            return []
        return self._vectorstore.similarity_search_by_vector(embedding, k=k, filter=filter)

    def save(self) -> bool:
        if self._vectorstore is None:
            return False
        try:
            os.makedirs(self.index_path, exist_ok=True)
            self._vectorstore.save_local(self.index_path)
            print(f"Saved LangChain FAISS index to {self.index_path}")
            return True
        except Exception as e:
            print(f"Failed to save index: {e}")
            return False

    @property
    def index(self):
        return self._vectorstore

    @property
    def is_ready(self) -> bool:
        return self._vectorstore is not None

_vectorstore_instance = None

def get_langchain_vectorstore(index_path: str = None) -> LangChainVectorStore:
    global _vectorstore_instance
    if index_path is None:
        index_path = settings.FAISS_INDEX_PATH
    if _vectorstore_instance is None:
        _vectorstore_instance = LangChainVectorStore(index_path)
    return _vectorstore_instance
