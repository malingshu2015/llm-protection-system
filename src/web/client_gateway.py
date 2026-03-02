"""
客户端网关 WebSocket 服务
为统一客户端提供实时通信支持
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Dict, Set, Optional
import json
import asyncio
import logging
from datetime import datetime, timezone

from src.auth.services.auth_service import auth_service
from src.auth.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["客户端网关"])


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, client_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(client_id)

        logger.info(f"客户端已连接: user={user_id}, client={client_id}")

    def disconnect(self, client_id: str, user_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(client_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"客户端已断开: client={client_id}")

    async def send_to_client(self, client_id: str, message: dict):
        """发送消息到指定客户端"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """广播消息到用户的所有客户端"""
        if user_id in self.user_connections:
            tasks = [
                self.send_to_client(client_id, message)
                for client_id in self.user_connections[user_id]
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_user_clients(self, user_id: str) -> Set[str]:
        """获取用户的所有客户端"""
        return self.user_connections.get(user_id, set())


manager = ConnectionManager()


@router.websocket("/api/v1/client/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="认证令牌"),
    client_id: str = Query(..., description="客户端ID")
):
    """WebSocket 端点"""
    logger.info(f"[WebSocket] 新连接请求: client_id={client_id}, token前10位={token[:10] if token else 'None'}")
    user: Optional[User] = None

    try:
        # 1. 验证 token
        logger.info(f"[WebSocket] 开始验证token: client_id={client_id}")
        user = await auth_service.verify_token(token)
        if not user:
            logger.warning(f"[WebSocket] Token验证失败: client_id={client_id}, token={token[:20]}...")
            await websocket.close(code=4001, reason="未授权")
            return

        logger.info(f"[WebSocket] Token验证成功: user_id={user.id}, username={user.username}, client_id={client_id}")

        # 2. 建立连接
        await manager.connect(websocket, user.id, client_id)
        logger.info(f"[WebSocket] 连接已建立: user_id={user.id}, client_id={client_id}")

        # 3. 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            "server_time": datetime.now(timezone.utc).isoformat()
        })

        # 4. 消息循环
        while True:
            data = await websocket.receive_json()
            logger.info(f"[WebSocket] 收到消息: client_id={client_id}, type={data.get('type')}, data={data}")
            await handle_message(websocket, user, data, client_id)

    except WebSocketDisconnect:
        if user:
            manager.disconnect(client_id, user.id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {str(e)}")
        if user:
            manager.disconnect(client_id, user.id)
        await websocket.close(code=1011, reason="服务器错误")


async def handle_message(websocket: WebSocket, user: User, data: dict, client_id: str):
    """处理客户端消息"""
    msg_type = data.get("type")
    msg_data = data.get("data", {})  # 获取嵌套的 data 对象
    logger.info(f"[WebSocket] 处理消息: msg_type={msg_type}, client_id={client_id}, user={user.username}")
    logger.info(f"[WebSocket] 消息数据: data={msg_data}")

    try:
        if msg_type == "chat:message":
            logger.info(f"[WebSocket] 处理聊天消息: {msg_data}")
            await handle_chat_message(websocket, user, msg_data)

        elif msg_type == "chat:stream":
            await handle_stream_message(websocket, user, msg_data)

        elif msg_type == "policy:sync":
            await handle_policy_sync(websocket, user, msg_data)

        elif msg_type == "ping":
            await websocket.send_json({
                "type": "pong",
                "timestamp": data.get("timestamp"),
                "server_time": datetime.now(timezone.utc).isoformat()
            })

        else:
            await websocket.send_json({
                "type": "error",
                "error": {"message": f"未知消息类型: {msg_type}"}
            })

    except Exception as e:
        logger.error(f"处理消息失败: {str(e)}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "error": {"message": str(e)}
        })


async def handle_chat_message(websocket: WebSocket, user: User, data: dict):
    """处理聊天消息"""
    session_id = data.get("sessionId")
    message = data.get("message")
    model = data.get("model", "llama3.2:latest")  # 默认使用 llama3.2

    try:
        # 尝试导入 ollama
        try:
            import ollama
            OLLAMA_AVAILABLE = True
        except ImportError:
            OLLAMA_AVAILABLE = False
            logger.warning("Ollama 模块不可用,返回错误响应")
            await websocket.send_json({
                "type": "error",
                "error": {"message": "LLM 服务暂时不可用"}
            })
            return

        logger.info(f"[WebSocket] 调用 Ollama 模型: {model}, 消息: {message[:50]}...")

        # 调用 Ollama API (非流式)
        try:
            import asyncio

            def call_ollama():
                client = ollama.Client(host='http://localhost:11434', timeout=60)
                response = client.chat(
                    model=model,
                    messages=[
                        {"role": "user", "content": message}
                    ],
                    stream=False
                )
                return response

            # 在单独线程中运行同步调用
            response = await asyncio.wait_for(
                asyncio.to_thread(call_ollama),
                timeout=60
            )

            # 提取回复内容
            reply = response.get("message", {}).get("content", "")

            logger.info(f"[WebSocket] Ollama 响应成功, 回复长度: {len(reply)}")

            # 发送响应
            await websocket.send_json({
                "type": "chat:response",
                "sessionId": session_id,
                "reply": reply,
                "model": model,
                "messageId": f"msg_{datetime.now(timezone.utc).timestamp()}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        except asyncio.TimeoutError:
            logger.error("[WebSocket] Ollama 调用超时")
            await websocket.send_json({
                "type": "error",
                "error": {"message": "请求超时,请稍后重试"}
            })
        except Exception as e:
            logger.error(f"[WebSocket] Ollama 调用失败: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "error": {"message": f"LLM 调用失败: {str(e)}"}
            })

    except Exception as e:
        logger.error(f"[WebSocket] 处理聊天消息失败: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "error": {"message": "处理消息失败"}
        })


async def handle_stream_message(websocket: WebSocket, user: User, data: dict):
    """处理流式消息"""
    stream_id = data.get("streamId")
    session_id = data.get("sessionId")
    message = data.get("message")

    try:
        # TODO: 实现实际的流式 LLM 调用
        # 这里先返回模拟的流式响应

        response_text = f"这是对 '{message}' 的流式回复。"

        # 模拟分块发送
        chunk_size = 5
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i+chunk_size]

            await websocket.send_json({
                "type": f"stream:{stream_id}:chunk",
                "data": chunk,
                "metadata": {
                    "tokens": len(chunk),
                    "filtered": False
                }
            })

            await asyncio.sleep(0.1)  # 模拟延迟

        # 发送结束信号
        await websocket.send_json({
            "type": f"stream:{stream_id}:end"
        })

    except Exception as e:
        await websocket.send_json({
            "type": f"stream:{stream_id}:error",
            "error": {"message": str(e)}
        })


async def handle_policy_sync(websocket: WebSocket, user: User, data: dict):
    """处理策略同步请求"""
    # TODO: 从数据库获取用户的策略
    # 这里先返回模拟策略

    policy = {
        "version": 1,
        "patterns": {
            "email": r"[\w.-]+@[\w.-]+\.\w+",
            "phone": r"\d{3}-\d{3,4}-\d{4}",
        },
        "keywords": ["敏感词1", "敏感词2"],
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }

    await websocket.send_json({
        "type": "policy:update",
        "policy": policy,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def push_policy_update(user_id: str, policy: dict):
    """推送策略更新到客户端"""
    await manager.broadcast_to_user(user_id, {
        "type": "policy_update",
        "policy": policy,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def force_logout(user_id: str, reason: str):
    """强制用户下线"""
    await manager.broadcast_to_user(user_id, {
        "type": "force_logout",
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    # 断开所有连接
    client_ids = list(manager.get_user_clients(user_id))
    for client_id in client_ids:
        if client_id in manager.active_connections:
            await manager.active_connections[client_id].close(code=4002, reason=reason)
            manager.disconnect(client_id, user_id)
