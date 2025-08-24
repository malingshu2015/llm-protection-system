#!/usr/bin/env python3
"""
Cherry Studio 专用配置验证和修复工具
用于诊断和解决Cherry Studio与本地大模型防火墙的连接问题
"""

import requests
import json
import sys
import time
import os
from urllib.parse import urljoin

class CherryStudioConfigValidator:
    def __init__(self, base_url="http://localhost:8081", api_key=None):
        self.base_url = base_url
        self.api_key = api_key or os.getenv("CHERRY_STUDIO_API_KEY", "cherry-studio-key")
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
        
    def validate_cherry_studio_config(self):
        """验证Cherry Studio配置"""
        self.print_status("🍒 Cherry Studio 配置验证开始...", "INFO")
        print("=" * 80)
        
        # 1. 基础连接测试
        self.print_status("1️⃣  验证服务连接...", "INFO")
        if not self._test_service_health():
            return False
            
        # 2. API密钥验证
        self.print_status("2️⃣  验证API密钥...", "INFO")
        if not self._test_api_authentication():
            return False
            
        # 3. 模型列表验证
        self.print_status("3️⃣  验证模型列表...", "INFO")
        models = self._test_models_endpoint()
        if not models:
            return False
            
        # 4. 聊天功能验证
        self.print_status("4️⃣  验证聊天功能...", "INFO")
        if not self._test_chat_functionality():
            return False
            
        # 5. Cherry Studio特定测试
        self.print_status("5️⃣  Cherry Studio特定验证...", "INFO")
        if not self._test_cherry_studio_specific():
            return False
            
        return True
        
    def _test_service_health(self):
        """测试服务健康状态"""
        try:
            url = urljoin(self.base_url, "/health")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_status(f"✅ 服务健康: {data.get('status')}", "SUCCESS")
                self.print_status(f"   📍 地址: {self.base_url}", "INFO")
                self.print_status(f"   🔢 版本: {data.get('version')}", "INFO")
                self.print_status(f"   🧠 Ollama: {'可用' if data.get('ollama_available') else '不可用'}", "INFO")
                return True
            else:
                self.print_status(f"❌ 服务健康检查失败: HTTP {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.print_status(f"❌ 无法连接到服务: {str(e)}", "ERROR")
            self.print_status("💡 建议: 检查服务是否运行，确认地址和端口正确", "WARNING")
            return False
            
    def _test_api_authentication(self):
        """测试API认证"""
        try:
            url = urljoin(self.base_url, "/v1/test")
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                self.print_status(f"✅ API密钥认证成功", "SUCCESS")
                self.print_status(f"   🔑 密钥: {self.api_key}", "INFO")
                return True
            elif response.status_code == 403:
                self.print_status(f"❌ API密钥认证失败: 无权限", "ERROR")
                self.print_status("💡 建议: 确认使用正确的API密钥 'cherry-studio-key'", "WARNING")
                return False
            else:
                self.print_status(f"❌ API认证测试失败: HTTP {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.print_status(f"❌ API认证测试出错: {str(e)}", "ERROR")
            return False
            
    def _test_models_endpoint(self):
        """测试模型列表端点"""
        try:
            url = urljoin(self.base_url, "/v1/models")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "object" in data and data["object"] == "list" and "data" in data:
                    models = data["data"]
                    self.print_status(f"✅ 模型列表获取成功: {len(models)}个模型", "SUCCESS")
                    
                    # 显示可用模型
                    self.print_status("   🎯 可用模型:", "INFO")
                    for i, model in enumerate(models[:5]):  # 显示前5个
                        model_id = model.get("id", "unknown")
                        self.print_status(f"      {i+1}. {model_id}", "INFO")
                    
                    if len(models) > 5:
                        self.print_status(f"      ... 还有 {len(models)-5} 个模型", "INFO")
                        
                    return models
                else:
                    self.print_status(f"❌ 模型列表格式错误: 非OpenAI标准格式", "ERROR")
                    return None
            else:
                self.print_status(f"❌ 模型列表获取失败: HTTP {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.print_status(f"❌ 模型列表测试出错: {str(e)}", "ERROR")
            return None
            
    def _test_chat_functionality(self):
        """测试聊天功能"""
        try:
            url = urljoin(self.base_url, "/v1/chat/completions")
            test_request = {
                "model": "tinyllama:latest",
                "messages": [
                    {"role": "user", "content": "Hello, Cherry Studio test"}
                ],
                "stream": False,
                "max_tokens": 30
            }
            
            response = requests.post(url, headers=self.headers, json=test_request, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content", "")
                    self.print_status(f"✅ 聊天功能正常", "SUCCESS")
                    self.print_status(f"   💬 测试响应: {content[:50]}...", "INFO")
                    return True
                else:
                    self.print_status(f"❌ 聊天响应格式异常", "ERROR")
                    return False
            else:
                self.print_status(f"❌ 聊天功能测试失败: HTTP {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.print_status(f"❌ 聊天功能测试出错: {str(e)}", "ERROR")
            return False
            
    def _test_cherry_studio_specific(self):
        """Cherry Studio特定测试"""
        # 测试Cherry Studio可能使用的特殊端点
        endpoints_to_test = [
            ("/v1/models", "标准模型端点"),
            ("/api/v1/ollama/v1/models", "Ollama兼容端点"),
            ("/v1/test", "连接测试端点")
        ]
        
        all_passed = True
        for endpoint, description in endpoints_to_test:
            try:
                url = urljoin(self.base_url, endpoint)
                response = requests.get(url, headers=self.headers, timeout=5)
                
                if response.status_code == 200:
                    self.print_status(f"✅ {description}: 正常", "SUCCESS")
                else:
                    self.print_status(f"❌ {description}: HTTP {response.status_code}", "ERROR")
                    all_passed = False
                    
            except Exception as e:
                self.print_status(f"❌ {description}: {str(e)}", "ERROR")
                all_passed = False
                
        return all_passed
        
    def generate_config_guide(self):
        """生成配置指南"""
        self.print_status("📋 Cherry Studio 配置指南", "INFO")
        print("=" * 80)
        
        print("\n🔧 Cherry Studio 配置步骤:")
        print("1. 打开 Cherry Studio")
        print("2. 进入 设置 → AI Providers → 添加新提供商")
        print("3. 选择 'OpenAI Compatible' 或 'Custom OpenAI'")
        print()
        
        print("📝 配置参数:")
        print(f"   提供商名称: 本地大模型防火墙")
        print(f"   API Base URL: {self.base_url}/v1")
        print(f"   API Key: {self.api_key}")
        print(f"   模型: tinyllama:latest (或其他可用模型)")
        print()
        
        print("🛠️ 如果连接失败，尝试以下方法:")
        print("1. 备选URL配置:")
        print(f"   - {self.base_url}/v1")
        print(f"   - http://127.0.0.1:8081/v1")
        print(f"   - {self.base_url}/api/v1/ollama/v1")
        print()
        print("2. 检查防火墙和网络设置")
        print("3. 确认服务正在运行")
        print("4. 尝试重启 Cherry Studio")
        print()
        
        print("🏃‍♂️ 测试连接:")
        print(f"   浏览器访问: {self.base_url}/v1/test")
        print(f"   应该显示连接成功信息")
        print()
        
    def run_full_validation(self):
        """运行完整验证"""
        self.print_status("🍒 Cherry Studio 配置验证工具", "INFO")
        print("=" * 80)
        
        # 配置验证
        success = self.validate_cherry_studio_config()
        
        print()
        print("=" * 80)
        
        if success:
            self.print_status("🎉 所有验证通过！Cherry Studio 配置正确", "SUCCESS")
            self.print_status("现在可以在 Cherry Studio 中正常使用本地大模型防火墙", "SUCCESS")
        else:
            self.print_status("❌ 验证失败，请按照以下指南进行配置", "ERROR")
            
        print()
        self.generate_config_guide()

def main():
    """主函数"""
    # 支持命令行参数
    base_url = "http://localhost:8081"
    api_key = os.getenv("CHERRY_STUDIO_API_KEY", "cherry-studio-key")
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        api_key = sys.argv[2]
        
    validator = CherryStudioConfigValidator(base_url, api_key)
    validator.run_full_validation()
    
if __name__ == "__main__":
    main()