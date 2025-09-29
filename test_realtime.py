#!/usr/bin/env python3
"""
实时更新功能测试脚本
用于验证WebSocket连接和模型更新功能
"""

import asyncio
import websockets
import json
import time

async def test_realtime_connection():
    """测试WebSocket连接"""
    try:
        # 连接到WebSocket服务器
        uri = "ws://localhost:8082/ws/models/updates"
        print(f"正在连接到: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("连接成功!")
            
            # 发送连接测试消息
            test_message = {
                "type": "ping",
                "timestamp": int(time.time())
            }
            
            await websocket.send(json.dumps(test_message))
            print("已发送测试消息:", test_message)
            
            # 等待响应
            response = await websocket.recv()
            print("收到响应:", response)
            
            # 测试订阅功能
            subscribe_message = {
                "type": "subscribe",
                "model_id": "test-model"
            }
            
            await websocket.send(json.dumps(subscribe_message))
            print("已发送订阅请求:", subscribe_message)
            
            response = await websocket.recv()
            print("订阅响应:", response)
            
            # 保持连接一段时间以测试心跳
            print("连接保持中... (按Ctrl+C退出)")
            await asyncio.sleep(10)
            
    except websockets.exceptions.ConnectionClosedError:
        print("连接被关闭")
    except Exception as e:
        print(f"连接错误: {e}")

async def test_http_api():
    """测试HTTP API端点"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            # 测试连接统计API
            url = "http://localhost:8082/api/v1/realtime/connections"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print("连接统计:", data)
                else:
                    print(f"API请求失败: {response.status}")
            
    except Exception as e:
        print(f"HTTP API测试错误: {e}")

async def main():
    """主测试函数"""
    print("=" * 50)
    print("实时更新功能测试")
    print("=" * 50)
    
    # 测试HTTP API
    print("\n1. 测试HTTP API...")
    await test_http_api()
    
    # 测试WebSocket连接
    print("\n2. 测试WebSocket连接...")
    await test_realtime_connection()
    
    print("\n测试完成!")

if __name__ == "__main__":
    # 检查服务器是否运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试已取消")
    except Exception as e:
        print(f"测试错误: {e}")