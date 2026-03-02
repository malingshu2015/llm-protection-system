from pydantic import ConfigDict
"""用户数据模型。"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """用户角色枚举。"""

    SUPER_ADMIN = "super_admin"        # 超级管理员
    ADMIN = "admin"                    # 管理员
    SECURITY_ANALYST = "security_analyst"  # 安全分析员
    DEVELOPER = "developer"            # 开发者
    VIEWER = "viewer"                  # 只读用户


class User(BaseModel):
    """用户模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    phone: Optional[str] = None
    password_hash: str  # bcrypt加密后的密码
    salt: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: UserRole = UserRole.VIEWER
    department: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    login_attempts: int = 0
    locked_until: Optional[datetime] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    avatar_url: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名。"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线和连字符")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """验证手机号。"""
        if v is not None:
            # 简单的中国手机号验证
            if not (v.isdigit() and len(v) == 11 and v[0] == "1"):
                raise ValueError("无效的手机号码")
        return v

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "phone": "13800138000",
                "role": "viewer",
                "department": "开发部"
            }
        })


class UserCreate(BaseModel):
    """创建用户请求模型。"""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    phone: Optional[str] = None
    role: UserRole = UserRole.VIEWER
    department: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度。"""
        if len(v) < 8:
            raise ValueError("密码长度至少为8个字符")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError("密码必须包含大写字母、小写字母和数字")

        return v


class UserUpdate(BaseModel):
    """更新用户请求模型。"""

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应模型(不包含敏感信息)。"""

    id: str
    username: str
    email: EmailStr
    phone: Optional[str]
    role: UserRole
    department: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    avatar_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型。"""

    old_password: str
    new_password: str = Field(min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度。"""
        if len(v) < 8:
            raise ValueError("密码长度至少为8个字符")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError("密码必须包含大写字母、小写字母和数字")

        return v

