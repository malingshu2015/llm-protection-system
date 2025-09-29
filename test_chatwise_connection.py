#!/usr/bin/env python3
"""
Chatwise连接测试脚本
"""

import requests
import json

def test_connection():
    base_url = "http://localhost:8082"
    api_key = "chatwise-key"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("🔍 测试Chatwise连接...")
    print(f"服务器地址: {base_url}")
    print(f"API密钥: {api_key}")
    print("="*50)
    
    # 测试1: 健康检查
    try:
        print("1. 测试健康检查...")
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.json()}")
            print("   ✅ 健康检查通过")
        else:
            print(f"   ❌ 健康检查失败")
    except Exception as e:
        print(f"   ❌ 健康检查错误: {e}")
    
    print()
    
    # 测试2: 模型列表
    try:
        print("2. 测试模型列表...")
        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(f"   模型数量: {len(models.get('data', []))}")
            if models.get('data'):
                print(f"   第一个模型: {models['data'][0].get('id', 'unknown')}")
            print("   ✅ 模型列表获取成功")
        else:
            print(f"   ❌ 模型列表获取失败: {response.text}")
    except Exception as e:
        print(f"   ❌ 模型列表错误: {e}")
    
    print()
    
    # 测试3: 聊天完成
    try:
        print("3. 测试聊天完成...")
        chat_data = {
            "model": "qwen3:latest",
            "messages": [
                {"role": "user", "content": "你好，这是连接测试"}
            ],
            "stream": False
        }
        response = requests.post(
            f"{base_url}/v1/chat/completions", 
            headers=headers, 
            json=chat_data, 
            timeout=30
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and result['choices']:
                content = result['choices'][0]['message']['content']
                print(f"   响应内容: {content[:100]}...")
                print("   ✅ 聊天完成测试成功")
            else:
                print(f"   ❌ 响应格式异常: {result}")
        else:
            print(f"   ❌ 聊天完成失败: {response.text}")
    except Exception as e:
        print(f"   ❌ 聊天完成错误: {e}")
    
    print()
    print("="*50)
    print("💡 Chatwise配置建议:")
    print(f"   API Base URL: {base_url}/v1")
    print(f"   API Key: {api_key}")
    print("   推荐模型: qwen3:latest")

if __name__ == "__main__":
    test_connection()