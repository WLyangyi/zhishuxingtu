import requests
import json
import time

BASE_URL = "http://localhost:8000"

def login():
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "test", "password": "test123"}
    )
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data:
            return data["access_token"]
        elif "data" in data and "access_token" in data["data"]:
            return data["data"]["access_token"]
    
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"username": "test", "password": "test123"}
    )
    if response.status_code == 200:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={"username": "test", "password": "test123"}
        )
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                return data["access_token"]
            elif "data" in data and "access_token" in data["data"]:
                return data["data"]["access_token"]
    
    raise Exception("登录失败")

def test_vector_memory(token):
    headers = {"Authorization": f"Bearer {token}"}
    session_id = "test-session-001"
    
    print("=" * 60)
    print("测试向量长期记忆功能")
    print("=" * 60)
    
    print("\n[1] 第一轮对话：告诉AI我的名字")
    response = requests.post(
        f"{BASE_URL}/api/search/chat",
        params={"message": "你好，我叫张三，我是一名Python开发者", "session_id": session_id},
        headers=headers
    )
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text[:500] if response.text else '空'}")
    if response.status_code == 200:
        result = response.json()
        print(f"AI回复: {result.get('data', {}).get('answer', '无回答')[:100]}...")
    
    print("\n[2] 第二轮对话：问AI我的名字（测试短期记忆）")
    response = requests.post(
        f"{BASE_URL}/api/search/chat",
        params={"message": "我叫什么名字？", "session_id": session_id},
        headers=headers
    )
    result = response.json()
    print(f"AI回复: {result['data']['answer']}")
    
    print("\n[3] 第三轮对话：问AI我的职业（测试向量记忆检索）")
    response = requests.post(
        f"{BASE_URL}/api/search/chat",
        params={"message": "我是做什么工作的？", "session_id": session_id},
        headers=headers
    )
    result = response.json()
    print(f"AI回复: {result['data']['answer']}")
    
    print("\n[4] 第四轮对话：新会话，测试跨会话记忆")
    new_session_id = "test-session-002"
    response = requests.post(
        f"{BASE_URL}/api/search/chat",
        params={
            "message": "你知道张三是谁吗？他是什么职业？", 
            "session_id": new_session_id
        },
        headers=headers
    )
    result = response.json()
    print(f"AI回复: {result['data']['answer']}")
    
    print("\n[5] 检查向量记忆存储状态")
    from app.services.chat_memory_store import get_chat_memory_store
    memory_store = get_chat_memory_store()
    stats = memory_store.get_stats()
    print(f"记忆存储统计: {stats}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    token = login()
    print(f"登录成功，Token: {token[:20]}...")
    test_vector_memory(token)
