"""WebAuthn/FIDO2认证数据模型。"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WebAuthnCredential(BaseModel):
    """WebAuthn凭证模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    credential_id: str  # Base64URL编码的凭证ID
    public_key: str  # Base64URL编码的公钥
    sign_count: int = 0  # 签名计数器，用于检测克隆
    aaguid: Optional[str] = None  # 验证器AAGUID
    transports: list[str] = Field(default_factory=list)  # 传输方式: usb, nfc, ble, internal
    device_name: Optional[str] = None  # 设备名称
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    is_backup_eligible: bool = False  # 是否可备份
    is_backed_up: bool = False  # 是否已备份


class RegisterChallengeRequest(BaseModel):
    """注册挑战请求模型。"""

    username: str


class RegisterChallengeResponse(BaseModel):
    """注册挑战响应模型。"""

    challenge: str
    user_id: str
    rp_id: str
    rp_name: str
    timeout: int = 60000  # 60秒


class RegisterCredentialRequest(BaseModel):
    """注册凭证请求模型。"""

    credential_id: str
    public_key: str  # 保留用于向后兼容,专业库会从 attestation_object 提取
    attestation_object: str
    client_data_json: str
    transports: list[str] = Field(default_factory=list)
    device_name: Optional[str] = None
    challenge: Optional[str] = None  # 客户端保存的 challenge (用于查找服务器端缓存)


class AuthenticationChallengeRequest(BaseModel):
    """认证挑战请求模型。"""

    username: Optional[str] = None


class AuthenticationChallengeResponse(BaseModel):
    """认证挑战响应模型。"""

    challenge: str
    timeout: int = 60000
    rp_id: str
    allow_credentials: list[dict] = Field(default_factory=list)


class AuthenticationCredentialRequest(BaseModel):
    """认证凭证请求模型。"""

    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str
    user_handle: Optional[str] = None
    challenge: Optional[str] = None  # 客户端保存的 challenge (用于查找服务器端缓存)


class WebAuthnLoginResponse(BaseModel):
    """WebAuthn登录响应模型。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class WebAuthnCredentialResponse(BaseModel):
    """WebAuthn凭证响应模型。"""

    id: str
    credential_id: str
    device_name: Optional[str]
    transports: list[str]
    created_at: datetime
    last_used: Optional[datetime]
    sign_count: int
