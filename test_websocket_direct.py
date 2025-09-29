#!/usr/bin/env python3
"""
直接测试WebSocket端点
"""

import asyncio
import websockets
import json
import time

async def test_websocket_direct():
    """直接测试WebSocket连接"""
    try:
        # 直接连接到WebSocket端点
        uri = "ws://localhost:8082/ws/models/updates"
        print(f"正在连接到: {uri}")
        
        # 使用更低的超时时间
        async with websockets.connect(uri, ping_timeout=10, close_timeout=10) as websocket:
            print("连接成功!")
            
            # 测试发送ping消息
            ping_message = {
                "type": "ping",
                "timestamp": int(time.time())
            }
            
            await websocket.send(json.dumps(ping_message))
            print("已发送ping消息:", ping_message)
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print("收到响应:", response)
            except asyncio.TimeoutError:
                print("等待响应超时")
                return
            
            # 测试订阅功能
            subscribe_message = {
                "type": "subscribe",
                "model_id": "test-model"
            }
            
            await websocket.send(json.dumps(subscribe_message))
            print("已发送订阅请求:", subscribe_message)
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print("订阅响应:", response)
            except asyncio.TimeoutError:
                print("等待订阅响应超时")
                return
            
            print("WebSocket连接测试成功!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"连接被拒绝，状态码: {e.status_code}")
        print("可能的原因:")
        print("1. WebSocket端点路径不正确")
        print("2. 安全中间件阻止了连接")
        print("3. CORS配置问题")
        print("4. 服务器未运行或端口不正确")
        
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"连接被关闭: {e}")
        
    except Exception as e:
        print(f"连接错误: {e}")

async def main():
    """主测试函数"""
    print("=" * 50)
    print("直接WebSocket连接测试")
    print("=" * 50)
    
    await test_websocket_direct()
    
    print("\n测试完成!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试已取消")
    except Exception as e:
        print(f"测试错误: {e}")