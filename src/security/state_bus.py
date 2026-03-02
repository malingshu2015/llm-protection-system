"""
系统状态总线模块 (基于 Redis Pub/Sub)
用于节点间广播高危对话阻断等关键状态事件，实现分布式环境的主备状态一致性 (M2.3)。
"""
import asyncio
import json
from typing import Callable, List, Optional
from src.utils.redis_client import redis_client
from src.logger import logger

class RedisStateBus:
    def __init__(self):
        self.channel_name = "llm_shield:state_bus"
        self._callbacks: List[Callable] = []
        self._listen_task: Optional[asyncio.Task] = None
        
    def register_callback(self, callback: Callable):
        """注册状态变更回调函数 (通常是 async 函数)"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            
    async def start_listening(self):
        """启动后台Pub/Sub监听任务"""
        if not getattr(redis_client, "_is_connected", False):
            logger.warning("Redis客户端未连接，状态总线将不进行跨节点同步 (降级模式)")
            return
            
        if self._listen_task is not None and not self._listen_task.done():
            return
            
        pubsub = redis_client.client.pubsub()
        try:
            await pubsub.subscribe(self.channel_name)
        except Exception as e:
            logger.error(f"订阅状态总线频道失败: {e}")
            return
        
        async def listen_loop():
            try:
                logger.info(f"状态总线集群网络接入成功，监听通道: {self.channel_name}")
                while True:
                    try:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message and message['type'] == 'message':
                            data = json.loads(message['data'])
                            event_type = data.get("type", "unknown")
                            payload = data.get("payload", {})
                            logger.info(f"🌍 状态总线收到跨节点集群事件: [{event_type}] payload={payload}")
                            
                            for cb in self._callbacks:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb(event_type, payload)
                                else:
                                    cb(event_type, payload)
                    except Exception as loop_e:
                        pass
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                logger.info("状态总线监听任务已正常取消")
            finally:
                await pubsub.unsubscribe(self.channel_name)
                
        self._listen_task = asyncio.create_task(listen_loop())
        
    async def broadcast(self, event_type: str, payload: dict):
        """广播状态变更到所有其他集群节点"""
        if not getattr(redis_client, "_is_connected", False):
            return
            
        try:
            msg = json.dumps({"type": event_type, "payload": payload})
            await redis_client.client.publish(self.channel_name, msg)
            logger.debug(f"📤 已向集群网络广播状态事件 [{event_type}]")
        except Exception as e:
            logger.error(f"广播状态事件失败: {e}")

# Global instance
state_bus = RedisStateBus()
