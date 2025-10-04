"""OAuth2认证服务。"""

import json
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode

import httpx
from pydantic import EmailStr

from src.auth.models.oauth import (
    OAuthProvider,
    OAuthAccount,
    OAuthLoginResponse,
    OAuthAccountResponse,
)
from src.auth.models.user import User, UserCreate, UserRole
from src.auth.models.session import LoginResponse
from src.logger import logger


class OAuthService:
    """OAuth2认证服务类。"""

    def __init__(self, storage_dir: str = "data/oauth"):
        """初始化OAuth服务。

        Args:
            storage_dir: OAuth数据存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, OAuthAccount]] = {}  # {user_id: {provider: account}}
        self._state_cache: Dict[str, Dict[str, Any]] = {}  # {state: {provider, created_at}}
        self._load_all()

        # OAuth配置 (从环境变量读取)
        import os

        self.google_config = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "userinfo_uri": "https://www.googleapis.com/oauth2/v2/userinfo",
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/oauth/callback/google"),
            "scopes": ["openid", "email", "profile"],
        }

        self.github_config = {
            "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
            "auth_uri": "https://github.com/login/oauth/authorize",
            "token_uri": "https://github.com/login/oauth/access_token",
            "userinfo_uri": "https://api.github.com/user",
            "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/v1/oauth/callback/github"),
            "scopes": ["read:user", "user:email"],
        }

    def _get_storage_path(self, user_id: str) -> Path:
        """获取用户OAuth存储路径。

        Args:
            user_id: 用户ID

        Returns:
            存储路径
        """
        return self.storage_dir / f"{user_id}.json"

    def _load_all(self) -> None:
        """从磁盘加载所有OAuth账户。"""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        user_id = file_path.stem
                        self._cache[user_id] = {}
                        for provider_str, account_data in data.items():
                            account = OAuthAccount(**account_data)
                            self._cache[user_id][provider_str] = account
                except Exception as e:
                    logger.error(f"加载OAuth账户失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"加载OAuth账户失败: {str(e)}")

    def _save(self, user_id: str, accounts: Dict[str, OAuthAccount]) -> None:
        """保存用户的OAuth账户到磁盘。

        Args:
            user_id: 用户ID
            accounts: OAuth账户字典 {provider: account}
        """
        try:
            self._cache[user_id] = accounts
            file_path = self._get_storage_path(user_id)

            data = {
                provider: account.model_dump(mode="json")
                for provider, account in accounts.items()
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            logger.error(f"保存OAuth账户失败: {str(e)}")
            raise

    def _get_provider_config(self, provider: OAuthProvider) -> Dict[str, Any]:
        """获取OAuth提供商配置。

        Args:
            provider: OAuth提供商

        Returns:
            提供商配置
        """
        if provider == OAuthProvider.GOOGLE:
            return self.google_config
        elif provider == OAuthProvider.GITHUB:
            return self.github_config
        else:
            raise ValueError(f"不支持的OAuth提供商: {provider}")

    def _generate_state(self, provider: OAuthProvider) -> str:
        """生成OAuth state参数。

        Args:
            provider: OAuth提供商

        Returns:
            state字符串
        """
        state = secrets.token_urlsafe(32)
        self._state_cache[state] = {
            "provider": provider,
            "created_at": datetime.utcnow(),
        }
        return state

    def _verify_state(self, state: str, provider: OAuthProvider) -> bool:
        """验证OAuth state参数。

        Args:
            state: state字符串
            provider: OAuth提供商

        Returns:
            是否有效
        """
        state_data = self._state_cache.get(state)
        if not state_data:
            return False

        # 检查是否过期 (10分钟)
        if datetime.utcnow() - state_data["created_at"] > timedelta(minutes=10):
            del self._state_cache[state]
            return False

        # 验证提供商
        if state_data["provider"] != provider:
            return False

        # 验证成功后删除
        del self._state_cache[state]
        return True

    async def get_authorization_url(self, provider: OAuthProvider) -> str:
        """获取OAuth授权URL。

        Args:
            provider: OAuth提供商

        Returns:
            授权URL
        """
        config = self._get_provider_config(provider)

        if not config["client_id"]:
            raise ValueError(f"{provider.value} OAuth未配置")

        state = self._generate_state(provider)

        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
            "state": state,
        }

        # GitHub需要额外的access_type参数
        if provider == OAuthProvider.GOOGLE:
            params["access_type"] = "offline"
            params["prompt"] = "consent"

        url = f"{config['auth_uri']}?{urlencode(params)}"
        logger.info(f"生成{provider.value} OAuth授权URL")
        return url

    async def exchange_code_for_token(
        self, provider: OAuthProvider, code: str, state: str
    ) -> Dict[str, Any]:
        """用授权码交换访问令牌。

        Args:
            provider: OAuth提供商
            code: 授权码
            state: state参数

        Returns:
            令牌数据

        Raises:
            ValueError: 验证失败
        """
        # 验证state
        if not self._verify_state(state, provider):
            raise ValueError("无效的state参数")

        config = self._get_provider_config(provider)

        # 交换令牌
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
        }

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_uri"], data=data, headers=headers, timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"交换令牌失败: {response.text}")
                raise ValueError(f"交换令牌失败: {response.status_code}")

            token_data = response.json()

        logger.info(f"成功获取{provider.value} OAuth令牌")
        return token_data

    async def get_user_info(
        self, provider: OAuthProvider, access_token: str
    ) -> Dict[str, Any]:
        """获取OAuth用户信息。

        Args:
            provider: OAuth提供商
            access_token: 访问令牌

        Returns:
            用户信息
        """
        config = self._get_provider_config(provider)

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                config["userinfo_uri"], headers=headers, timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"获取用户信息失败: {response.text}")
                raise ValueError(f"获取用户信息失败: {response.status_code}")

            user_info = response.json()

        # 标准化用户信息
        if provider == OAuthProvider.GOOGLE:
            standardized = {
                "provider_user_id": user_info["id"],
                "email": user_info.get("email"),
                "username": user_info.get("email", "").split("@")[0],
                "name": user_info.get("name"),
                "avatar_url": user_info.get("picture"),
            }
        elif provider == OAuthProvider.GITHUB:
            standardized = {
                "provider_user_id": str(user_info["id"]),
                "email": user_info.get("email"),
                "username": user_info.get("login"),
                "name": user_info.get("name"),
                "avatar_url": user_info.get("avatar_url"),
            }
        else:
            standardized = user_info

        logger.info(f"获取{provider.value}用户信息: {standardized['username']}")
        return standardized

    async def link_account(
        self,
        user_id: str,
        provider: OAuthProvider,
        provider_user_id: str,
        provider_username: Optional[str],
        provider_email: Optional[EmailStr],
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> OAuthAccount:
        """链接OAuth账户到用户。

        Args:
            user_id: 用户ID
            provider: OAuth提供商
            provider_user_id: 提供商用户ID
            provider_username: 提供商用户名
            provider_email: 提供商邮箱
            access_token: 访问令牌
            refresh_token: 刷新令牌
            expires_in: 令牌过期时间(秒)

        Returns:
            OAuth账户

        Raises:
            ValueError: 账户已被其他用户链接
        """
        # 检查是否已被其他用户链接
        for uid, accounts in self._cache.items():
            if uid != user_id:
                for p, account in accounts.items():
                    if p == provider.value and account.provider_user_id == provider_user_id:
                        raise ValueError(f"该{provider.value}账户已被其他用户链接")

        # 创建或更新账户
        accounts = self._cache.get(user_id, {})

        token_expires_at = None
        if expires_in:
            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_username=provider_username,
            provider_email=provider_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            updated_at=datetime.utcnow(),
        )

        accounts[provider.value] = oauth_account
        self._save(user_id, accounts)

        logger.info(f"用户 {user_id} 链接了 {provider.value} 账户")
        return oauth_account

    async def get_account(
        self, user_id: str, provider: OAuthProvider
    ) -> Optional[OAuthAccount]:
        """获取用户的OAuth账户。

        Args:
            user_id: 用户ID
            provider: OAuth提供商

        Returns:
            OAuth账户或None
        """
        accounts = self._cache.get(user_id, {})
        return accounts.get(provider.value)

    async def get_all_accounts(self, user_id: str) -> list[OAuthAccountResponse]:
        """获取用户的所有OAuth账户。

        Args:
            user_id: 用户ID

        Returns:
            OAuth账户列表
        """
        accounts = self._cache.get(user_id, {})
        return [
            OAuthAccountResponse(
                id=account.id,
                provider=account.provider,
                provider_username=account.provider_username,
                provider_email=account.provider_email,
                created_at=account.created_at,
                last_used=account.last_used,
            )
            for account in accounts.values()
        ]

    async def unlink_account(self, user_id: str, provider: OAuthProvider) -> bool:
        """取消链接OAuth账户。

        Args:
            user_id: 用户ID
            provider: OAuth提供商

        Returns:
            是否成功

        Raises:
            ValueError: 账户未链接
        """
        accounts = self._cache.get(user_id, {})

        if provider.value not in accounts:
            raise ValueError(f"{provider.value}账户未链接")

        del accounts[provider.value]

        if accounts:
            self._save(user_id, accounts)
        else:
            # 如果没有OAuth账户了，删除文件
            file_path = self._get_storage_path(user_id)
            if file_path.exists():
                file_path.unlink()
            del self._cache[user_id]

        logger.info(f"用户 {user_id} 取消链接 {provider.value} 账户")
        return True

    async def find_user_by_provider_id(
        self, provider: OAuthProvider, provider_user_id: str
    ) -> Optional[str]:
        """通过提供商ID查找用户。

        Args:
            provider: OAuth提供商
            provider_user_id: 提供商用户ID

        Returns:
            用户ID或None
        """
        for user_id, accounts in self._cache.items():
            account = accounts.get(provider.value)
            if account and account.provider_user_id == provider_user_id:
                return user_id
        return None


# 创建全局OAuth服务实例
oauth_service = OAuthService()
