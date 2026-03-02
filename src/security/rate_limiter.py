"""请求速率限制模块。"""

import json
import os
import time
from typing import Dict, Optional, Tuple

from fastapi import Request, HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from src.config import settings
from src.logger import logger
from src.security.api_auth import extract_api_key_from_request, api_key_manager

from src.utils.redis_client import redis_client


class RateLimiter:
    """请求速率限制器。"""

    def __init__(self):
        """初始化速率限制器。"""
        self.rate_limit_file = settings.security.rate_limit_path
        self.request_counts = {}  # 客户端ID -> {时间窗口开始时间, 请求计数}
        self.default_rate_limit = 60  # 默认每分钟60个请求
        self.window_size = 60  # 时间窗口大小（秒）
        self._load_request_counts()

    def _load_request_counts(self) -> None:
        """从文件加载请求计数。仅在没有Redis或初始化作为回退时使用。"""
        if not os.path.exists(self.rate_limit_file):
            os.makedirs(os.path.dirname(self.rate_limit_file), exist_ok=True)
            self.request_counts = {}
            return

        try:
            with open(self.rate_limit_file, "r") as f:
                data = json.load(f)
                # 过滤掉过期的计数
                current_time = time.time()
                self.request_counts = {
                    client_id: counts
                    for client_id, counts in data.items()
                    if current_time - counts["window_start"] < self.window_size
                }
            logger.info(f"成功加载本地请求计数作为后备，客户端数量: {len(self.request_counts)}")
        except Exception as e:
            logger.error(f"加载请求计数失败: {e}")
            self.request_counts = {}

    def _save_request_counts(self) -> None:
        """保存请求计数到文件。作为回退手段。"""
        try:
            current_time = time.time()
            filtered_counts = {
                client_id: counts
                for client_id, counts in self.request_counts.items()
                if current_time - counts["window_start"] < self.window_size
            }

            with open(self.rate_limit_file, "w") as f:
                json.dump(filtered_counts, f, indent=2)
            logger.debug(f"成功保存请求计数到文件: {self.rate_limit_file}")
        except Exception as e:
            logger.error(f"保存请求计数失败: {e}")

    def _get_client_id(self, request: Request) -> str:
        """获取客户端ID。

        首先尝试从请求中提取API密钥，如果存在则使用API密钥作为客户端ID。
        否则，使用客户端IP地址作为客户端ID。

        Args:
            request: 请求对象。

        Returns:
            客户端ID。
        """
        # 尝试从请求中提取API密钥
        api_key = extract_api_key_from_request(request)
        if api_key:
            return f"api_key:{api_key}"

        # 使用客户端IP地址
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _get_rate_limit(self, client_id: str) -> int:
        """获取客户端的速率限制。

        Args:
            client_id: 客户端ID。

        Returns:
            速率限制（每分钟请求数）。
        """
        # 如果是API密钥，从API密钥管理器获取速率限制
        if client_id.startswith("api_key:"):
            api_key = client_id.split(":", 1)[1]
            rate_limit = api_key_manager.get_rate_limit(api_key)
            if rate_limit > 0:
                return rate_limit

        # 默认速率限制
        return self.default_rate_limit

    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """检查请求是否超过速率限制（优先使用Redis）。

        Args:
            request: 请求对象。

        Returns:
            (是否允许请求, 速率限制信息)
        """
        if not settings.security.enable_rate_limiting:
            return True, {}

        client_id = self._get_client_id(request)
        rate_limit = self._get_rate_limit(client_id)
        current_time = time.time()
        
        # Redis Key format: rate_limit:client_id:window_start_epoch
        window_start = int(current_time // self.window_size * self.window_size)
        redis_key = f"rate_limit:{client_id}:{window_start}"

        current_count = None

        if getattr(redis_client, "_is_connected", False):
            try:
                # 1. 尝试使用 Redis 
                async with redis_client.client.pipeline(transaction=True) as pipe:
                    pipe.incr(redis_key)
                    pipe.expire(redis_key, self.window_size * 2) # Buffer expiry
                    result = await pipe.execute()
                    
                current_count = result[0]
            except Exception as e:
                logger.error(f"Redis 限流器出错 (将回退执行本地内存): {e}")
                # Redis 异常时不直接崩溃，允许向下走到内存逻辑
                
        if current_count is None:
            # 2. Redis 不可用：回退到本地内存
            if client_id not in self.request_counts:
                self.request_counts[client_id] = {
                    "window_start": current_time,
                    "count": 0
                }

            client_counts = self.request_counts[client_id]

            if current_time - client_counts["window_start"] >= self.window_size:
                client_counts["window_start"] = current_time
                client_counts["count"] = 0

            client_counts["count"] += 1
            current_count = client_counts["count"]
            
            # 定期保存本地计数
            if current_count % 10 == 0:
                self._save_request_counts()

        is_allowed = current_count <= rate_limit
        remaining = max(0, rate_limit - current_count)
        reset_time = window_start + self.window_size

        rate_limit_info = {
            "limit": rate_limit,
            "remaining": remaining,
            "reset": int(reset_time),
            "used": current_count
        }

        return is_allowed, rate_limit_info


# 创建全局速率限制器实例
rate_limiter = RateLimiter()


async def check_rate_limit(request: Request) -> None:
    """检查请求是否超过速率限制。

    Args:
        request: 请求对象。

    Raises:
        HTTPException: 如果请求超过速率限制。
    """
    is_allowed, rate_limit_info = await rate_limiter.check_rate_limit(request)

    # 添加速率限制头部
    request.state.rate_limit_info = rate_limit_info

    if not is_allowed:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="请求频率超过限制",
            headers={
                "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                "X-RateLimit-Reset": str(rate_limit_info["reset"]),
                "X-RateLimit-Used": str(rate_limit_info["used"]),
                "Retry-After": str(rate_limit_info["reset"] - int(time.time()))
            }
        )
