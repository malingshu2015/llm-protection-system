#!/usr/bin/env python3
"""
Cherry Studio 实时调试工具

模拟Cherry Studio的请求行为，帮助诊断连接问题
"""

import requests
import json
import time
from typing import Dict, Any

def test_cherry_studio_connection():
    """模拟Cherry Studio的连接测试"""
    print("🍒 Cherry Studio 连接调试工具")
    print("=" * 50)
    
    # 测试配置
    configs = [
        {
            "name": "当前配置 - Ollama兼容",
            "base_url": "http://localhost:8082/api/v1/ollama/v1",
            "headers": {
                "Authorization": "Bearer cherry-studio-key",
                "Content-Type": "application/json"
            }
        },
        {
            "name": "推荐配置 - OpenAI兼容", 
            "base_url": "http://localhost:8082/v1",
            "headers": {
                "Authorization": "Bearer cherry-studio-key",
                "Content-Type": "application/json"
            }
        },
        {
            "name": "基础配置",
            "base_url": "http://localhost:8082",
            "headers": {
                "Authorization": "Bearer cherry-studio-key",
                "Content-Type": "application/json"
            }
        }
    ]
    
    for config in configs:
        print(f"\n🧪 测试 {config['name']}")
        print(f"Base URL: {config['base_url']}")
        
        # 1. 测试模型列表
        print("\n1️⃣ 测试模型列表...")
        model_endpoints = [
            "/models",
            "/v1/models", 
            "/api/v1/ollama/models",
            "/api/v1/ollama/v1/models"
        ]
        
        for endpoint in model_endpoints:
            try:
                url = config['base_url'] + endpoint
                response = requests.get(url, headers=config['headers'], timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get('models', []))
                    print(f"   ✅ {endpoint} - {model_count}个模型")
                    break
                else:
                    print(f"   ❌ {endpoint} - HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ {endpoint} - 错误: {str(e)[:50]}")
        
        # 2. 测试聊天功能
        print("\n2️⃣ 测试聊天功能...")
        chat_endpoints = [
            "/chat/completions",
            "/v1/chat/completions",
            "/api/v1/ollama/chat",
            "/api/v1/ollama/v1/chat/completions"
        ]
        
        payload = {
            "model": "tinyllama:latest",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }
        
        for endpoint in chat_endpoints:
            try:
                url = config['base_url'] + endpoint
                response = requests.post(url, headers=config['headers'], 
                                       json=payload, timeout=10)
                if response.status_code == 200:
                    print(f"   ✅ {endpoint} - 聊天成功")
                    break
                else:
                    print(f"   ❌ {endpoint} - HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ {endpoint} - 错误: {str(e)[:50]}")
        
        print("-" * 50)

def simulate_cherry_studio_requests():
    """模拟Cherry Studio的具体请求"""
    print("\n🔍 模拟Cherry Studio请求行为")
    print("=" * 50)
    
    # Cherry Studio通常的请求序列
    base_url = "http://localhost:8082/api/v1/ollama/v1"
    headers = {
        "Authorization": "Bearer cherry-studio-key",
        "Content-Type": "application/json",
        "User-Agent": "Cherry Studio"
    }
    
    # 1. 连接测试 - 通常发送空请求或简单请求
    print("\n1️⃣ 模拟连接测试...")
    try:
        # 测试responses端点（Cherry Studio特有）
        response = requests.post(
            f"{base_url}/responses",
            headers=headers,
            json={"model": "tinyllama:latest"},
            timeout=5
        )
        print(f"   连接测试: HTTP {response.status_code}")
        if response.status_code == 200:
            print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   连接测试失败: {e}")
    
    # 2. 获取模型列表
    print("\n2️⃣ 模拟获取模型列表...")
    try:
        response = requests.get(f"{base_url}/models", headers=headers, timeout=5)
        print(f"   模型列表: HTTP {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            print(f"   可用模型: {models[:3]}...")  # 只显示前3个
    except Exception as e:
        print(f"   获取模型失败: {e}")
    
    # 3. 发送聊天请求
    print("\n3️⃣ 模拟聊天请求...")
    try:
        payload = {
            "model": "tinyllama:latest",
            "messages": [{"role": "user", "content": "测试消息"}],
            "stream": False,
            "temperature": 0.7
        }
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        print(f"   聊天请求: HTTP {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content'][:100]
                print(f"   AI回复: {content}...")
    except Exception as e:
        print(f"   聊天请求失败: {e}")

def check_api_key_validation():
    """检查API密钥验证"""
    print("\n🔑 API密钥验证测试")
    print("=" * 50)
    
    test_keys = [
        ("正确密钥", "cherry-studio-key"),
        ("错误密钥", "wrong-key"),
        ("空密钥", ""),
        ("无Bearer前缀", None)
    ]
    
    for name, key in test_keys:
        print(f"\n测试 {name}:")
        
        if key is None:
            headers = {"Content-Type": "application/json"}
        else:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        
        try:
            response = requests.get(
                "http://localhost:8082/v1/models",
                headers=headers,
                timeout=5
            )
            print(f"   结果: HTTP {response.status_code}")
            if response.status_code == 403:
                print("   ❌ API密钥验证失败")
            elif response.status_code == 200:
                print("   ✅ API密钥验证成功")
        except Exception as e:
            print(f"   错误: {e}")

def main():
    """主函数"""
    print("🚀 开始Cherry Studio调试...")
    
    # 1. 基础连接测试
    test_cherry_studio_connection()
    
    # 2. 模拟Cherry Studio行为
    simulate_cherry_studio_requests()
    
    # 3. API密钥验证测试
    check_api_key_validation()
    
    print("\n" + "=" * 50)
    print("📋 调试建议:")
    print("1. 如果所有测试都通过，问题可能在Cherry Studio客户端")
    print("2. 检查Cherry Studio的网络设置和代理配置")
    print("3. 尝试重启Cherry Studio应用")
    print("4. 确认Cherry Studio版本支持自定义API")
    print("\n🎯 推荐配置:")
    print("   API类型: OpenAI Compatible")
    print("   Base URL: http://localhost:8082/v1")
    print("   API Key: cherry-studio-key")

if __name__ == "__main__":
    main()
