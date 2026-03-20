import requests
import json

BASE_URL = "http://localhost:8001/api/prompt-chains"

def test_chain_apis():
    print("=== 测试提示词链API ===\n")
    
    print("1. 获取预设链模板...")
    response = requests.get(f"{BASE_URL}/presets")
    print(f"状态码: {response.status_code}")
    presets = response.json()["data"]
    print(f"预设链数量: {len(presets)}")
    for p in presets:
        print(f"  - {p['type']}: {p['name']}")
    print()
    
    print("2. 创建自定义链...")
    chain_data = {
        "name": "测试分析链",
        "description": "用于测试的简单分析链",
        "steps": [
            {
                "step_order": 1,
                "step_name": "分析内容",
                "prompt_template": "请分析以下内容的主题：\n\n{content}\n\n请用一句话总结主题：",
                "input_mapping": "{\"content\": \"input.content\"}"
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/", json=chain_data)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        chain = response.json()["data"]
        chain_id = chain["id"]
        print(f"创建成功，链ID: {chain_id}")
    else:
        print(f"创建失败: {response.text}")
        return
    print()
    
    print("3. 获取链列表...")
    response = requests.get(f"{BASE_URL}/")
    print(f"状态码: {response.status_code}")
    chains = response.json()["data"]
    print(f"链数量: {len(chains)}")
    print()
    
    print("4. 执行链...")
    execute_data = {
        "content": "Vue3是一个渐进式JavaScript框架，它提供了组合式API、更好的TypeScript支持和更快的渲染性能。"
    }
    response = requests.post(f"{BASE_URL}/{chain_id}/execute", json=execute_data)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()["data"]
        print(f"执行成功: {result['success']}")
        if result['success']:
            print(f"输出: {result['output'][:100]}...")
        print(f"执行ID: {result['execution_id']}")
    else:
        print(f"执行失败: {response.text}")
    print()
    
    print("5. 获取执行记录...")
    response = requests.get(f"{BASE_URL}/{chain_id}/executions")
    print(f"状态码: {response.status_code}")
    executions = response.json()["data"]
    print(f"执行记录数: {len(executions)}")
    print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_chain_apis()
