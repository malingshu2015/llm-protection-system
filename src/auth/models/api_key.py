from pydantic import ConfigDict
"""API密钥数据模型。"""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class APIKey(BaseModel):
    """API密钥模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    key_hash: str  # SHA256加密后的密钥
    key_prefix: str  # 显示用前缀,如 "sk-xxxxx..."
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)  # 权限范围
    rate_limit: Optional[int] = None  # 每小时请求限制
    ip_whitelist: List[str] = Field(default_factory=list)
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

    @staticmethod
    def generate_key() -> str:
        """生成新的API密钥。

        Returns:
            生成的API密钥字符串
        """
        # 生成32字节的随机密钥
        random_bytes = secrets.token_bytes(32)
        # 转换为hex字符串
        key = f"sk-{random_bytes.hex()}"
        return key

    @staticmethod
    def hash_key(key: str) -> str:
        """对密钥进行SHA256哈希。

        Args:
            key: 原始密钥

        Returns:
            哈希后的密钥
        """
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def get_key_prefix(key: str) -> str:
        """获取密钥显示前缀。

        Args:
            key: 原始密钥

        Returns:
            密钥前缀(前12个字符)
        """
        if len(key) <= 12:
            return key
        return f"{key[:12]}..."

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "name": "Production API Key",
                "description": "用于生产环境的API密钥",
                "scopes": ["chat", "models"],
                "rate_limit": 1000,
                "ip_whitelist": ["192.168.1.1"]
            }
        })


class APIKeyCreate(BaseModel):
    """创建API密钥请求模型。"""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["chat"])
    rate_limit: Optional[int] = Field(default=1000, ge=1, le=10000)
    ip_whitelist: List[str] = Field(default_factory=list)
    expires_days: Optional[int] = Field(default=None, ge=1, le=365)

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "name": "Dev API Key",
                "description": "开发环境测试密钥",
                "scopes": ["chat", "models"],
                "rate_limit": 100,
                "expires_days": 90
            }
        })


class APIKeyUpdate(BaseModel):
    """更新API密钥请求模型。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(default=None, ge=1, le=10000)
    ip_whitelist: Optional[List[str]] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """API密钥响应模型。"""

    id: str
    user_id: str
    key_prefix: str
    name: str
    description: Optional[str]
    scopes: List[str]
    rate_limit: Optional[int]
    ip_whitelist: List[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]
    usage_count: int

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(BaseModel):
    """创建API密钥响应模型(包含完整密钥,仅在创建时返回一次)。"""

    api_key: str  # 完整的API密钥,仅此一次显示
    key_info: APIKeyResponse

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "api_key": "sk-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "key_info": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "key_prefix": "sk-0123456789...",
                    "name": "Production Key",
                    "scopes": ["chat", "models"],
                    "is_active": True
                }
            }
        })
