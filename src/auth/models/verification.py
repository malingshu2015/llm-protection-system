"""邮箱验证相关数据模型。"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class VerificationType(str, Enum):
    """验证类型枚举。"""

    EMAIL_VERIFICATION = "email_verification"  # 邮箱验证
    PASSWORD_RESET = "password_reset"          # 密码重置


class VerificationCode(BaseModel):
    """验证码模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    email: EmailStr
    code: str  # 6位数字验证码
    verification_type: VerificationType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_used: bool = False
    used_at: Optional[datetime] = None
    ip_address: Optional[str] = None

    @classmethod
    def create_verification_code(
        cls,
        user_id: str,
        email: EmailStr,
        verification_type: VerificationType,
        ip_address: Optional[str] = None,
        expires_in_minutes: int = 30
    ) -> "VerificationCode":
        """创建新的验证码。

        Args:
            user_id: 用户ID
            email: 用户邮箱
            verification_type: 验证类型
            ip_address: 请求IP地址
            expires_in_minutes: 过期时间(分钟)

        Returns:
            验证码对象
        """
        import random
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        return cls(
            user_id=user_id,
            email=email,
            code=code,
            verification_type=verification_type,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
            ip_address=ip_address
        )

    def is_valid(self) -> bool:
        """检查验证码是否有效。

        Returns:
            是否有效
        """
        return not self.is_used and datetime.now(timezone.utc) < self.expires_at

    def mark_as_used(self) -> None:
        """标记验证码为已使用。"""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)


class SendVerificationEmailRequest(BaseModel):
    """发送验证邮件请求模型。"""

    email: EmailStr


class VerifyEmailRequest(BaseModel):
    """验证邮箱请求模型。"""

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class SendPasswordResetEmailRequest(BaseModel):
    """发送密码重置邮件请求模型。"""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """重置密码请求模型。"""

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=100)
