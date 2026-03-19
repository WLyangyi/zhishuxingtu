import sys
import os

user_site = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python313', 'site-packages')
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

import json
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import faiss
import threading
import time


class VectorStoreError(Exception):
    pass


class VectorStore:
    def __init__(self, index_path: str, dimension: int = 1024):
        self.index_path = index_path
        self.dimension = dimension
        self.index: Optional[faiss.IndexFlatIP] = None
        self.id_map: Dict[int, str] = {}
        self.reverse_map: Dict[str, int] = {}
        self._next_idx = 0
        self._lock = threading.RLock()
        self._initialized = False
        self._stats = {
            'total_adds': 0,
            'total_updates': 0,
            'total_removes': 0,
            'total_searches': 0,
            'total_search_time': 0.0
        }
        
        try:
            os.makedirs(index_path, exist_ok=True)
            self._load_or_create()
            self._initialized = True
        except Exception as e:
            print(f"Failed to initialize vector store: {e}")
            self._create_new()
            self._initialized = True
    
    def _load_or_create(self):
        index_file = os.path.join(self.index_path, "index.faiss")
        meta_file = os.path.join(self.index_path, "meta.json")
        
        if os.path.exists(index_file) and os.path.exists(meta_file):
            try:
                self.index = faiss.read_index(index_file)
                loaded_dimension = self.index.d
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    self.id_map = {int(k): v for k, v in meta.get('id_map', {}).items()}
                    self.reverse_map = meta.get('reverse_map', {})
                    self._next_idx = meta.get('next_idx', 0)
                
                if loaded_dimension != self.dimension:
                    print(f"Dimension mismatch: loaded {loaded_dimension}, expected {self.dimension}. Creating new index.")
                    self._create_new()
                else:
                    print(f"Loaded FAISS index with {self.index.ntotal} vectors, dimension: {loaded_dimension}")
            except Exception as e:
                print(f"Failed to load index, creating new one: {e}")
                self._create_new()
        else:
            self._create_new()
    
    def _create_new(self):
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_map = {}
        self.reverse_map = {}
        self._next_idx = 0
    
    def _validate_vector(self, vector: np.ndarray) -> np.ndarray:
        if vector is None:
            raise VectorStoreError("Vector cannot be None")
        
        if not isinstance(vector, np.ndarray):
            vector = np.array(vector, dtype=np.float32)
        
        if vector.shape[0] != self.dimension:
            raise VectorStoreError(
                f"Vector dimension mismatch: expected {self.dimension}, got {vector.shape[0]}"
            )
        
        return vector.astype(np.float32)
    
    def add_vector(self, note_id: str, vector: np.ndarray) -> bool:
        with self._lock:
            try:
                if note_id in self.reverse_map:
                    return self._update_vector_internal(note_id, vector)
                
                vector = self._validate_vector(vector)
                vector = vector.reshape(1, -1)
                
                self.index.add(vector)
                
                idx = self._next_idx
                self.id_map[idx] = note_id
                self.reverse_map[note_id] = idx
                self._next_idx += 1
                self._stats['total_adds'] += 1
                
                return True
            except VectorStoreError:
                raise
            except Exception as e:
                raise VectorStoreError(f"Failed to add vector: {e}")
    
    def add_vectors(self, note_ids: List[str], vectors: np.ndarray) -> Dict[str, Any]:
        if not note_ids:
            return {'success': 0, 'failed': 0, 'errors': []}
        
        if len(note_ids) != vectors.shape[0]:
            raise VectorStoreError(
                f"Number of IDs ({len(note_ids)}) must match number of vectors ({vectors.shape[0]})"
            )
        
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        with self._lock:
            for i, note_id in enumerate(note_ids):
                try:
                    self.add_vector(note_id, vectors[i])
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({'id': note_id, 'error': str(e)})
        
        return results
    
    def _update_vector_internal(self, note_id: str, vector: np.ndarray) -> bool:
        idx = self.reverse_map[note_id]
        vector = self._validate_vector(vector)
        vector = vector.reshape(1, -1)
        
        try:
            self.index.remove_ids(faiss.IDSelectorArray(np.array([idx])))
        except Exception:
            pass
        
        self.index.add(vector)
        
        new_idx = self._next_idx
        del self.id_map[idx]
        self.id_map[new_idx] = note_id
        self.reverse_map[note_id] = new_idx
        self._next_idx += 1
        self._stats['total_updates'] += 1
        
        return True
    
    def update_vector(self, note_id: str, vector: np.ndarray) -> bool:
        with self._lock:
            try:
                if note_id not in self.reverse_map:
                    return self.add_vector(note_id, vector)
                return self._update_vector_internal(note_id, vector)
            except VectorStoreError:
                raise
            except Exception as e:
                raise VectorStoreError(f"Failed to update vector: {e}")
    
    def remove_vector(self, note_id: str) -> bool:
        with self._lock:
            if note_id not in self.reverse_map:
                return False
            
            idx = self.reverse_map[note_id]
            
            try:
                self.index.remove_ids(faiss.IDSelectorArray(np.array([idx])))
            except Exception:
                pass
            
            if idx in self.id_map:
                del self.id_map[idx]
            del self.reverse_map[note_id]
            self._stats['total_removes'] += 1
            
            return True
    
    def remove_vectors(self, note_ids: List[str]) -> Dict[str, Any]:
        results = {'success': 0, 'not_found': 0}
        
        with self._lock:
            for note_id in note_ids:
                if self.remove_vector(note_id):
                    results['success'] += 1
                else:
                    results['not_found'] += 1
        
        return results
    
    def search(
        self, 
        query_vector: np.ndarray, 
        k: int = 5, 
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        with self._lock:
            start_time = time.time()
            
            try:
                if self.index.ntotal == 0:
                    return []
                
                query_vector = self._validate_vector(query_vector)
                query_vector = query_vector.reshape(1, -1)
                
                k = min(k, self.index.ntotal)
                scores, indices = self.index.search(query_vector, k)
                
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx >= 0 and scores[0][i] >= threshold:
                        note_id = self.id_map.get(int(idx))
                        if note_id:
                            results.append((note_id, float(scores[0][i])))
                
                self._stats['total_searches'] += 1
                self._stats['total_search_time'] += time.time() - start_time
                
                return results
            except VectorStoreError:
                raise
            except Exception as e:
                raise VectorStoreError(f"Search failed: {str(e)}")
    
    def batch_search(
        self, 
        query_vectors: np.ndarray, 
        k: int = 5, 
        threshold: float = 0.3
    ) -> List[List[Tuple[str, float]]]:
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)
        
        results = []
        for i in range(query_vectors.shape[0]):
            try:
                result = self.search(query_vectors[i], k, threshold)
                results.append(result)
            except Exception as e:
                print(f"Batch search error at index {i}: {e}")
                results.append([])
        
        return results
    
    def get_vector_by_id(self, note_id: str) -> Optional[np.ndarray]:
        with self._lock:
            if note_id not in self.reverse_map:
                return None
            
            idx = self.reverse_map[note_id]
            try:
                vector = self.index.reconstruct(idx)
                return vector
            except Exception:
                return None
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_search_time = 0.0
            if self._stats['total_searches'] > 0:
                avg_search_time = (
                    self._stats['total_search_time'] / self._stats['total_searches']
                )
            
            return {
                'total_vectors': self.index.ntotal if self.index else 0,
                'dimension': self.dimension,
                'index_path': self.index_path,
                'initialized': self._initialized,
                'stats': {
                    'total_adds': self._stats['total_adds'],
                    'total_updates': self._stats['total_updates'],
                    'total_removes': self._stats['total_removes'],
                    'total_searches': self._stats['total_searches'],
                    'avg_search_time_ms': avg_search_time * 1000
                }
            }
    
    def save(self) -> bool:
        with self._lock:
            try:
                abs_index_path = os.path.abspath(self.index_path)
                os.makedirs(abs_index_path, exist_ok=True)
                
                index_file = os.path.join(abs_index_path, "index.faiss")
                meta_file = os.path.join(abs_index_path, "meta.json")
                
                faiss.write_index(self.index, index_file)
                
                meta = {
                    'id_map': self.id_map,
                    'reverse_map': self.reverse_map,
                    'next_idx': self._next_idx,
                    'stats': self._stats
                }
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                
                print(f"Saved FAISS index with {self.index.ntotal} vectors to {abs_index_path}")
                return True
            except Exception as e:
                print(f"Failed to save index: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def clear(self):
        with self._lock:
            self._create_new()
    
    def rebuild_index(self, note_ids: List[str], vectors: np.ndarray) -> Dict[str, Any]:
        with self._lock:
            self._create_new()
            self._stats = {
                'total_adds': 0,
                'total_updates': 0,
                'total_removes': 0,
                'total_searches': 0,
                'total_search_time': 0.0
            }
        
        return self.add_vectors(note_ids, vectors)
    
    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self.index else 0
    
    @property
    def is_ready(self) -> bool:
        return self._initialized and self.index is not None
    
    def __len__(self) -> int:
        return self.total_vectors
    
    def __contains__(self, note_id: str) -> bool:
        return note_id in self.reverse_map
