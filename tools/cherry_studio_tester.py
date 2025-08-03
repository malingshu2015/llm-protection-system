#!/usr/bin/env python3
"""
Cherry Studio 兼容性测试工具

这个工具专门用于测试Cherry Studio客户端与LLM安全防火墙的兼容性。
"""

import requests
import json
import sys
from typing import Dict, Any, List

class CherryStudioTester:
    def __init__(self, base_url: str = "http://localhost:8082", api_key: str = "cherry-studio-key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def test_health(self) -> bool:
        """测试服务健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ 服务健康检查通过")
                return True
            else:
                print(f"❌ 服务健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到服务: {e}")
            return False
    
    def test_models_endpoint(self, endpoint: str) -> bool:
        """测试模型列表端点"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"✅ {endpoint} - 成功获取 {len(models)} 个模型")
                if models:
                    print(f"   示例模型: {models[0].get('name', 'N/A')}")
                return True
            else:
                print(f"❌ {endpoint} - 失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ {endpoint} - 异常: {e}")
            return False
    
    def test_chat_completion(self, model: str = "tinyllama:latest") -> bool:
        """测试聊天完成功能"""
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Hello! Please respond with 'Hi from Cherry Studio test!'"}
                ],
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    print(f"✅ 聊天完成测试通过")
                    print(f"   模型响应: {content[:100]}...")
                    return True
                else:
                    print("❌ 聊天完成测试失败: 响应格式不正确")
                    return False
            else:
                print(f"❌ 聊天完成测试失败: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ 聊天完成测试异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🍒 Cherry Studio 兼容性测试开始")
        print("=" * 50)
        
        # 测试服务健康状态
        if not self.test_health():
            print("\n❌ 服务未运行，请先启动LLM安全防火墙")
            return False
        
        print()
        
        # 测试各种模型端点
        endpoints_to_test = [
            "/v1/models",                    # 标准OpenAI端点
            "/api/v1/ollama/models",         # Ollama兼容端点
            "/api/v1/ollama/v1/models",      # Cherry Studio专用端点
        ]
        
        success_count = 0
        for endpoint in endpoints_to_test:
            if self.test_models_endpoint(endpoint):
                success_count += 1
        
        print()
        
        # 测试聊天功能
        chat_success = self.test_chat_completion()
        
        print()
        print("=" * 50)
        print(f"📊 测试结果汇总:")
        print(f"   模型端点测试: {success_count}/{len(endpoints_to_test)} 通过")
        print(f"   聊天功能测试: {'✅ 通过' if chat_success else '❌ 失败'}")
        
        if success_count > 0 and chat_success:
            print("\n🎉 Cherry Studio 应该可以正常工作！")
            self.print_configuration_guide()
        else:
            print("\n⚠️  存在兼容性问题，请检查配置")
            self.print_troubleshooting_guide()
        
        return success_count > 0 and chat_success
    
    def print_configuration_guide(self):
        """打印配置指南"""
        print("\n📋 Cherry Studio 推荐配置:")
        print("   API名称: LLM Security Firewall")
        print("   API类型: OpenAI Compatible")
        print(f"   Base URL: {self.base_url}/v1")
        print(f"   API Key: {self.api_key}")
        print("   模型: tinyllama:latest")
    
    def print_troubleshooting_guide(self):
        """打印故障排除指南"""
        print("\n🔧 故障排除步骤:")
        print("1. 确认防火墙程序正在运行:")
        print(f"   curl {self.base_url}/health")
        print()
        print("2. 检查API密钥是否正确:")
        print(f"   curl -H 'Authorization: Bearer {self.api_key}' {self.base_url}/v1/models")
        print()
        print("3. 尝试不同的Base URL配置:")
        print(f"   - {self.base_url}/v1")
        print(f"   - {self.base_url}/api/v1/ollama")
        print(f"   - {self.base_url}")
        print()
        print("4. 检查Cherry Studio的API类型设置:")
        print("   - OpenAI Compatible")
        print("   - Ollama")
        print()
        print("5. 查看防火墙日志获取详细错误信息")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cherry Studio 兼容性测试工具")
    parser.add_argument("--url", default="http://localhost:8082", help="防火墙服务地址")
    parser.add_argument("--key", default="cherry-studio-key", help="API密钥")
    parser.add_argument("--model", default="tinyllama:latest", help="测试用模型")
    
    args = parser.parse_args()
    
    tester = CherryStudioTester(args.url, args.key)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
