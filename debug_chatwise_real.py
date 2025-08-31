#!/usr/bin/env python3
"""
ChatWise 实际连接问题调试工具
模拟 ChatWise 的真实行为进行深入诊断
"""

import requests
import json
import time
import sys
from urllib.parse import urljoin

class ChatWiseRealDebugger:
    def __init__(self, base_url="http://localhost:8081", api_key="chatwise-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ChatWise/1.0"  # 模拟ChatWise的User-Agent
        }
        
    def print_status(self, message, status="INFO"):
        """打印状态信息"""
        status_colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m", 
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "RESET": "\033[0m"
        }
        color = status_colors.get(status, status_colors["INFO"])
        reset = status_colors["RESET"]
        print(f"{color}[{status}]{reset} {message}")
        
    def test_health_check(self):
        """测试健康检查 - ChatWise首先会做这个"""
        self.print_status("🏥 测试健康检查...")
        
        try:
            url = urljoin(self.base_url, "/health")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                self.print_status("✅ 健康检查成功", "SUCCESS")
                return True
            else:
                self.print_status(f"❌ 健康检查失败: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.print_status(f"❌ 健康检查异常: {e}", "ERROR")
            return False
    
    def test_models_with_different_endpoints(self):
        """测试不同的模型端点"""
        self.print_status("📋 测试模型端点...")
        
        endpoints = [
            "/v1/models",
            "/api/v1/models", 
            "/api/v1/ollama/models",
            "/api/v1/ollama/v1/models"
        ]
        
        for endpoint in endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        models = [model["id"] for model in data["data"]]
                        self.print_status(f"✅ {endpoint}: {len(models)}个模型", "SUCCESS")
                        print(f"    模型: {', '.join(models[:3])}...")
                    else:
                        self.print_status(f"⚠️  {endpoint}: 非标准格式", "WARNING")
                else:
                    self.print_status(f"❌ {endpoint}: HTTP {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.print_status(f"❌ {endpoint}: {e}", "ERROR")
    
    def test_chat_completions_detailed(self):
        """详细测试聊天完成端点"""
        self.print_status("💬 详细测试聊天完成...")
        
        # 测试不同的请求体格式
        test_cases = [
            {
                "name": "标准OpenAI格式",
                "endpoint": "/v1/chat/completions",
                "body": {
                    "model": "qwen3:latest",
                    "messages": [{"role": "user", "content": "Hello from ChatWise"}],
                    "stream": False,
                    "max_tokens": 100
                }
            },
            {
                "name": "简化格式",
                "endpoint": "/v1/chat/completions", 
                "body": {
                    "model": "qwen3:latest",
                    "messages": [{"role": "user", "content": "测试消息"}],
                    "stream": False
                }
            },
            {
                "name": "Ollama端点",
                "endpoint": "/api/v1/ollama/v1/chat/completions",
                "body": {
                    "model": "qwen3:latest",
                    "messages": [{"role": "user", "content": "Ollama测试"}],
                    "stream": False
                }
            }
        ]
        
        for test_case in test_cases:
            self.print_status(f"🧪 测试: {test_case['name']}")
            
            try:
                url = urljoin(self.base_url, test_case['endpoint'])
                
                # 记录请求详情
                print(f"    URL: {url}")
                print(f"    Body: {json.dumps(test_case['body'], ensure_ascii=False)}")
                
                response = requests.post(
                    url, 
                    headers=self.headers, 
                    json=test_case['body'], 
                    timeout=60  # 延长超时时间
                )
                
                print(f"    状态码: {response.status_code}")
                print(f"    响应头: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0].get("message", {}).get("content", "")
                            self.print_status(f"✅ 成功: {content[:50]}...", "SUCCESS")
                        else:
                            self.print_status("⚠️  响应格式异常", "WARNING")
                            print(f"    响应: {response.text[:200]}...")
                    except json.JSONDecodeError:
                        self.print_status("❌ 响应不是有效JSON", "ERROR")
                        print(f"    响应: {response.text[:200]}...")
                else:
                    self.print_status(f"❌ 失败: HTTP {response.status_code}", "ERROR")
                    print(f"    错误: {response.text[:200]}...")
                    
            except requests.exceptions.Timeout:
                self.print_status("❌ 请求超时", "ERROR")
            except Exception as e:
                self.print_status(f"❌ 异常: {e}", "ERROR")
            
            print()
    
    def test_streaming_chat(self):
        """测试流式聊天"""
        self.print_status("🌊 测试流式聊天...")
        
        try:
            url = urljoin(self.base_url, "/v1/chat/completions")
            body = {
                "model": "qwen3:latest",
                "messages": [{"role": "user", "content": "你好，请简短回复"}],
                "stream": True,
                "max_tokens": 50
            }
            
            response = requests.post(
                url,
                headers=self.headers,
                json=body,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                self.print_status("✅ 流式请求成功", "SUCCESS")
                chunks_received = 0
                for line in response.iter_lines():
                    if line:
                        chunks_received += 1
                        if chunks_received <= 3:  # 只显示前几个chunk
                            print(f"    Chunk {chunks_received}: {line.decode()[:100]}...")
                        if chunks_received >= 10:  # 限制接收数量
                            break
                self.print_status(f"📦 接收到 {chunks_received} 个数据块", "SUCCESS")
            else:
                self.print_status(f"❌ 流式请求失败: {response.status_code}", "ERROR")
                
        except Exception as e:
            self.print_status(f"❌ 流式测试异常: {e}", "ERROR")
    
    def test_different_auth_methods(self):
        """测试不同的认证方法"""
        self.print_status("🔐 测试不同认证方法...")
        
        auth_methods = [
            {"name": "Bearer Token", "headers": {"Authorization": f"Bearer {self.api_key}"}},
            {"name": "X-API-Key", "headers": {"X-API-Key": self.api_key}},
            {"name": "api-key", "headers": {"api-key": self.api_key}},
            {"name": "Query参数", "params": {"api_key": self.api_key}},
        ]
        
        for method in auth_methods:
            try:
                url = urljoin(self.base_url, "/v1/models")
                headers = {"Content-Type": "application/json"}
                headers.update(method.get("headers", {}))
                params = method.get("params", {})
                
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    self.print_status(f"✅ {method['name']}: 认证成功", "SUCCESS")
                else:
                    self.print_status(f"❌ {method['name']}: HTTP {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.print_status(f"❌ {method['name']}: {e}", "ERROR")

def main():
    print("🔧 ChatWise 实际连接问题深度调试工具")
    print("=" * 80)
    
    debugger = ChatWiseRealDebugger()
    
    # 执行所有测试
    debugger.test_health_check()
    print()
    
    debugger.test_models_with_different_endpoints()
    print()
    
    debugger.test_different_auth_methods()
    print()
    
    debugger.test_chat_completions_detailed()
    print()
    
    debugger.test_streaming_chat()
    print()
    
    print("🎯 调试完成！请检查上述结果找出ChatWise连接问题。")

if __name__ == "__main__":
    main()