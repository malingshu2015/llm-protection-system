"""用户会话数据模型。"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field


class UserSession(BaseModel):
    """用户会话模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    token: str  # JWT access token
    refresh_token: str  # JWT refresh token
    ip_address: str
    user_agent: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_revoked: bool = False

    @staticmethod
    def calculate_expiry(minutes: int = 15) -> datetime:
        """计算过期时间。

        Args:
            minutes: 有效期分钟数

        Returns:
            过期时间
        """
        return datetime.utcnow() + timedelta(minutes=minutes)

    def is_expired(self) -> bool:
        """检查会话是否过期。

        Returns:
            是否过期
        """
        return datetime.utcnow() > self.expires_at or self.is_revoked

    def update_activity(self) -> None:
        """更新最后活动时间。"""
        self.last_activity = datetime.utcnow()

    class Config:
        """Pydantic配置。"""

        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0..."
            }
        }


class LoginRequest(BaseModel):
    """登录请求模型。"""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)
    remember_me: bool = False

    class Config:
        """Pydantic配置。"""

        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123",
                "remember_me": False
            }
        }


class LoginResponse(BaseModel):
    """登录响应模型。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数
    user: dict  # UserResponse

    class Config:
        """Pydantic配置。"""

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "role": "viewer"
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """刷新Token请求模型。"""

    refresh_token: str

    class Config:
        """Pydantic配置。"""

        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
            }
        }


class TokenPayload(BaseModel):
    """JWT Token载荷模型。"""

    sub: str  # subject (user_id)
    username: str
    email: str
    role: str
    exp: datetime  # expiration time
    iat: datetime  # issued at
    jti: Optional[str] = None  # JWT ID (用于会话管理)

    class Config:
        """Pydantic配置。"""

        json_schema_extra = {
            "example": {
                "sub": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "email": "john@example.com",
                "role": "viewer",
                "exp": "2024-12-31T23:59:59",
                "iat": "2024-12-31T00:00:00"
            }
        }
