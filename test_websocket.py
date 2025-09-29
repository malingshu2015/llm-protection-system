#!/usr/bin/env python3
"""
WebSocket连接测试脚本
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8082/ws/models/updates"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功建立")
            
            # 发送连接确认
            await websocket.send(json.dumps({
                "type": "subscribe",
                "model_id": "test-model-123"
            }))
            
            # 接收欢迎消息
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 收到服务器响应: {data}")
            
            # 发送心跳
            await websocket.send(json.dumps({
                "type": "ping",
                "timestamp": 1234567890
            }))
            
            # 接收心跳响应
            response = await websocket.recv()
            data = json.loads(response)
            print(f"💓 心跳响应: {data}")
            
            print("✅ WebSocket通信测试完成！")
            
    except Exception as e:
        print(f"❌ WebSocket连接失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_websocket())