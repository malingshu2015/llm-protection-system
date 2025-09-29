#!/usr/bin/env python3
"""
模型市场功能测试脚本
测试API端点和页面访问
"""

import requests
import json

BASE_URL = "http://localhost:8081"

def test_api_endpoint(endpoint, method="GET", data=None):
    """测试API端点"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        
        print(f"测试 {method} {endpoint}:")
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  响应内容: {response.text[:200]}...")
        else:
            print(f"  错误信息: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"  请求失败: {e}")
        return False

def test_page_access(page_url):
    """测试页面访问"""
    url = f"{BASE_URL}{page_url}"
    try:
        response = requests.get(url)
        print(f"测试页面 {page_url}:")
        print(f"  状态码: {response.status_code}")
        print(f"  内容类型: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            print("  页面访问成功")
            return True
        else:
            print(f"  页面访问失败: {response.text[:100]}...")
            return False
            
    except Exception as e:
        print(f"  页面访问失败: {e}")
        return False

def main():
    print("=" * 60)
    print("模型市场功能测试")
    print("=" * 60)
    
    # 测试API端点
    print("\n1. 测试API端点:")
    api_tests = [
        ("/api/v1/models", "GET"),
        ("/api/v1/models/stats/summary", "GET"),
        ("/api/v1/models/search/suggestions?q=llama", "GET"),
        ("/api/v1/models/llama-3-8b", "GET"),
    ]
    
    api_success = 0
    for endpoint, method in api_tests:
        if test_api_endpoint(endpoint, method):
            api_success += 1
        print()
    
    # 测试页面访问
    print("\n2. 测试页面访问:")
    page_tests = [
        "/model-market",
        "/static/model-market.html"
    ]
    
    page_success = 0
    for page in page_tests:
        if test_page_access(page):
            page_success += 1
        print()
    
    # 测试模型操作
    print("\n3. 测试模型操作:")
    operation_tests = [
        ("/api/v1/models/llama-3-8b/like", "POST"),
        ("/api/v1/models/llama-3-8b/download", "POST"),
    ]
    
    operation_success = 0
    for endpoint, method in operation_tests:
        if test_api_endpoint(endpoint, method):
            operation_success += 1
        print()
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总:")
    print(f"  API端点测试: {api_success}/{len(api_tests)} 成功")
    print(f"  页面访问测试: {page_success}/{len(page_tests)} 成功") 
    print(f"  模型操作测试: {operation_success}/{len(operation_tests)} 成功")
    
    total_tests = len(api_tests) + len(page_tests) + len(operation_tests)
    total_success = api_success + page_success + operation_success
    
    print(f"  总体成功率: {total_success}/{total_tests} ({total_success/total_tests*100:.1f}%)")
    
    if total_success == total_tests:
        print("✅ 所有测试通过！模型市场功能正常")
    else:
        print("❌ 部分测试失败，请检查日志")
    
    print("=" * 60)

if __name__ == "__main__":
    main()