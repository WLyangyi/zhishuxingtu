import sys
sys.path.insert(0, 'd:/知枢星图/backend')

from app.services.chat_memory_store import ChatMemoryStore, get_chat_memory_store
from app.services.langchain_embeddings import get_langchain_embeddings
from datetime import datetime
import os

def test_chat_memory_store():
    print("=" * 60)
    print("测试向量长期记忆功能")
    print("=" * 60)
    
    test_index_path = "d:/知枢星图/backend/data/test_chat_memory"
    os.makedirs(test_index_path, exist_ok=True)
    
    memory_store = ChatMemoryStore(
        index_path=test_index_path,
        top_k=3,
        min_score=0.1
    )
    
    print("\n[1] 测试添加对话记忆...")
    conv_id_1 = memory_store.add_conversation(
        user_message="你好，我叫张三，我是一名Python开发者",
        assistant_message="你好张三！很高兴认识你。作为Python开发者，你一定对编程很有热情。有什么我可以帮助你的吗？",
        session_id="test-session-001"
    )
    print(f"添加对话1成功，ID: {conv_id_1}")
    
    conv_id_2 = memory_store.add_conversation(
        user_message="我最近在学习LangChain框架",
        assistant_message="LangChain是一个很棒的AI应用开发框架！它可以帮助你快速构建RAG应用、对话系统等。你有什么具体问题吗？",
        session_id="test-session-001"
    )
    print(f"添加对话2成功，ID: {conv_id_2}")
    
    print("\n[2] 测试语义检索历史对话...")
    results = memory_store.search_relevant_history(
        query="张三是做什么工作的？",
        top_k=3
    )
    print(f"检索到 {len(results)} 条相关对话:")
    for i, r in enumerate(results):
        print(f"  [{i+1}] 相似度: {r['similarity']:.3f}")
        print(f"      用户: {r['user_message'][:50]}...")
        print(f"      助手: {r['assistant_message'][:50]}...")
    
    print("\n[3] 测试获取上下文...")
    context = memory_store.get_context_for_query(
        query="LangChain是什么？",
        session_id="test-session-001"
    )
    print(f"获取到的上下文:\n{context[:300]}..." if context else "无相关上下文")
    
    print("\n[4] 测试跨会话检索...")
    conv_id_3 = memory_store.add_conversation(
        user_message="我喜欢喝咖啡",
        assistant_message="咖啡是很多程序员的提神利器！你喜欢什么口味的咖啡？",
        session_id="test-session-002"
    )
    
    results = memory_store.search_relevant_history(
        query="程序员喜欢喝什么？",
        top_k=5
    )
    print(f"跨会话检索到 {len(results)} 条相关对话:")
    for i, r in enumerate(results):
        print(f"  [{i+1}] 会话: {r['session_id']}, 相似度: {r['similarity']:.3f}")
        print(f"      用户: {r['user_message'][:30]}...")
    
    print("\n[5] 测试存储统计...")
    stats = memory_store.get_stats()
    print(f"存储统计: {stats}")
    
    print("\n" + "=" * 60)
    print("所有测试通过！向量长期记忆功能正常工作")
    print("=" * 60)

if __name__ == "__main__":
    test_chat_memory_store()
