"""OAuth2认证数据模型。"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OAuthProvider(str, Enum):
    """OAuth提供商枚举。"""

    GOOGLE = "google"
    GITHUB = "github"


class OAuthAccount(BaseModel):
    """OAuth账户关联模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: OAuthProvider
    provider_user_id: str  # 提供商的用户ID
    provider_username: Optional[str] = None
    provider_email: Optional[str] = None
    access_token: Optional[str] = None  # 加密存储
    refresh_token: Optional[str] = None  # 加密存储
    token_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


class OAuthAuthorizationRequest(BaseModel):
    """OAuth授权请求模型。"""

    provider: OAuthProvider
    redirect_uri: str


class OAuthCallbackRequest(BaseModel):
    """OAuth回调请求模型。"""

    code: str
    state: str


class OAuthLinkAccountRequest(BaseModel):
    """OAuth账户链接请求模型。"""

    provider: OAuthProvider
    provider_user_id: str


class OAuthAccountResponse(BaseModel):
    """OAuth账户响应模型。"""

    id: str
    provider: OAuthProvider
    provider_username: Optional[str]
    provider_email: Optional[str]
    created_at: datetime
    last_used: Optional[datetime]


class OAuthLoginResponse(BaseModel):
    """OAuth登录响应模型。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict  # UserResponse
    is_new_user: bool = False
