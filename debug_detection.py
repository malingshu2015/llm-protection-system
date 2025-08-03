#!/usr/bin/env python3
"""
调试安全检测逻辑
"""

import requests
import json

def debug_normal_request():
    """调试正常请求被阻止的原因"""
    
    test_message = "What is artificial intelligence?"
    
    data = {
        "model": "tinyllama:latest",
        "messages": [
            {"role": "user", "content": test_message}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(
            "http://localhost:8081/v1/chat/completions",
            headers={
                "Authorization": "Bearer cherry-studio-key",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=15
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"响应内容: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应文本: {response.text}")
            
    except Exception as e:
        print(f"请求异常: {e}")

if __name__ == "__main__":
    debug_normal_request()