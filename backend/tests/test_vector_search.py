import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
user_site = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python313', 'site-packages')
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

import unittest
import numpy as np
import tempfile
import shutil
import time
from app.services.embedding_service import EmbeddingService, embedding_service
from app.services.vector_store import VectorStore, VectorStoreError


class TestEmbeddingService(unittest.TestCase):
    
    def setUp(self):
        self.service = embedding_service
    
    def test_service_singleton(self):
        service2 = EmbeddingService()
        self.assertIs(self.service, service2)
    
    def test_dimension_property(self):
        dim = self.service.dimension
        self.assertIsInstance(dim, int)
        self.assertGreater(dim, 0)
    
    def test_available_property(self):
        available = self.service.available
        self.assertIsInstance(available, bool)
    
    def test_embed_text_returns_correct_shape(self):
        if not self.service.available:
            self.skipTest("Embedding service not available")
        
        text = "这是一个测试文本"
        vector = self.service.embed_text(text)
        
        self.assertIsInstance(vector, np.ndarray)
        self.assertEqual(vector.shape[0], self.service.dimension)
        self.assertEqual(vector.dtype, np.float32)
    
    def test_embed_empty_text(self):
        vector = self.service.embed_text("")
        self.assertEqual(vector.shape[0], self.service.dimension)
        self.assertTrue(np.allclose(vector, np.zeros(self.service.dimension)))
    
    def test_embed_none_text(self):
        vector = self.service.embed_text(None)
        self.assertEqual(vector.shape[0], self.service.dimension)
        self.assertTrue(np.allclose(vector, np.zeros(self.service.dimension)))
    
    def test_embed_texts_batch(self):
        if not self.service.available:
            self.skipTest("Embedding service not available")
        
        texts = ["文本1", "文本2", "文本3"]
        vectors = self.service.embed_texts(texts)
        
        self.assertEqual(vectors.shape[0], len(texts))
        self.assertEqual(vectors.shape[1], self.service.dimension)
    
    def test_prepare_note_text(self):
        title = "测试标题"
        content = "这是测试内容"
        result = self.service.prepare_note_text(title, content)
        
        self.assertIn(title, result)
        self.assertIn(content, result)
    
    def test_prepare_note_text_truncation(self):
        title = "标题"
        content = "x" * 1000
        result = self.service.prepare_note_text(title, content, max_length=100)
        
        self.assertLessEqual(len(result), 100)
    
    def test_vector_normalization(self):
        if not self.service.available:
            self.skipTest("Embedding service not available")
        
        text = "测试归一化"
        vector = self.service.embed_text(text)
        
        norm = np.linalg.norm(vector)
        self.assertAlmostEqual(norm, 1.0, places=5)


class TestVectorStore(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = VectorStore(self.temp_dir, dimension=384)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        self.assertTrue(self.store.is_ready)
        self.assertEqual(self.store.total_vectors, 0)
    
    def test_add_single_vector(self):
        vector = np.random.randn(384).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        
        result = self.store.add_vector("note_1", vector)
        
        self.assertTrue(result)
        self.assertEqual(self.store.total_vectors, 1)
        self.assertIn("note_1", self.store)
    
    def test_add_vector_wrong_dimension(self):
        vector = np.random.randn(128).astype(np.float32)
        
        with self.assertRaises(VectorStoreError):
            self.store.add_vector("note_1", vector)
    
    def test_add_vectors_batch(self):
        vectors = np.random.randn(5, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        ids = [f"note_{i}" for i in range(5)]
        
        result = self.store.add_vectors(ids, vectors)
        
        self.assertEqual(result['success'], 5)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(self.store.total_vectors, 5)
    
    def test_update_vector(self):
        vector1 = np.random.randn(384).astype(np.float32)
        vector1 = vector1 / np.linalg.norm(vector1)
        self.store.add_vector("note_1", vector1)
        
        vector2 = np.random.randn(384).astype(np.float32)
        vector2 = vector2 / np.linalg.norm(vector2)
        result = self.store.update_vector("note_1", vector2)
        
        self.assertTrue(result)
        self.assertEqual(self.store.total_vectors, 1)
    
    def test_remove_vector(self):
        vector = np.random.randn(384).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        self.store.add_vector("note_1", vector)
        
        result = self.store.remove_vector("note_1")
        
        self.assertTrue(result)
        self.assertEqual(self.store.total_vectors, 0)
        self.assertNotIn("note_1", self.store)
    
    def test_remove_nonexistent_vector(self):
        result = self.store.remove_vector("nonexistent")
        self.assertFalse(result)
    
    def test_search_empty_index(self):
        query = np.random.randn(384).astype(np.float32)
        results = self.store.search(query)
        
        self.assertEqual(len(results), 0)
    
    def test_search_returns_correct_results(self):
        base_vector = np.random.randn(384).astype(np.float32)
        base_vector = base_vector / np.linalg.norm(base_vector)
        
        similar_vector = base_vector + np.random.randn(384).astype(np.float32) * 0.1
        similar_vector = similar_vector / np.linalg.norm(similar_vector)
        
        different_vector = np.random.randn(384).astype(np.float32)
        different_vector = different_vector / np.linalg.norm(different_vector)
        
        self.store.add_vector("similar_note", similar_vector)
        self.store.add_vector("different_note", different_vector)
        
        results = self.store.search(base_vector, k=2, threshold=-1.0)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "similar_note")
        self.assertGreater(results[0][1], results[1][1])
    
    def test_search_with_threshold(self):
        vector = np.random.randn(384).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        
        self.store.add_vector("note_1", vector)
        
        query = np.random.randn(384).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        results = self.store.search(query, k=1, threshold=0.99)
        
        self.assertEqual(len(results), 0)
    
    def test_batch_search(self):
        vectors = np.random.randn(3, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        for i, v in enumerate(vectors):
            self.store.add_vector(f"note_{i}", v)
        
        query_vectors = np.random.randn(2, 384).astype(np.float32)
        query_vectors = query_vectors / np.linalg.norm(query_vectors, axis=1, keepdims=True)
        
        results = self.store.batch_search(query_vectors, k=2, threshold=-1.0)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(len(results[0]), 2)
        self.assertEqual(len(results[1]), 2)
    
    def test_save_and_load(self):
        vectors = np.random.randn(3, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        for i, v in enumerate(vectors):
            self.store.add_vector(f"note_{i}", v)
        
        self.assertTrue(self.store.save())
        
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "index.faiss")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "meta.json")))
        
        new_store = VectorStore(self.temp_dir, dimension=384)
        
        self.assertEqual(new_store.total_vectors, 3)
        self.assertIn("note_0", new_store)
        self.assertIn("note_1", new_store)
        self.assertIn("note_2", new_store)
    
    def test_get_stats(self):
        stats = self.store.get_stats()
        
        self.assertIn('total_vectors', stats)
        self.assertIn('dimension', stats)
        self.assertIn('stats', stats)
        self.assertEqual(stats['dimension'], 384)
    
    def test_clear(self):
        vector = np.random.randn(384).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        self.store.add_vector("note_1", vector)
        
        self.store.clear()
        
        self.assertEqual(self.store.total_vectors, 0)
    
    def test_rebuild_index(self):
        old_vector = np.random.randn(384).astype(np.float32)
        old_vector = old_vector / np.linalg.norm(old_vector)
        self.store.add_vector("old_note", old_vector)
        
        new_vectors = np.random.randn(2, 384).astype(np.float32)
        new_vectors = new_vectors / np.linalg.norm(new_vectors, axis=1, keepdims=True)
        new_ids = ["new_note_1", "new_note_2"]
        
        result = self.store.rebuild_index(new_ids, new_vectors)
        
        self.assertEqual(result['success'], 2)
        self.assertEqual(self.store.total_vectors, 2)
        self.assertNotIn("old_note", self.store)
        self.assertIn("new_note_1", self.store)


class TestVectorSearchIntegration(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = VectorStore(self.temp_dir, dimension=384)
        self.service = embedding_service
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_semantic_search_similarity(self):
        if not self.service.available:
            self.skipTest("Embedding service not available")
        
        texts = [
            "Vue3 组合式 API 的使用方法",
            "React Hooks 入门教程",
            "机器学习基础概念",
            "Python 数据分析实战",
            "前端框架比较分析"
        ]
        
        for i, text in enumerate(texts):
            vector = self.service.embed_text(text)
            self.store.add_vector(f"note_{i}", vector)
        
        query = "前端开发学习"
        query_vector = self.service.embed_text(query)
        
        results = self.store.search(query_vector, k=3, threshold=0.0)
        
        self.assertEqual(len(results), 3)
        
        top_ids = [r[0] for r in results]
        self.assertIn("note_0", top_ids)
        self.assertIn("note_1", top_ids)
        self.assertIn("note_4", top_ids)
    
    def test_search_performance(self):
        if not self.service.available:
            self.skipTest("Embedding service not available")
        
        for i in range(100):
            text = f"测试笔记 {i} 的内容，包含一些随机文字"
            vector = self.service.embed_text(text)
            self.store.add_vector(f"note_{i}", vector)
        
        query = "测试搜索性能"
        query_vector = self.service.embed_text(query)
        
        start_time = time.time()
        for _ in range(10):
            results = self.store.search(query_vector, k=10)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        self.assertLess(avg_time, 0.1)
        
        stats = self.store.get_stats()
        self.assertEqual(stats['total_vectors'], 100)


class TestErrorHandling(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = VectorStore(self.temp_dir, dimension=384)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_none_vector(self):
        with self.assertRaises(VectorStoreError):
            self.store.add_vector("note_1", None)
    
    def test_add_list_as_vector(self):
        vector_list = [0.1] * 384
        result = self.store.add_vector("note_1", vector_list)
        self.assertTrue(result)
    
    def test_batch_search_with_single_vector(self):
        vector = np.random.randn(384).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        self.store.add_vector("note_1", vector)
        
        query = np.random.randn(384).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        results = self.store.batch_search(query, k=1)
        
        self.assertEqual(len(results), 1)
    
    def test_concurrent_access(self):
        import threading
        
        vectors = np.random.randn(10, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        errors = []
        
        def add_vectors(start_idx):
            try:
                for i in range(start_idx, start_idx + 5):
                    self.store.add_vector(f"note_{i}", vectors[i % 10])
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=add_vectors, args=(0,)),
            threading.Thread(target=add_vectors, args=(5,))
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingService))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorStore))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorSearchIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("向量化和 FAISS 检索功能测试")
    print("=" * 60)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\n出错的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")
