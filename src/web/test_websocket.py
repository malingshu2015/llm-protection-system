"""
简单的WebSocket测试端点
用于验证WebSocket功能是否正常工作
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.logger import logger

router = APIRouter()

@router.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """简单的WebSocket测试端点"""
    try:
        # 接受连接
        await websocket.accept()
        logger.info("测试WebSocket连接已接受")
        
        # 发送欢迎消息
        await websocket.send_json({
            "type": "welcome",
            "message": "测试WebSocket连接成功",
            "status": "connected"
        })
        
        # 处理消息
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"收到测试消息: {data}")
                
                # 回声响应
                await websocket.send_json({
                    "type": "echo",
                    "received": data,
                    "timestamp": "2025-08-31T13:00:00Z"
                })
                
            except WebSocketDisconnect:
                logger.info("测试WebSocket连接断开")
                break
            except Exception as e:
                logger.error(f"测试WebSocket错误: {e}")
                break
                
    except Exception as e:
        logger.error(f"测试WebSocket连接错误: {e}")
        await websocket.close()