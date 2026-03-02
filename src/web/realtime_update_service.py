"""实时模型更新服务 - WebSocket实现"""

import asyncio
import json
import hashlib
import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum
import websockets
from fastapi import WebSocket, WebSocketDisconnect

from src.logger import logger
from src.config import settings

class UpdateType(str, Enum):
    MODEL_ADD = "model_add"
    MODEL_REMOVE = "model_remove" 
    VERSION_CHANGE = "version_change"
    SECURITY_UPDATE = "security_update"
    METADATA_UPDATE = "metadata_update"

@dataclass
class ModelUpdate:
    type: UpdateType
    model_id: str
    timestamp: int
    version: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    change_type: Optional[str] = None  # major, minor, patch

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # model_id -> connection_ids
        
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"客户端连接建立: {connection_id}")
        
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            # 清理订阅
            for model_id in list(self.subscriptions.keys()):
                if connection_id in self.subscriptions[model_id]:
                    self.subscriptions[model_id].remove(connection_id)
            logger.info(f"客户端连接断开: {connection_id}")
    
    async def subscribe(self, connection_id: str, model_id: str):
        if model_id not in self.subscriptions:
            self.subscriptions[model_id] = set()
        self.subscriptions[model_id].add(connection_id)
        logger.info(f"客户端 {connection_id} 订阅模型 {model_id}")
    
    async def unsubscribe(self, connection_id: str, model_id: str):
        if model_id in self.subscriptions and connection_id in self.subscriptions[model_id]:
            self.subscriptions[model_id].remove(connection_id)
            logger.info(f"客户端 {connection_id} 取消订阅模型 {model_id}")
    
    async def broadcast_update(self, update: ModelUpdate):
        """广播更新给所有订阅者"""
        message = {
            "type": update.type.value,
            "model_id": update.model_id,
            "timestamp": update.timestamp,
            "version": update.version,
            "checksum": update.checksum,
            "metadata": update.metadata,
            "change_type": update.change_type
        }
        
        json_message = json.dumps(message)
        connections_to_notify = set()
        
        # 获取需要通知的连接
        if update.model_id in self.subscriptions:
            connections_to_notify.update(self.subscriptions[update.model_id])
        
        # 广播给所有订阅者
        for connection_id in connections_to_notify:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_text(json_message)
                    logger.debug(f"向 {connection_id} 发送更新通知: {update.model_id}")
                except Exception as e:
                    logger.error(f"发送更新通知失败 {connection_id}: {e}")
                    self.disconnect(connection_id)

class VersionDetector:
    """版本检测器"""
    
    def __init__(self):
        self.model_versions: Dict[str, str] = {}
        self.model_hashes: Dict[str, str] = {}
        
    def generate_hash(self, model_data: Dict[str, Any]) -> str:
        """生成模型数据哈希"""
        data_str = json.dumps(model_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def detect_changes(self, current_models: List[Dict[str, Any]]) -> List[ModelUpdate]:
        """检测模型变化并生成更新列表"""
        updates = []
        current_hashes = {}
        
        for model in current_models:
            model_id = model.get('id') or model.get('model')
            if not model_id:
                continue
                
            model_hash = self.generate_hash(model)
            current_hashes[model_id] = model_hash
            
            # 检测新模型
            if model_id not in self.model_hashes:
                updates.append(ModelUpdate(
                    type=UpdateType.MODEL_ADD,
                    model_id=model_id,
                    timestamp=int(time.time()),
                    version=model.get('version'),
                    checksum=model_hash,
                    metadata=model
                ))
            
            # 检测版本变化
            elif self.model_hashes[model_id] != model_hash:
                updates.append(ModelUpdate(
                    type=UpdateType.VERSION_CHANGE,
                    model_id=model_id,
                    timestamp=int(time.time()),
                    version=model.get('version'),
                    checksum=model_hash,
                    metadata=model,
                    change_type=self.determine_change_type(model_id, model)
                ))
        
        # 检测删除的模型
        removed_models = set(self.model_hashes.keys()) - set(current_hashes.keys())
        for model_id in removed_models:
            updates.append(ModelUpdate(
                type=UpdateType.MODEL_REMOVE,
                model_id=model_id,
                timestamp=int(time.time())
            ))
        
        # 更新存储的状态
        self.model_hashes = current_hashes
        return updates
    
    def determine_change_type(self, model_id: str, new_model: Dict[str, Any]) -> str:
        """确定变更类型 (major/minor/patch)"""
        # 简化实现：基于版本号变化判断
        # 实际项目中应该使用semver解析版本号
        old_version = self.model_versions.get(model_id, '0.0.0')
        new_version = new_model.get('version', '0.0.0')
        
        if old_version.split('.')[0] != new_version.split('.')[0]:
            return 'major'
        elif old_version.split('.')[1] != new_version.split('.')[1]:
            return 'minor'
        else:
            return 'patch'

class RealTimeUpdateService:
    """实时更新服务"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.version_detector = VersionDetector()
        self.is_monitoring = False
        
    async def start_monitoring(self, poll_interval: int = 30):
        """启动模型监控"""
        self.is_monitoring = True
        logger.info(f"启动模型实时监控，轮询间隔: {poll_interval}秒")
        
        while self.is_monitoring:
            try:
                # 这里需要从实际的数据源获取模型列表
                # 暂时使用空列表，实际实现需要连接到模型数据源
                current_models = await self.fetch_current_models()
                updates = self.version_detector.detect_changes(current_models)
                
                for update in updates:
                    await self.connection_manager.broadcast_update(update)
                    logger.info(f"检测到模型更新: {update.type} - {update.model_id}")
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"模型监控错误: {e}")
                await asyncio.sleep(5)  # 错误时短暂等待
    
    async def fetch_current_models(self) -> List[Dict[str, Any]]:
        """从Ollama API获取当前模型列表"""
        try:
            import httpx
            import os
            
            # 获取Ollama模型列表
            ollama_host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{ollama_host}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('models', [])
                    
                    # 转换为标准格式
                    formatted_models = []
                    for model in models:
                        model_id = model.get('name', '')
                        if model_id:
                            formatted_models.append({
                                'id': model_id,
                                'model': model_id,
                                'name': model_id.split(':')[0],
                                'version': model_id.split(':')[1] if ':' in model_id else 'latest',
                                'size': model.get('size', 0),
                                'modified_at': model.get('modified_at', ''),
                                'details': model.get('details', {})
                            })
                    
                    return formatted_models
                else:
                    logger.warning(f"获取Ollama模型列表失败: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"获取模型数据错误: {e}")
            return []
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        logger.info("停止模型实时监控")
    
    def get_recent_updates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的模型更新记录（用于HTTP轮询）"""
        # 这里返回一个空的更新列表，实际实现应该从数据库或缓存中获取
        # 由于这是简化实现，返回一个示例响应
        return [
            {
                "type": "version_check",
                "timestamp": int(time.time()),
                "message": "HTTP轮询模式 - 使用WebSocket获取实时更新",
                "polling": True
            }
        ]

# 全局实例
realtime_service = RealTimeUpdateService()

async def start_realtime_service():
    """启动实时服务"""
    asyncio.create_task(realtime_service.start_monitoring())

async def stop_realtime_service():
    """停止实时服务"""
    realtime_service.stop_monitoring()