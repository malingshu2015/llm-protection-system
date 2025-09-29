#!/usr/bin/env python3
"""
快速验证模型市场修复的脚本
"""

import requests
import json
import time

def test_api_endpoints():
    """测试所有API端点"""
    base_url = "http://localhost:8081"
    endpoints = [
        ("GET", "/api/v1/models", "模型列表"),
        ("GET", "/api/v1/models/stats/summary", "统计信息"),
        ("GET", "/api/v1/models/llama-3-8b", "模型详情"),
        ("POST", "/api/v1/models/llama-3-8b/download", "下载模型"),
    ]
    
    print("🧪 开始API端点测试...")
    results = []
    
    for method, endpoint, description in endpoints:
        try:
            url = base_url + endpoint
            print(f"\n🔍 测试 {description}: {method} {endpoint}")
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:  # POST
                response = requests.post(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功 - 状态码: {response.status_code}")
                if isinstance(data, list):
                    print(f"   返回 {len(data)} 条记录")
                elif isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"   返回数据包含: {keys}")
                results.append(True)
            else:
                print(f"❌ 失败 - 状态码: {response.status_code}")
                print(f"   响应: {response.text[:200]}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ 异常: {e}")
            results.append(False)
    
    success_rate = (sum(results) / len(results)) * 100
    print(f"\n📊 API测试结果: {sum(results)}/{len(results)} 通过 ({success_rate:.1f}%)")
    return success_rate == 100

def check_server_health():
    """检查服务器健康状态"""
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器健康状态正常")
            return True
        else:
            print(f"⚠️ 服务器响应异常: {response.status_code}")
            return False
    except:
        print("❌ 无法连接到服务器")
        return False

def main():
    print("🚀 模型市场修复验证工具")
    print("=" * 50)
    
    # 检查服务器状态
    if not check_server_health():
        print("\n❌ 服务器未运行，请先启动服务器:")
        print("   python -m uvicorn src.main:app --host 0.0.0.0 --port 8081")
        return
    
    # 测试API端点
    api_success = test_api_endpoints()
    
    print("\n" + "=" * 50)
    if api_success:
        print("🎉 所有API测试通过！模型市场修复成功！")
        print("\n📋 下一步:")
        print("1. 打开浏览器访问测试页面")
        print("2. 测试模型管理页面的'浏览市场'功能")
        print("3. 验证弹窗和搜索功能正常")
    else:
        print("⚠️ 部分API测试失败，请检查错误信息")
    
    print("=" * 50)

if __name__ == "__main__":
    main()