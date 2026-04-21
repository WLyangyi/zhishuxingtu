import sys
import os
import json
import requests

user_site = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python313', 'site-packages')
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

import numpy as np
from typing import List, Optional, Tuple
from app.core.config import settings
from app.services.text_chunker import RecursiveChunker, TextChunk


class EmbeddingService:
    _instance: Optional['EmbeddingService'] = None
    _dimension = 1024
    _available = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._available:
            self._check_api()

        self.chunker = RecursiveChunker(
            max_chunk_size=getattr(settings, 'MAX_CHUNK_SIZE', 800),
            overlap_ratio=getattr(settings, 'OVERLAP_RATIO', 0.5),
            min_chunk_size=getattr(settings, 'MIN_CHUNK_SIZE', 50),
            chunk_by_divider=getattr(settings, 'CHUNK_BY_DIVIDER', True),
            chunk_by_heading=getattr(settings, 'CHUNK_BY_HEADING', True),
            chunk_by_paragraph=getattr(settings, 'CHUNK_BY_PARAGRAPH', True),
            chunk_by_sentence=getattr(settings, 'CHUNK_BY_SENTENCE', True)
        )
    
    def _check_api(self):
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', '')
        if api_key:
            self._available = True
            print(f"Using DashScope API with model: text-embedding-v3")
            print(f"Embedding service initialized, dimension: {self._dimension}")
        else:
            print("Warning: DASHSCOPE_API_KEY not set, embedding service disabled")
            print("Set DASHSCOPE_API_KEY in .env to enable vector search")
            self._available = False
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def available(self) -> bool:
        return self._available
    
    def embed_text(self, text: str) -> np.ndarray:
        if not self._available:
            return np.zeros(self._dimension, dtype=np.float32)
        
        if not text or not text.strip():
            return np.zeros(self._dimension, dtype=np.float32)
        
        try:
            api_key = getattr(settings, 'DASHSCOPE_API_KEY', '')
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                "model": "text-embedding-v3",
                "input": text,
                "dimensions": 1024,
                "encoding_format": "float"
            }
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()
            
            if data.get('data') and len(data['data']) > 0:
                embedding = np.array(data['data'][0]['embedding'], dtype=np.float32)
                return embedding
            else:
                print(f"DashScope API error: {data}")
                return np.zeros(self._dimension, dtype=np.float32)
        except Exception as e:
            print(f"Embedding API call failed: {e}")
            return np.zeros(self._dimension, dtype=np.float32)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not self._available:
            return np.zeros((len(texts), self._dimension), dtype=np.float32)
        
        if not texts:
            return np.array([], dtype=np.float32)
        
        try:
            api_key = getattr(settings, 'DASHSCOPE_API_KEY', '')
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            valid_texts = [t if t and t.strip() else "" for t in texts]
            
            all_embeddings = []
            batch_size = 10
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]
                payload = {
                    "model": "text-embedding-v3",
                    "input": batch,
                    "dimensions": 1024,
                    "encoding_format": "float"
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                data = response.json()
                
                if data.get('data') and len(data['data']) > 0:
                    for item in data['data']:
                        embedding = np.array(item['embedding'], dtype=np.float32)
                        all_embeddings.append(embedding)
                else:
                    print(f"DashScope batch error: {data}")
                    for _ in batch:
                        all_embeddings.append(np.zeros(self._dimension, dtype=np.float32))
            
            return np.array(all_embeddings, dtype=np.float32)
        except Exception as e:
            print(f"Batch embedding failed: {e}")
            return np.zeros((len(texts), self._dimension), dtype=np.float32)
    
    def prepare_note_text(self, title: str, content: str, max_length: int = 2048) -> str:
        combined = f"{title}\n{content or ''}"
        if len(combined) > max_length:
            combined = combined[:max_length]
        return combined

    def embed_chunks(self, note_id: str, title: str, content: str) -> Tuple[List[TextChunk], np.ndarray]:
        chunks = self.chunker.chunk(note_id, title, content)
        if not chunks:
            return [], np.array([])

        texts = [chunk.content for chunk in chunks]
        vectors = self.embed_texts(texts)
        return chunks, vectors


embedding_service = EmbeddingService()
