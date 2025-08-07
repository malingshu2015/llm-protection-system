#!/usr/bin/env python3
"""
上下文污染问题诊断工具
用于分析为什么连续的请求会被错误拦截
"""

import json
import time
from typing import Dict, Any, List

def analyze_context_pollution():
    """分析上下文污染问题"""
    print("=== 上下文污染问题诊断 ===")
    print()
    
    # 1. 检查对话跟踪器的状态
    print("1. 检查对话跟踪器状态:")
    try:
        from src.security.conversation_tracker import conversation_tracker
        print(f"   当前对话数量: {len(conversation_tracker.conversations)}")
        
        for conv_id, conv in conversation_tracker.conversations.items():
            print(f"   对话ID: {conv_id}")
            print(f"   消息数量: {len(conv.messages)}")
            print(f"   是否被攻陷: {conv.is_compromised}")
            print(f"   最后更新: {time.ctime(conv.updated_at)}")
            
            # 显示最近的消息
            if conv.messages:
                print("   最近消息:")
                for msg in conv.messages[-3:]:  # 显示最后3条消息
                    print(f"     {msg.role}: {msg.content[:100]}...")
            print()
            
    except Exception as e:
        print(f"   错误: 无法访问对话跟踪器 - {e}")
    
    # 2. 检查检测器缓存状态
    print("2. 检查检测器缓存状态:")
    try:
        from src.security.detector import SecurityDetector
        detector = SecurityDetector()
        
        # 检查各个子检测器是否有缓存
        for detector_name in ['prompt_injection_detector', 'jailbreak_detector', 
                             'harmful_content_detector', 'sensitive_info_detector']:
            if hasattr(detector, detector_name):
                sub_detector = getattr(detector, detector_name)
                if hasattr(sub_detector, 'cache'):
                    print(f"   {detector_name} 缓存大小: {len(getattr(sub_detector, 'cache', {}))}")
                else:
                    print(f"   {detector_name}: 无缓存")
        
    except Exception as e:
        print(f"   错误: 无法访问检测器 - {e}")
    
    # 3. 检查最近的安全事件
    print("3. 检查最近的安全事件:")
    try:
        events_file = "data/security_events/events.json"
        with open(events_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        # 显示最近的5个事件
        recent_events = sorted(events, key=lambda x: x.get('timestamp', 0), reverse=True)[:5]
        
        for i, event in enumerate(recent_events, 1):
            print(f"   事件 {i}:")
            print(f"     时间: {time.ctime(event.get('timestamp', 0))}")
            print(f"     类型: {event.get('detection_type', 'unknown')}")
            print(f"     严重性: {event.get('severity', 'unknown')}")
            print(f"     原因: {event.get('reason', 'unknown')[:100]}...")
            if 'details' in event and event['details']:
                if 'matched_text' in event['details']:
                    print(f"     匹配文本: {event['details']['matched_text']}")
            print()
            
    except Exception as e:
        print(f"   错误: 无法读取安全事件 - {e}")
    
    # 4. 模拟测试检测器的行为
    print("4. 模拟测试检测器行为:")
    test_cases = [
        "你好",
        "我想知道你是哪个大模型",
        "今天天气怎么样",
        "如何制作一把刀"  # 这个应该被拦截
    ]
    
    try:
        from src.security.detector import SecurityDetector
        detector = SecurityDetector()
        
        for i, test_text in enumerate(test_cases, 1):
            print(f"   测试 {i}: '{test_text}'")
            
            # 创建模拟请求
            from src.models_interceptor import InterceptedRequest
            mock_request = InterceptedRequest(
                method="POST",
                url="http://localhost:8081/v1/chat/completions",
                headers={"content-type": "application/json"},
                body={
                    "model": "test",
                    "messages": [{"role": "user", "content": test_text}]
                },
                query_params={},
                timestamp=time.time(),
                client_ip="127.0.0.1",
                provider="test"
            )
            
            # 进行检测
            try:
                import asyncio
                result = asyncio.run(detector.check_request(mock_request))
                
                if result.is_allowed:
                    print(f"     结果: ✅ 允许通过")
                else:
                    print(f"     结果: ❌ 被拦截")
                    print(f"     原因: {result.reason}")
                    if hasattr(result, 'details') and result.details:
                        print(f"     详情: {result.details}")
            except Exception as e:
                print(f"     检测失败: {e}")
            
            print()
            
    except Exception as e:
        print(f"   错误: 无法进行模拟测试 - {e}")

    print("=== 诊断完成 ===")

if __name__ == "__main__":
    analyze_context_pollution()