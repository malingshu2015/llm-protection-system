"""双因素认证(2FA)数据模型。"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TwoFactorAuth(BaseModel):
    """双因素认证模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    secret: str  # TOTP密钥
    backup_codes: list[str] = Field(default_factory=list)  # 备用恢复码
    is_enabled: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    enabled_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


class Enable2FARequest(BaseModel):
    """启用2FA请求模型。"""

    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class Verify2FARequest(BaseModel):
    """验证2FA请求模型。"""

    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class Disable2FARequest(BaseModel):
    """禁用2FA请求模型。"""

    password: str
    code: Optional[str] = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")


class BackupCodeVerifyRequest(BaseModel):
    """备用码验证请求模型。"""

    backup_code: str


class Setup2FAResponse(BaseModel):
    """设置2FA响应模型。"""

    secret: str
    qr_code_url: str
    backup_codes: list[str]
    manual_entry_key: str


class TwoFactorStatus(BaseModel):
    """2FA状态响应模型。"""

    is_enabled: bool
    enabled_at: Optional[datetime] = None
    backup_codes_remaining: int = 0
