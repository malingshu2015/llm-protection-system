#!/usr/bin/env python3
"""
Cherry Studio 连接问题修复工具

这个工具专门用于解决Cherry Studio连接LLM安全防火墙时的常见问题。
"""

import requests
import json
import sys
import time
from typing import Dict, Any, List, Tuple

def test_all_cherry_studio_endpoints() -> Dict[str, bool]:
    """测试所有Cherry Studio可能使用的端点"""
    endpoints = {
        # 标准端点
        "OpenAI模型列表": "/v1/models",
        "OpenAI聊天": "/v1/chat/completions",
        
        # Ollama兼容端点
        "Ollama模型列表": "/api/v1/ollama/models",
        "Ollama聊天": "/api/v1/ollama/chat",
        
        # Cherry Studio专用端点
        "Cherry Studio模型": "/api/v1/ollama/v1/models",
        "Cherry Studio响应": "/api/v1/ollama/v1/responses",
        
        # 路径重复修复端点
        "重复路径模型": "/api/v1/ollama/v1/v1/models",
        "重复路径响应": "/api/v1/ollama/v1/v1/responses",
        "重复路径聊天": "/api/v1/ollama/v1/v1/chat/completions"
    }
    
    results = {}
    headers = {"Authorization": "Bearer cherry-studio-key"}
    
    for name, endpoint in endpoints.items():
        try:
            if "聊天" in name or "响应" in name:
                # POST请求
                payload = {"model": "tinyllama:latest", "messages": [{"role": "user", "content": "test"}]}
                response = requests.post(f"http://localhost:8082{endpoint}", 
                                       headers={**headers, "Content-Type": "application/json"},
                                       json=payload, timeout=10)
            else:
                # GET请求
                response = requests.get(f"http://localhost:8082{endpoint}", headers=headers, timeout=10)
            
            results[name] = response.status_code == 200
            
        except Exception as e:
            results[name] = False
    
    return results

def generate_cherry_studio_configs() -> List[Dict[str, str]]:
    """生成所有可能的Cherry Studio配置"""
    return [
        {
            "name": "配置1 - OpenAI兼容 (最推荐)",
            "api_type": "OpenAI Compatible",
            "base_url": "http://localhost:8082/v1",
            "api_key": "cherry-studio-key",
            "description": "标准OpenAI API格式，兼容性最好"
        },
        {
            "name": "配置2 - Ollama兼容",
            "api_type": "Ollama",
            "base_url": "http://localhost:8082/api/v1/ollama",
            "api_key": "cherry-studio-key",
            "description": "Ollama原生格式"
        },
        {
            "name": "配置3 - Cherry Studio专用",
            "api_type": "Ollama",
            "base_url": "http://localhost:8082/api/v1/ollama/v1",
            "api_key": "cherry-studio-key",
            "description": "专为Cherry Studio优化"
        },
        {
            "name": "配置4 - 基础URL",
            "api_type": "OpenAI Compatible",
            "base_url": "http://localhost:8082",
            "api_key": "cherry-studio-key",
            "description": "让Cherry Studio自动添加路径"
        }
    ]

def print_step_by_step_guide():
    """打印详细的配置步骤"""
    print("\n📋 Cherry Studio 详细配置步骤:")
    print("=" * 60)
    
    print("\n1️⃣ 打开Cherry Studio设置")
    print("   • 启动Cherry Studio应用")
    print("   • 点击左下角的设置图标（齿轮）")
    print("   • 选择'模型'选项卡")
    
    print("\n2️⃣ 添加自定义API")
    print("   • 点击'添加自定义API'按钮")
    print("   • 选择API类型")
    
    print("\n3️⃣ 填入配置信息")
    configs = generate_cherry_studio_configs()
    
    for i, config in enumerate(configs, 1):
        print(f"\n   {config['name']}:")
        print(f"   ┌─ API名称: LLM Security Firewall")
        print(f"   ├─ API类型: {config['api_type']}")
        print(f"   ├─ Base URL: {config['base_url']}")
        print(f"   ├─ API Key: {config['api_key']}")
        print(f"   └─ 说明: {config['description']}")
    
    print("\n4️⃣ 测试连接")
    print("   • 点击'测试连接'按钮")
    print("   • 等待连接测试完成")
    print("   • 如果成功，会显示可用模型")
    
    print("\n5️⃣ 开始使用")
    print("   • 创建新对话")
    print("   • 选择模型（推荐: tinyllama:latest）")
    print("   • 发送测试消息")

def print_troubleshooting_tips():
    """打印故障排除提示"""
    print("\n🔧 常见问题解决方案:")
    print("=" * 60)
    
    print("\n❌ 问题1: 连接失败")
    print("   解决方案:")
    print("   • 确认防火墙程序正在运行")
    print("   • 检查URL拼写是否正确")
    print("   • 尝试不同的配置选项")
    
    print("\n❌ 问题2: API密钥验证失败")
    print("   解决方案:")
    print("   • 确认API Key为: cherry-studio-key")
    print("   • 检查是否有多余空格")
    print("   • 重新输入API密钥")
    
    print("\n❌ 问题3: 无法获取模型列表")
    print("   解决方案:")
    print("   • 确认Ollama服务运行正常")
    print("   • 检查防火墙日志")
    print("   • 尝试重启防火墙程序")
    
    print("\n❌ 问题4: 路径重复错误")
    print("   解决方案:")
    print("   • 系统已自动修复此问题")
    print("   • 如仍有问题，尝试配置1")
    
    print("\n💡 调试技巧:")
    print("   • 查看Cherry Studio的错误信息")
    print("   • 检查防火墙程序的控制台输出")
    print("   • 使用浏览器访问 http://localhost:8082/health")

def main():
    """主修复流程"""
    print("🍒 Cherry Studio 连接问题修复工具")
    print("=" * 60)
    
    # 1. 检查服务状态
    print("\n🔍 检查系统状态...")
    try:
        response = requests.get("http://localhost:8082/health", timeout=5)
        if response.status_code == 200:
            print("✅ 防火墙服务正常运行")
        else:
            print("❌ 防火墙服务异常")
            return False
    except:
        print("❌ 无法连接到防火墙服务")
        print("请先启动服务: WEB_PORT=8082 python3 -m src.main")
        return False
    
    # 2. 测试所有端点
    print("\n🧪 测试所有Cherry Studio端点...")
    results = test_all_cherry_studio_endpoints()
    
    working_endpoints = []
    for name, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {name}")
        if status:
            working_endpoints.append(name)
    
    # 3. 生成建议
    print(f"\n📊 测试结果: {len(working_endpoints)}/{len(results)} 个端点正常工作")
    
    if len(working_endpoints) >= 6:  # 大部分端点工作
        print("🎉 系统工作正常！Cherry Studio应该可以连接。")
        print("\n🎯 推荐使用配置1 (OpenAI兼容)")
    elif len(working_endpoints) >= 3:  # 部分端点工作
        print("⚠️  部分功能正常，可能需要特定配置。")
        print("\n🎯 建议尝试多个配置选项")
    else:
        print("❌ 系统存在问题，需要检查配置。")
        print("\n🎯 请检查防火墙程序和Ollama服务")
    
    # 4. 显示配置指南
    print_step_by_step_guide()
    
    # 5. 显示故障排除提示
    print_troubleshooting_tips()
    
    print("\n" + "=" * 60)
    print("🚀 修复完成！请按照上述指南配置Cherry Studio。")
    print("如果仍有问题，请运行: python3 tools/diagnose_cherry_studio.py")
    
    return len(working_endpoints) >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
