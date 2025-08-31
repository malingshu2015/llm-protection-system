"""客户端许可证管理模块。"""

import time
import uuid
from typing import Dict, Set, Optional, List
from dataclasses import dataclass
from datetime import datetime

from src.logger import logger
from src.config import settings


@dataclass
class ClientInfo:
    """客户端信息。"""
    client_id: str
    api_key: str
    ip_address: str
    user_agent: str
    connected_at: float
    last_activity: float
    session_id: Optional[str] = None


@dataclass  
class LicenseConfig:
    """许可证配置。"""
    max_clients: int = 10  # 最大客户端数量
    client_timeout: int = 300  # 客户端超时时间(秒)
    allow_concurrent: bool = True  # 是否允许并发连接
    license_type: str = "standard"  # 许可证类型
    features: List[str] = None  # 许可证特性
    
    def __post_init__(self):
        if self.features is None:
            self.features = ["basic"]


class ClientTracker:
    """客户端连接跟踪器。"""
    
    def __init__(self):
        self.active_clients: Dict[str, Set[str]] = {}  # api_key -> client_ids
        self.client_info: Dict[str, ClientInfo] = {}   # client_id -> 客户端信息
        self._lock = None  # 用于线程安全
        
    def initialize(self):
        """初始化客户端跟踪器。"""
        try:
            import asyncio
            self._lock = asyncio.Lock()
        except ImportError:
            # 同步环境使用 threading
            import threading
            self._lock = threading.Lock()
        
        logger.info("客户端跟踪器初始化完成")
    
    async def register_client(self, api_key: str, client_id: str, 
                            ip_address: str, user_agent: str) -> bool:
        """注册客户端连接。
        
        Args:
            api_key: API密钥
            client_id: 客户端ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            是否注册成功
        """
        if self._lock is None:
            self.initialize()
            
        async with self._lock:
            # 清理过期客户端
            await self._cleanup_expired_clients()
            
            # 检查是否已存在
            if client_id in self.client_info:
                logger.warning(f"客户端 {client_id} 已存在，更新活动时间")
                self.client_info[client_id].last_activity = time.time()
                return True
            
            # 检查客户端数量限制
            current_count = len(self.active_clients.get(api_key, set()))
            from src.security.api_auth import api_key_manager
            license_config = api_key_manager.get_license_config(api_key)
            max_clients = license_config["max_clients"]
            
            if current_count >= max_clients:
                logger.warning(f"API密钥 {api_key[:8]}... 客户端数超出限制: {current_count}/{max_clients}")
                return False
            
            # 注册新客户端
            client_info = ClientInfo(
                client_id=client_id,
                api_key=api_key,
                ip_address=ip_address,
                user_agent=user_agent,
                connected_at=time.time(),
                last_activity=time.time(),
                session_id=str(uuid.uuid4())
            )
            
            self.client_info[client_id] = client_info
            
            # 添加到活跃客户端集合
            if api_key not in self.active_clients:
                self.active_clients[api_key] = set()
            self.active_clients[api_key].add(client_id)
            
            logger.info(f"注册客户端: {client_id} for API密钥 {api_key[:8]}... "
                       f"(当前: {len(self.active_clients[api_key])}/{max_clients})")
            return True
    
    async def unregister_client(self, client_id: str):
        """注销客户端连接。"""
        if self._lock is None:
            self.initialize()
            
        async with self._lock:
            if client_id in self.client_info:
                client_info = self.client_info[client_id]
                api_key = client_info.api_key
                
                # 从活跃客户端中移除
                if api_key in self.active_clients and client_id in self.active_clients[api_key]:
                    self.active_clients[api_key].remove(client_id)
                    if not self.active_clients[api_key]:
                        del self.active_clients[api_key]
                
                # 从客户端信息中移除
                del self.client_info[client_id]
                
                logger.info(f"注销客户端: {client_id}")
    
    async def update_client_activity(self, client_id: str):
        """更新客户端活动时间。"""
        if client_id in self.client_info:
            self.client_info[client_id].last_activity = time.time()
    
    def get_active_count(self, api_key: str) -> int:
        """获取活跃客户端数量。"""
        return len(self.active_clients.get(api_key, set()))
    
    def get_client_info(self, client_id: str) -> Optional[ClientInfo]:
        """获取客户端信息。"""
        return self.client_info.get(client_id)
    
    def get_all_clients(self) -> List[ClientInfo]:
        """获取所有客户端信息。"""
        return list(self.client_info.values())
    
    def get_clients_by_api_key(self, api_key: str) -> List[ClientInfo]:
        """按API密钥获取客户端。"""
        client_ids = self.active_clients.get(api_key, set())
        return [self.client_info[cid] for cid in client_ids if cid in self.client_info]
    
    async def _cleanup_expired_clients(self):
        """清理过期客户端。"""
        current_time = time.time()
        expired_clients = []
        
        for client_id, info in self.client_info.items():
            # 检查客户端是否超时（5分钟无活动）
            if current_time - info.last_activity > 300:  # 5分钟
                expired_clients.append(client_id)
        
        # 清理过期客户端
        for client_id in expired_clients:
            await self.unregister_client(client_id)
            logger.debug(f"清理过期客户端: {client_id}")
    
    def get_stats(self) -> Dict:
        """获取统计信息。"""
        total_clients = len(self.client_info)
        total_api_keys = len(self.active_clients)
        
        stats = {
            "total_clients": total_clients,
            "total_api_keys": total_api_keys,
            "clients_per_key": {},
            "timestamp": time.time()
        }
        
        for api_key, client_ids in self.active_clients.items():
            stats["clients_per_key"][api_key[:8] + "..."] = len(client_ids)
        
        return stats


# 全局客户端跟踪器实例
client_tracker = ClientTracker()