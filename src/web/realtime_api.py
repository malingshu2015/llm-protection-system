"""实时更新WebSocket API"""

import uuid
import json
import time
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse

from src.logger import logger
from src.web.realtime_update_service import realtime_service, ConnectionManager

router = APIRouter()

# WebSocket连接管理器
connection_manager = ConnectionManager()

@router.websocket("/ws/models/updates")
async def websocket_model_updates(websocket: WebSocket):
    """模型更新WebSocket端点"""
    connection_id = str(uuid.uuid4())
    
    try:
        # 接受WebSocket连接
        await websocket.accept()
        await connection_manager.connect(websocket, connection_id)
        
        # 发送连接确认
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "实时模型更新连接已建立"
        })
        
        # 处理客户端消息
        while True:
            data = await websocket.receive_json()
            
            # 处理订阅请求
            if data.get("type") == "subscribe":
                model_id = data.get("model_id")
                if model_id:
                    await connection_manager.subscribe(connection_id, model_id)
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "model_id": model_id,
                        "message": f"已订阅模型 {model_id} 的更新"
                    })
            
            # 处理取消订阅请求
            elif data.get("type") == "unsubscribe":
                model_id = data.get("model_id")
                if model_id:
                    await connection_manager.unsubscribe(connection_id, model_id)
                    await websocket.send_json({
                        "type": "unsubscription_confirmed", 
                        "model_id": model_id,
                        "message": f"已取消订阅模型 {model_id} 的更新"
                    })
            
            # 处理心跳检测
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {connection_id}")
        connection_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket处理错误: {e}")
        connection_manager.disconnect(connection_id)

@router.get("/realtime-demo")
async def realtime_demo():
    """实时更新演示页面"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>实时模型更新演示</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .update { background: #fff3cd; color: #856404; margin: 5px 0; padding: 10px; border-radius: 3px; }
            #messages { max-height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>实时模型更新演示</h1>
            <div id="status" class="status disconnected">未连接</div>
            <button onclick="connect()">连接</button>
            <button onclick="disconnect()">断开</button>
            
            <h3>订阅模型更新</h3>
            <input type="text" id="modelId" placeholder="输入模型ID">
            <button onclick="subscribe()">订阅</button>
            <button onclick="unsubscribe()">取消订阅</button>
            
            <h3>实时更新消息</h3>
            <div id="messages"></div>
        </div>

        <script>
            let ws = null;
            const statusEl = document.getElementById('status');
            const messagesEl = document.getElementById('messages');
            const modelIdInput = document.getElementById('modelId');
            
            function connect() {
                ws = new WebSocket(`ws://${window.location.host}/ws/models/updates`);
                
                ws.onopen = () => {
                    statusEl.className = 'status connected';
                    statusEl.textContent = '已连接';
                    addMessage('连接已建立');
                    
                    // 发送心跳
                    setInterval(() => {
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
                        }
                    }, 30000);
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    addMessage(JSON.stringify(data, null, 2));
                };
                
                ws.onclose = () => {
                    statusEl.className = 'status disconnected';
                    statusEl.textContent = '连接已断开';
                    addMessage('连接已断开');
                };
                
                ws.onerror = (error) => {
                    addMessage('连接错误: ' + error);
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function subscribe() {
                const modelId = modelIdInput.value.trim();
                if (modelId && ws) {
                    ws.send(JSON.stringify({ type: 'subscribe', model_id: modelId }));
                }
            }
            
            function unsubscribe() {
                const modelId = modelIdInput.value.trim();
                if (modelId && ws) {
                    ws.send(JSON.stringify({ type: 'unsubscribe', model_id: modelId }));
                }
            }
            
            function addMessage(message) {
                const div = document.createElement('div');
                div.className = 'update';
                div.textContent = new Date().toLocaleTimeString() + ' - ' + message;
                messagesEl.appendChild(div);
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
        </script>
    </body>
    </html>
    """)

@router.post("/api/v1/models/{model_id}/notify-update")
async def notify_model_update(model_id: str, update_data: Dict[str, Any]):
    """手动触发模型更新通知（用于测试）"""
    from src.web.realtime_update_service import ModelUpdate, UpdateType
    
    update = ModelUpdate(
        type=UpdateType.VERSION_CHANGE,
        model_id=model_id,
        timestamp=int(time.time()),
        version=update_data.get("version"),
        checksum=update_data.get("checksum"),
        metadata=update_data.get("metadata"),
        change_type=update_data.get("change_type", "minor")
    )
    
    await connection_manager.broadcast_update(update)
    return {"status": "success", "message": f"已发送模型 {model_id} 的更新通知"}

@router.get("/api/v1/realtime/connections")
async def get_connection_stats():
    """获取实时连接统计"""
    return {
        "active_connections": len(connection_manager.active_connections),
        "subscriptions": {
            model_id: len(connections) 
            for model_id, connections in connection_manager.subscriptions.items()
        }
    }

@router.get("/api/models/updates")
async def get_model_updates():
    """HTTP轮询端点 - 用于WebSocket降级时的模型更新检查"""
    from src.web.realtime_update_service import realtime_service
    
    # 返回最近的模型更新信息
    recent_updates = realtime_service.get_recent_updates(limit=10)
    
    return {
        "status": "success",
        "updates": recent_updates,
        "timestamp": int(time.time()),
        "polling": True,
        "message": "使用HTTP轮询模式获取模型更新"
    }