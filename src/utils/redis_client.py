"""Redis Client Wrapper."""

import json
from typing import Any, Optional, Union

import redis.asyncio as redis
from pydantic import Field
from pydantic_settings import BaseSettings

from src.logger import logger


class RedisConfig(BaseSettings):
    """Redis configuration."""
    
    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    max_connections: int = Field(default=10, description="Maximum number of connections in the pool")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    decode_responses: bool = Field(default=True, description="Decode responses to strings")

    model_config = {
        "env_prefix": "REDIS_",
        "extra": "ignore"
    }


class RedisClient:
    """Async Redis client wrapper."""
    
    def __init__(self, config: Optional[RedisConfig] = None):
        self._config = config or RedisConfig()
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._is_connected = False

    @property
    def client(self) -> redis.Redis:
        if self._client is None or not self._is_connected:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self._client
        
    async def connect(self) -> None:
        """Initialize the Redis connection pool and client."""
        if self._is_connected:
            return
            
        try:
            self._pool = redis.ConnectionPool.from_url(
                url=self._config.url,
                max_connections=self._config.max_connections,
                decode_responses=self._config.decode_responses,
                socket_timeout=self._config.socket_timeout
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Simple ping to test connection
            await self._client.ping()
            self._is_connected = True
            logger.info(f"Successfully connected to Redis at {self._config.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._is_connected = False
            # We don't raise here to allow fallback to in-memory mechanisms if needed
            
    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.disconnect()
        self._is_connected = False
        logger.info("Disconnected from Redis")

    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from Redis."""
        if not self._is_connected:
            return None
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error fetching {key} from Redis: {e}")
            return None
            
    async def set_json(self, key: str, value: Any, ex: int = None) -> bool:
        """Set a JSON value in Redis."""
        if not self._is_connected:
            return False
        try:
            return await self.client.set(key, json.dumps(value), ex=ex)
        except Exception as e:
            logger.error(f"Error setting {key} in Redis: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self._is_connected:
            return False
        try:
            return await self.client.delete(key) > 0
        except Exception as e:
            logger.error(f"Error deleting {key} from Redis: {e}")
            return False

# Global Redis client instance
redis_client = RedisClient()

