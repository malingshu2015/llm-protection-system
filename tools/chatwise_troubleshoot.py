#!/usr/bin/env python3
"""
ChatWise 连接故障排查工具
用于诊断和修复 ChatWise 与本地大模型防火墙的连接问题
"""

import requests
import json
import sys
import time
from urllib.parse import urljoin

class ChatWiseTroubleshooter:
    def __init__(self, base_url="http://localhost:8081", api_key="chatwise-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
        
    def test_basic_connectivity(self):
        """测试基本连接"""
        self.print_status("🔍 测试基本连接...")
        
        try:
            url = urljoin(self.base_url, "/health")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_status(f"✅ 健康检查成功: {data.get('status', 'unknown')}", "SUCCESS")
                self.print_status(f"   版本: {data.get('version', 'unknown')}")
                self.print_status(f"   Ollama可用: {data.get('ollama_available', False)}")
                return True
            else:
                self.print_status(f"❌ 健康检查失败: HTTP {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.print_status(f"❌ 连接失败: {str(e)}", "ERROR")
            return False
            
    def test_api_key(self):
        """测试API密钥"""
        self.print_status("🔍 测试API密钥认证...")
        
        # 测试多个可能的密钥
        api_keys_to_test = [
            "chatwise-key",
            "api_key_123456", 
            "cherry-studio-key",
            "demo-key-12345"
        ]
        
        successful_keys = []
        
        for test_key in api_keys_to_test:
            try:
                test_headers = {
                    "Authorization": f"Bearer {test_key}",
                    "Content-Type": "application/json"
                }
                
                url = urljoin(self.base_url, "/v1/models")
                response = requests.get(url, headers=test_headers, timeout=10)
                
                if response.status_code == 200:
                    self.print_status(f"✅ API密钥 '{test_key}' 认证成功", "SUCCESS")
                    successful_keys.append(test_key)
                elif response.status_code == 403:
                    self.print_status(f"❌ API密钥 '{test_key}' 认证失败: 权限被拒绝", "ERROR")
                else:
                    self.print_status(f"❌ API密钥 '{test_key}' 测试失败: HTTP {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.print_status(f"❌ API密钥 '{test_key}' 测试错误: {str(e)}", "ERROR")
                
        return successful_keys
            
    def test_models_endpoint(self):
        """测试模型列表端点"""
        self.print_status("🔍 测试模型列表端点...")
        
        endpoints_to_test = [
            "/v1/models",
            "/api/v1/ollama/models", 
            "/api/v1/ollama/v1/models"
        ]
        
        successful_endpoints = []
        
        for endpoint in endpoints_to_test:
            try:
                url = urljoin(self.base_url, endpoint)
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 检查OpenAI格式
                    if "object" in data and data["object"] == "list" and "data" in data:
                        models_count = len(data["data"])
                        self.print_status(f"✅ {endpoint}: OpenAI格式, {models_count}个模型", "SUCCESS")
                        successful_endpoints.append(endpoint)
                        
                        # 显示前3个模型
                        for i, model in enumerate(data["data"][:3]):
                            model_id = model.get("id", "unknown")
                            self.print_status(f"   模型 {i+1}: {model_id}")
                            
                    # 检查Ollama格式  
                    elif "models" in data:
                        models_count = len(data["models"])
                        self.print_status(f"⚠️  {endpoint}: Ollama格式, {models_count}个模型", "WARNING")
                        
                    else:
                        self.print_status(f"⚠️  {endpoint}: 未知格式", "WARNING")
                        
                else:
                    self.print_status(f"❌ {endpoint}: HTTP {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.print_status(f"❌ {endpoint}: {str(e)}", "ERROR")
                
        return successful_endpoints
        
    def test_chat_endpoint(self):
        """测试聊天端点"""
        self.print_status("🔍 测试聊天完成端点...")
        
        test_request = {
            "model": "tinyllama:latest",
            "messages": [
                {"role": "user", "content": "你好，这是ChatWise测试消息"}
            ],
            "stream": False,
            "max_tokens": 50
        }
        
        endpoints_to_test = [
            "/v1/chat/completions",
            "/api/v1/ollama/v1/chat/completions"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                url = urljoin(self.base_url, endpoint)
                response = requests.post(url, headers=self.headers, json=test_request, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "")
                        self.print_status(f"✅ {endpoint}: 聊天成功", "SUCCESS")
                        self.print_status(f"   响应: {content[:100]}...")
                        return True
                    else:
                        self.print_status(f"⚠️  {endpoint}: 响应格式异常", "WARNING")
                else:
                    self.print_status(f"❌ {endpoint}: HTTP {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.print_status(f"❌ {endpoint}: {str(e)}", "ERROR")
                
        return False
        
    def test_cors_headers(self):
        """测试CORS头"""
        self.print_status("🔍 测试CORS配置...")
        
        try:
            url = urljoin(self.base_url, "/v1/models")
            response = requests.options(url, headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization"
            }, timeout=5)
            
            if response.status_code == 200:
                cors_headers = {
                    "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                    "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                    "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
                }
                
                self.print_status("✅ CORS预检请求成功", "SUCCESS")
                for header, value in cors_headers.items():
                    if value:
                        self.print_status(f"   {header}: {value}")
                return True
            else:
                self.print_status(f"❌ CORS预检失败: HTTP {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.print_status(f"❌ CORS测试错误: {str(e)}", "ERROR")
            return False
            
    def generate_troubleshooting_report(self):
        """生成故障排查报告"""
        self.print_status("📋 生成ChatWise连接故障排查报告...", "INFO")
        print("=" * 80)
        
        results = {}
        
        # 执行所有测试
        results["basic_connectivity"] = self.test_basic_connectivity()
        print()
        
        results["api_keys"] = self.test_api_key()
        print()
        
        results["models_endpoints"] = self.test_models_endpoint()
        print()
        
        results["chat_endpoint"] = self.test_chat_endpoint()
        print()
        
        results["cors"] = self.test_cors_headers()
        print()
        
        # 生成建议
        self.print_status("🎯 ChatWise连接配置建议:", "INFO")
        print("=" * 80)
        
        if not results["basic_connectivity"]:
            self.print_status("1. 检查服务是否正在运行: python -m src.main", "ERROR")
        
        if not results["api_keys"]:
            self.print_status("2. 在ChatWise中使用以下API密钥:", "ERROR")
            self.print_status("   - chatwise-key (推荐)", "ERROR")
            self.print_status("   - api_key_123456 (兼容格式)", "ERROR")
            self.print_status("   - cherry-studio-key (通用密钥)", "ERROR")
            
        if not results["models_endpoints"]:
            self.print_status("3. 在ChatWise中设置API Base URL:", "ERROR")
            self.print_status("   - http://localhost:8081/v1 (推荐)", "ERROR")
            self.print_status("   - http://127.0.0.1:8081/v1 (备用)", "ERROR")
            
        if not results["cors"]:
            self.print_status("4. CORS配置问题，请重启服务", "ERROR")
            
        # 总体状态
        success_count = sum(1 for v in results.values() if v is True or (isinstance(v, list) and v))
        total_tests = len(results)
        
        if success_count == total_tests:
            self.print_status(f"🎉 所有测试通过 ({success_count}/{total_tests})", "SUCCESS")
            self.print_status("ChatWise应该可以正常连接!", "SUCCESS")
        else:
            self.print_status(f"⚠️  部分测试失败 ({success_count}/{total_tests})", "WARNING")
            self.print_status("请根据上述建议进行调整", "WARNING")

def main():
    """主函数"""
    print("🤖 ChatWise 连接故障排查工具")
    print("=" * 80)
    
    # 支持命令行参数
    base_url = "http://localhost:8081"
    api_key = "chatwise-key"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        api_key = sys.argv[2]
        
    print(f"测试地址: {base_url}")
    print(f"API密钥: {api_key}")
    print()
    
    troubleshooter = ChatWiseTroubleshooter(base_url, api_key)
    troubleshooter.generate_troubleshooting_report()
    
if __name__ == "__main__":
    main()