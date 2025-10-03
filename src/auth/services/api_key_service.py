"""API密钥服务。"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from src.auth.models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
)
from src.auth.models.user import User
from src.auth.services.user_db import user_db
from src.logger import logger


class APIKeyService:
    """API密钥服务类。"""

    async def create_api_key(
        self,
        user: User,
        key_data: APIKeyCreate
    ) -> Tuple[str, APIKeyResponse]:
        """创建API密钥。

        Args:
            user: 用户对象
            key_data: 密钥创建数据

        Returns:
            完整密钥和密钥信息的元组
        """
        # 生成新密钥
        api_key_str = APIKey.generate_key()

        # 计算过期时间
        expires_at = None
        if key_data.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=key_data.expires_days)

        # 创建密钥对象
        api_key = APIKey(
            user_id=user.id,
            key_hash=APIKey.hash_key(api_key_str),
            key_prefix=APIKey.get_key_prefix(api_key_str),
            name=key_data.name,
            description=key_data.description,
            scopes=key_data.scopes,
            rate_limit=key_data.rate_limit,
            ip_whitelist=key_data.ip_whitelist,
            expires_at=expires_at
        )

        # 保存到数据库
        await user_db.create_api_key(api_key)

        logger.info(f"用户 {user.username} 创建API密钥: {api_key.name}")

        # 构建响应
        key_response = APIKeyResponse(
            id=api_key.id,
            user_id=api_key.user_id,
            key_prefix=api_key.key_prefix,
            name=api_key.name,
            description=api_key.description,
            scopes=api_key.scopes,
            rate_limit=api_key.rate_limit,
            ip_whitelist=api_key.ip_whitelist,
            is_active=api_key.is_active,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count
        )

        return api_key_str, key_response

    async def get_api_key(self, key_id: str, user: User) -> Optional[APIKeyResponse]:
        """获取API密钥详情。

        Args:
            key_id: 密钥ID
            user: 当前用户

        Returns:
            密钥响应,如果不存在或无权限则返回None
        """
        api_key = await user_db.get_api_key_by_id(key_id)

        if not api_key:
            return None

        # 检查权限:只能查看自己的密钥
        if api_key.user_id != user.id:
            return None

        return APIKeyResponse(
            id=api_key.id,
            user_id=api_key.user_id,
            key_prefix=api_key.key_prefix,
            name=api_key.name,
            description=api_key.description,
            scopes=api_key.scopes,
            rate_limit=api_key.rate_limit,
            ip_whitelist=api_key.ip_whitelist,
            is_active=api_key.is_active,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count
        )

    async def list_api_keys(
        self,
        user: User,
        limit: int = 100,
        offset: int = 0
    ) -> List[APIKeyResponse]:
        """获取用户的API密钥列表。

        Args:
            user: 用户对象
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            密钥响应列表
        """
        api_keys = await user_db.list_api_keys_by_user(user.id, limit, offset)

        return [
            APIKeyResponse(
                id=key.id,
                user_id=key.user_id,
                key_prefix=key.key_prefix,
                name=key.name,
                description=key.description,
                scopes=key.scopes,
                rate_limit=key.rate_limit,
                ip_whitelist=key.ip_whitelist,
                is_active=key.is_active,
                expires_at=key.expires_at,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                usage_count=key.usage_count
            )
            for key in api_keys
        ]

    async def update_api_key(
        self,
        key_id: str,
        user: User,
        key_update: APIKeyUpdate
    ) -> Optional[APIKeyResponse]:
        """更新API密钥。

        Args:
            key_id: 密钥ID
            user: 当前用户
            key_update: 更新数据

        Returns:
            更新后的密钥响应,如果失败则返回None
        """
        # 检查密钥是否存在且有权限
        api_key = await user_db.get_api_key_by_id(key_id)
        if not api_key or api_key.user_id != user.id:
            return None

        # 准备更新数据
        updates = {}
        if key_update.name is not None:
            updates["name"] = key_update.name
        if key_update.description is not None:
            updates["description"] = key_update.description
        if key_update.scopes is not None:
            updates["scopes"] = key_update.scopes
        if key_update.rate_limit is not None:
            updates["rate_limit"] = key_update.rate_limit
        if key_update.ip_whitelist is not None:
            updates["ip_whitelist"] = key_update.ip_whitelist
        if key_update.is_active is not None:
            updates["is_active"] = int(key_update.is_active)

        # 执行更新
        if updates:
            await user_db.update_api_key(key_id, updates)

        # 返回更新后的密钥
        return await self.get_api_key(key_id, user)

    async def delete_api_key(self, key_id: str, user: User) -> bool:
        """删除API密钥。

        Args:
            key_id: 密钥ID
            user: 当前用户

        Returns:
            是否删除成功
        """
        # 检查密钥是否存在且有权限
        api_key = await user_db.get_api_key_by_id(key_id)
        if not api_key or api_key.user_id != user.id:
            return False

        # 删除密钥
        success = await user_db.delete_api_key(key_id)

        if success:
            logger.info(f"用户 {user.username} 删除API密钥: {api_key.name}")

        return success

    async def regenerate_api_key(
        self,
        key_id: str,
        user: User
    ) -> Optional[Tuple[str, APIKeyResponse]]:
        """重新生成API密钥。

        Args:
            key_id: 密钥ID
            user: 当前用户

        Returns:
            新密钥和密钥信息的元组,如果失败则返回None
        """
        # 检查密钥是否存在且有权限
        old_key = await user_db.get_api_key_by_id(key_id)
        if not old_key or old_key.user_id != user.id:
            return None

        # 生成新密钥
        new_key_str = APIKey.generate_key()

        # 更新密钥哈希和前缀
        updates = {
            "key_hash": APIKey.hash_key(new_key_str),
            "key_prefix": APIKey.get_key_prefix(new_key_str),
            "usage_count": 0,
            "last_used_at": None
        }

        await user_db.update_api_key(key_id, updates)

        logger.info(f"用户 {user.username} 重新生成API密钥: {old_key.name}")

        # 返回新密钥和更新后的信息
        key_response = await self.get_api_key(key_id, user)
        if key_response:
            return new_key_str, key_response

        return None

    async def verify_api_key(
        self,
        api_key_str: str,
        ip_address: Optional[str] = None
    ) -> Optional[Tuple[APIKey, User]]:
        """验证API密钥。

        Args:
            api_key_str: API密钥字符串
            ip_address: 客户端IP地址

        Returns:
            密钥和用户对象的元组,如果验证失败则返回None
        """
        # 计算密钥哈希
        key_hash = APIKey.hash_key(api_key_str)

        # 从数据库获取密钥
        api_key = await user_db.get_api_key_by_hash(key_hash)
        if not api_key:
            return None

        # 检查密钥是否激活
        if not api_key.is_active:
            logger.warning(f"使用已禁用的API密钥: {api_key.key_prefix}")
            return None

        # 检查密钥是否过期
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            logger.warning(f"使用已过期的API密钥: {api_key.key_prefix}")
            return None

        # 检查IP白名单
        if api_key.ip_whitelist and ip_address:
            if ip_address not in api_key.ip_whitelist:
                logger.warning(
                    f"IP {ip_address} 不在密钥 {api_key.key_prefix} 的白名单中"
                )
                return None

        # 获取用户信息
        user = await user_db.get_user_by_id(api_key.user_id)
        if not user or not user.is_active:
            return None

        # 更新使用记录
        await user_db.update_api_key_usage(api_key.id)

        return api_key, user


# 全局API密钥服务实例
api_key_service = APIKeyService()
