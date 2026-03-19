import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
user_site = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python313', 'site-packages')
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

import numpy as np
import tempfile
import shutil
import time
from app.services.vector_store import VectorStore, VectorStoreError


def test_vector_store_basic():
    print("\n" + "="*60)
    print("测试 1: 向量存储基本功能")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    try:
        store = VectorStore(temp_dir, dimension=384)
        
        print(f"✓ 初始化成功，维度: {store.dimension}")
        print(f"✓ 初始向量数: {store.total_vectors}")
        
        vector = np.random.randn(384).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        
        result = store.add_vector("note_1", vector)
        print(f"✓ 添加向量成功: {result}")
        print(f"✓ 当前向量数: {store.total_vectors}")
        
        results = store.search(vector, k=1, threshold=-1.0)
        print(f"✓ 搜索结果: {len(results)} 条")
        if results:
            print(f"  - ID: {results[0][0]}, 相似度: {results[0][1]:.4f}")
        
        vector2 = np.random.randn(384).astype(np.float32)
        vector2 = vector2 / np.linalg.norm(vector2)
        result = store.update_vector("note_1", vector2)
        print(f"✓ 更新向量成功: {result}")
        
        result = store.remove_vector("note_1")
        print(f"✓ 删除向量成功: {result}")
        print(f"✓ 删除后向量数: {store.total_vectors}")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_batch_operations():
    print("\n" + "="*60)
    print("测试 2: 批量操作")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    try:
        store = VectorStore(temp_dir, dimension=384)
        
        vectors = np.random.randn(10, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        ids = [f"note_{i}" for i in range(10)]
        
        result = store.add_vectors(ids, vectors)
        print(f"✓ 批量添加: 成功 {result['success']}, 失败 {result['failed']}")
        print(f"✓ 当前向量数: {store.total_vectors}")
        
        query_vectors = np.random.randn(3, 384).astype(np.float32)
        query_vectors = query_vectors / np.linalg.norm(query_vectors, axis=1, keepdims=True)
        
        batch_results = store.batch_search(query_vectors, k=5, threshold=-1.0)
        print(f"✓ 批量搜索: {len(batch_results)} 个查询")
        for i, results in enumerate(batch_results):
            print(f"  - 查询 {i+1}: {len(results)} 条结果")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_persistence():
    print("\n" + "="*60)
    print("测试 3: 持久化存储")
    print("="*60)
    
    test_dir = None
    for base_path in ['C:/temp', 'D:/temp', 'E:/temp']:
        try:
            os.makedirs(base_path, exist_ok=True)
            if os.access(base_path, os.W_OK):
                test_dir = os.path.join(base_path, 'zhishuxingtu_test_faiss')
                break
        except:
            continue
    
    if not test_dir:
        test_dir = 'C:/temp/zhishuxingtu_test_faiss'
    
    try:
        os.makedirs(test_dir, exist_ok=True)
        
        for f in os.listdir(test_dir):
            try:
                os.remove(os.path.join(test_dir, f))
            except:
                pass
        
        store1 = VectorStore(test_dir, dimension=384)
        
        vectors = np.random.randn(5, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        for i, v in enumerate(vectors):
            store1.add_vector(f"note_{i}", v)
        
        print(f"✓ 添加了 {store1.total_vectors} 个向量")
        
        save_result = store1.save()
        print(f"✓ 保存索引: {save_result}")
        
        index_file = os.path.join(test_dir, "index.faiss")
        meta_file = os.path.join(test_dir, "meta.json")
        print(f"  - index.faiss 存在: {os.path.exists(index_file)}")
        print(f"  - meta.json 存在: {os.path.exists(meta_file)}")
        
        if not save_result:
            print("✗ 保存失败，跳过加载测试")
            return False
        
        store2 = VectorStore(test_dir, dimension=384)
        print(f"✓ 重新加载索引")
        print(f"✓ 加载后向量数: {store2.total_vectors}")
        
        for i in range(5):
            if f"note_{i}" in store2:
                print(f"  - note_{i} 存在于索引中")
        
        return store2.total_vectors == 5
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            shutil.rmtree(test_dir, ignore_errors=True)
        except:
            pass


def test_search_performance():
    print("\n" + "="*60)
    print("测试 4: 搜索性能")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    try:
        store = VectorStore(temp_dir, dimension=384)
        
        print("正在添加 1000 个向量...")
        vectors = np.random.randn(1000, 384).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        start = time.time()
        for i, v in enumerate(vectors):
            store.add_vector(f"note_{i}", v)
        add_time = time.time() - start
        print(f"✓ 添加 1000 个向量耗时: {add_time:.3f} 秒")
        
        query = np.random.randn(384).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        print("正在执行 100 次搜索...")
        start = time.time()
        for _ in range(100):
            results = store.search(query, k=10, threshold=-1.0)
        search_time = time.time() - start
        
        avg_time = search_time / 100
        print(f"✓ 100 次搜索总耗时: {search_time:.3f} 秒")
        print(f"✓ 平均每次搜索: {avg_time*1000:.2f} 毫秒")
        
        stats = store.get_stats()
        print(f"✓ 统计信息:")
        print(f"  - 总向量数: {stats['total_vectors']}")
        print(f"  - 总搜索次数: {stats['stats']['total_searches']}")
        print(f"  - 平均搜索时间: {stats['stats']['avg_search_time_ms']:.2f} 毫秒")
        
        return avg_time < 0.1
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_error_handling():
    print("\n" + "="*60)
    print("测试 5: 错误处理")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    try:
        store = VectorStore(temp_dir, dimension=384)
        
        print("测试错误维度...")
        try:
            wrong_vector = np.random.randn(128).astype(np.float32)
            store.add_vector("note_1", wrong_vector)
            print("✗ 应该抛出异常")
            return False
        except VectorStoreError as e:
            print(f"✓ 正确捕获维度错误: {str(e)[:50]}...")
        
        print("测试 None 向量...")
        try:
            store.add_vector("note_2", None)
            print("✗ 应该抛出异常")
            return False
        except VectorStoreError as e:
            print(f"✓ 正确捕获 None 错误: {str(e)[:50]}...")
        
        print("测试删除不存在的向量...")
        result = store.remove_vector("nonexistent")
        print(f"✓ 删除不存在的向量返回: {result}")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    print("\n" + "="*60)
    print("向量化和 FAISS 检索功能验证")
    print("="*60)
    
    results = []
    
    results.append(("基本功能", test_vector_store_basic()))
    results.append(("批量操作", test_batch_operations()))
    results.append(("持久化存储", test_persistence()))
    results.append(("搜索性能", test_search_performance()))
    results.append(("错误处理", test_error_handling()))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
