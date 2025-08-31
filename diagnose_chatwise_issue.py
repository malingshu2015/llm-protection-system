#!/usr/bin/env python3
"""
诊断Chatwise连接问题的脚本
"""
import requests
import json
import time
import sys

def test_firewall_health():
    """测试防火墙健康状态"""
    print("🔍 检查防火墙健康状态...")
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 防火墙健康状态: {data.get('status', 'unknown')}")
            print(f"📊 Ollama可用: {data.get('ollama_available', 'unknown')}")
            print(f"🏷️ 版本: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ 防火墙健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 防火墙连接失败: {e}")
        return False

def test_models_endpoint():
    """测试模型列表端点"""
    print("\n🔍 检查模型列表端点...")
    try:
        headers = {"Authorization": "Bearer cherry-studio-key"}
        response = requests.get("http://localhost:8081/v1/models", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            print(f"✅ 模型列表获取成功，共 {len(models)} 个模型")
            for model in models[:3]:  # 显示前3个
                print(f"   📦 {model['id']} ({model.get('owned_by', 'unknown')})")
            if len(models) > 3:
                print(f"   ... 还有 {len(models) - 3} 个模型")
            return True
        else:
            print(f"❌ 模型列表获取失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 模型列表请求失败: {e}")
        return False

def test_chat_endpoint():
    """测试聊天端点"""
    print("\n🔍 检查聊天端点...")
    try:
        headers = {
            "Authorization": "Bearer cherry-studio-key",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tinyllama:latest",
            "messages": [{"role": "user", "content": "Say 'Hello' in one word"}],
            "stream": False,
            "max_tokens": 10
        }
        
        print("📤 发送聊天请求...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:8081/v1/chat/completions", 
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        response_time = time.time() - start_time
        print(f"⏱️ 响应时间: {response_time:.2f}秒")
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                message = data['choices'][0].get('message', {})
                content = message.get('content', '').strip()
                print(f"✅ 聊天响应成功: {content}")
                return True
            else:
                print(f"❌ 聊天响应格式异常: {data}")
                return False
        else:
            print(f"❌ 聊天请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 聊天请求超时")
        return False
    except Exception as e:
        print(f"❌ 聊天请求失败: {e}")
        return False

def test_ollama_direct():
    """直接测试Ollama"""
    print("\n🔍 直接检查Ollama服务...")
    try:
        # 检查模型列表
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"✅ Ollama模型列表: {len(models)} 个模型")
            
            # 测试简单生成
            payload = {
                "model": "tinyllama:latest",
                "prompt": "Hi",
                "stream": False
            }
            response = requests.post(
                "http://localhost:11434/api/generate", 
                json=payload, 
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '').strip()
                print(f"✅ Ollama直接响应: {response_text[:50]}...")
                return True
            else:
                print(f"❌ Ollama生成失败: {response.status_code}")
                return False
        else:
            print(f"❌ Ollama模型列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama直接测试失败: {e}")
        return False

def test_cors_headers():
    """测试CORS头"""
    print("\n🔍 检查CORS配置...")
    try:
        headers = {
            "Origin": "http://localhost:3000",
            "Authorization": "Bearer cherry-studio-key"
        }
        response = requests.options("http://localhost:8081/v1/models", headers=headers, timeout=5)
        cors_headers = {
            key: value for key, value in response.headers.items() 
            if key.lower().startswith('access-control')
        }
        if cors_headers:
            print("✅ CORS头存在:")
            for key, value in cors_headers.items():
                print(f"   {key}: {value}")
            return True
        else:
            print("⚠️ 未发现CORS头")
            return False
    except Exception as e:
        print(f"❌ CORS检查失败: {e}")
        return False

def main():
    print("🚀 开始诊断Chatwise连接问题...\n")
    
    tests = [
        ("防火墙健康检查", test_firewall_health),
        ("模型列表端点", test_models_endpoint),
        ("CORS配置检查", test_cors_headers),
        ("Ollama直接测试", test_ollama_direct),
        ("聊天端点测试", test_chat_endpoint)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        results[test_name] = test_func()
    
    print(f"\n{'='*50}")
    print("📋 诊断结果汇总:")
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    failed_tests = [name for name, success in results.items() if not success]
    if failed_tests:
        print(f"\n🔥 失败的测试: {', '.join(failed_tests)}")
        print("💡 建议检查防火墙日志和配置")
    else:
        print("\n🎉 所有测试通过！Chatwise应该可以正常连接。")

if __name__ == "__main__":
    main()