"""JWT Token工具类。"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from jose import JWTError, jwt

from src.auth.models.session import TokenPayload
from src.config import settings


class JWTManager:
    """JWT Token管理工具类。"""

    # 从配置中获取密钥,如果没有则使用默认值
    SECRET_KEY: str = settings.web.secret_key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @classmethod
    def create_access_token(
        cls,
        user_id: str,
        username: str,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌。

        Args:
            user_id: 用户ID
            username: 用户名
            email: 邮箱
            role: 角色
            expires_delta: 过期时间增量

        Returns:
            JWT访问令牌
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        payload = {
            "sub": user_id,
            "username": username,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # JWT ID,用于会话管理
            "type": "access"
        }

        encoded_jwt = jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def create_refresh_token(
        cls,
        user_id: str,
        username: str,
        email: str,
        role: str
    ) -> str:
        """创建刷新令牌。

        Args:
            user_id: 用户ID
            username: 用户名
            email: 邮箱
            role: 角色

        Returns:
            JWT刷新令牌
        """
        expire = datetime.utcnow() + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": user_id,
            "username": username,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        }

        encoded_jwt = jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def decode_token(cls, token: str) -> Optional[TokenPayload]:
        """解码JWT令牌。

        Args:
            token: JWT令牌

        Returns:
            解码后的载荷,如果无效则返回None
        """
        try:
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )

            # 转换时间戳为datetime
            exp_timestamp = payload.get("exp")
            iat_timestamp = payload.get("iat")

            token_data = TokenPayload(
                sub=payload.get("sub"),
                username=payload.get("username"),
                email=payload.get("email"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(exp_timestamp) if exp_timestamp else datetime.utcnow(),
                iat=datetime.fromtimestamp(iat_timestamp) if iat_timestamp else datetime.utcnow(),
                jti=payload.get("jti")
            )

            return token_data

        except JWTError:
            return None

    @classmethod
    def verify_token(cls, token: str) -> bool:
        """验证JWT令牌是否有效。

        Args:
            token: JWT令牌

        Returns:
            令牌是否有效
        """
        token_data = cls.decode_token(token)
        if not token_data:
            return False

        # 检查是否过期
        if token_data.exp < datetime.utcnow():
            return False

        return True

    @classmethod
    def get_user_id_from_token(cls, token: str) -> Optional[str]:
        """从令牌中获取用户ID。

        Args:
            token: JWT令牌

        Returns:
            用户ID,如果无效则返回None
        """
        token_data = cls.decode_token(token)
        if not token_data:
            return None

        return token_data.sub

    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Optional[str]:
        """使用刷新令牌生成新的访问令牌。

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的访问令牌,如果刷新令牌无效则返回None
        """
        token_data = cls.decode_token(refresh_token)
        if not token_data:
            return None

        # 验证是否为刷新令牌
        try:
            payload = jwt.decode(
                refresh_token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM]
            )
            if payload.get("type") != "refresh":
                return None
        except JWTError:
            return None

        # 创建新的访问令牌
        new_access_token = cls.create_access_token(
            user_id=token_data.sub,
            username=token_data.username,
            email=token_data.email,
            role=token_data.role
        )

        return new_access_token

    @classmethod
    def get_token_expiry(cls, token: str) -> Optional[datetime]:
        """获取令牌过期时间。

        Args:
            token: JWT令牌

        Returns:
            过期时间,如果令牌无效则返回None
        """
        token_data = cls.decode_token(token)
        if not token_data:
            return None

        return token_data.exp
