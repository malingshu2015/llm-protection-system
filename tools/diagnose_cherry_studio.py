#!/usr/bin/env python3
"""
Cherry Studio 问题诊断工具

这个工具帮助诊断Cherry Studio无法连接到LLM安全防火墙的具体问题。
"""

import requests
import json
import subprocess
import sys
import time
from typing import Dict, Any, List, Tuple

def check_service_running() -> Tuple[bool, str]:
    """检查防火墙服务是否运行"""
    try:
        response = requests.get("http://localhost:8082/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"服务正常运行 (版本: {data.get('version', 'unknown')})"
        else:
            return False, f"服务响应异常: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到服务 - 服务可能未启动"
    except Exception as e:
        return False, f"检查服务时出错: {e}"

def check_port_usage() -> Tuple[bool, str]:
    """检查端口8082是否被占用"""
    try:
        result = subprocess.run(['lsof', '-i', ':8082'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # 有标题行和数据行
                return True, f"端口8082被占用:\n{result.stdout}"
            else:
                return False, "端口8082未被占用"
        else:
            return False, "端口8082未被占用"
    except subprocess.TimeoutExpired:
        return False, "检查端口超时"
    except FileNotFoundError:
        return False, "lsof命令不可用，无法检查端口"
    except Exception as e:
        return False, f"检查端口时出错: {e}"

def test_api_endpoints() -> Dict[str, Any]:
    """测试各个API端点"""
    endpoints = {
        "健康检查": "/health",
        "OpenAI模型列表": "/v1/models",
        "Ollama模型列表": "/api/v1/ollama/models",
        "Cherry Studio专用": "/api/v1/ollama/v1/models"
    }
    
    results = {}
    headers = {"Authorization": "Bearer cherry-studio-key"}
    
    for name, endpoint in endpoints.items():
        try:
            url = f"http://localhost:8082{endpoint}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "models" in data:
                    model_count = len(data["models"])
                    results[name] = {"status": "✅ 成功", "details": f"{model_count}个模型"}
                else:
                    results[name] = {"status": "✅ 成功", "details": "响应正常"}
            elif response.status_code == 403:
                results[name] = {"status": "❌ 失败", "details": "API密钥验证失败"}
            else:
                results[name] = {"status": "❌ 失败", "details": f"HTTP {response.status_code}"}
        except Exception as e:
            results[name] = {"status": "❌ 异常", "details": str(e)}
    
    return results

def test_chat_functionality() -> Tuple[bool, str]:
    """测试聊天功能"""
    try:
        payload = {
            "model": "tinyllama:latest",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }
        
        headers = {
            "Authorization": "Bearer cherry-studio-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "http://localhost:8082/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return True, "聊天功能正常"
            else:
                return False, "响应格式不正确"
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return False, f"测试异常: {e}"

def check_ollama_service() -> Tuple[bool, str]:
    """检查Ollama服务状态"""
    try:
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            model_count = len(lines) - 1 if len(lines) > 1 else 0  # 减去标题行
            return True, f"Ollama正常运行，{model_count}个模型可用"
        else:
            return False, f"Ollama命令失败: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Ollama命令超时"
    except FileNotFoundError:
        return False, "Ollama未安装或不在PATH中"
    except Exception as e:
        return False, f"检查Ollama时出错: {e}"

def generate_cherry_studio_configs() -> List[Dict[str, str]]:
    """生成Cherry Studio配置建议"""
    return [
        {
            "name": "配置1 - OpenAI兼容 (推荐)",
            "api_type": "OpenAI Compatible",
            "base_url": "http://localhost:8082/v1",
            "api_key": "cherry-studio-key"
        },
        {
            "name": "配置2 - Ollama兼容",
            "api_type": "Ollama",
            "base_url": "http://localhost:8082/api/v1/ollama",
            "api_key": "cherry-studio-key"
        },
        {
            "name": "配置3 - Cherry Studio专用",
            "api_type": "Ollama",
            "base_url": "http://localhost:8082/api/v1/ollama/v1",
            "api_key": "cherry-studio-key"
        }
    ]

def main():
    """主诊断流程"""
    print("🍒 Cherry Studio 问题诊断工具")
    print("=" * 60)
    
    # 1. 检查服务状态
    print("\n1️⃣ 检查防火墙服务状态...")
    service_ok, service_msg = check_service_running()
    print(f"   {'✅' if service_ok else '❌'} {service_msg}")
    
    if not service_ok:
        print("\n🚨 防火墙服务未运行！")
        print("请先启动服务: WEB_PORT=8082 python3 -m src.main")
        return False
    
    # 2. 检查端口占用
    print("\n2️⃣ 检查端口占用情况...")
    port_ok, port_msg = check_port_usage()
    print(f"   {'✅' if port_ok else '⚠️'} {port_msg}")
    
    # 3. 检查Ollama服务
    print("\n3️⃣ 检查Ollama服务...")
    ollama_ok, ollama_msg = check_ollama_service()
    print(f"   {'✅' if ollama_ok else '⚠️'} {ollama_msg}")
    
    # 4. 测试API端点
    print("\n4️⃣ 测试API端点...")
    api_results = test_api_endpoints()
    for name, result in api_results.items():
        print(f"   {result['status']} {name}: {result['details']}")
    
    # 5. 测试聊天功能
    print("\n5️⃣ 测试聊天功能...")
    chat_ok, chat_msg = test_chat_functionality()
    print(f"   {'✅' if chat_ok else '❌'} {chat_msg}")
    
    # 6. 生成配置建议
    print("\n6️⃣ Cherry Studio 配置建议:")
    configs = generate_cherry_studio_configs()
    for i, config in enumerate(configs, 1):
        print(f"\n   {config['name']}:")
        print(f"   API类型: {config['api_type']}")
        print(f"   Base URL: {config['base_url']}")
        print(f"   API Key: {config['api_key']}")
    
    # 7. 诊断结果总结
    print("\n" + "=" * 60)
    print("📊 诊断结果总结:")
    
    issues = []
    if not service_ok:
        issues.append("防火墙服务未运行")
    if not ollama_ok:
        issues.append("Ollama服务异常")
    if not chat_ok:
        issues.append("聊天功能异常")
    
    failed_endpoints = [name for name, result in api_results.items() 
                       if "失败" in result["status"] or "异常" in result["status"]]
    if failed_endpoints:
        issues.append(f"API端点异常: {', '.join(failed_endpoints)}")
    
    if not issues:
        print("✅ 所有检查都通过！Cherry Studio应该可以正常工作。")
        print("\n🎯 建议使用配置1 (OpenAI兼容) 进行连接。")
        print("如果仍有问题，请检查Cherry Studio中的API密钥是否正确设置。")
    else:
        print("❌ 发现以下问题:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n🔧 请根据上述问题进行修复后重试。")
    
    return len(issues) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
