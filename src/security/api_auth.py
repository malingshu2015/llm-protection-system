"""API认证和授权模块。"""

import json
import os
import time
import uuid
from typing import Dict, List, Optional, Set

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from src.config import settings
from src.logger import logger


class APIKeyManager:
    """API密钥管理器。"""

    def __init__(self):
        """初始化API密钥管理器。"""
        self.api_keys_file = settings.security.api_keys_path
        self.api_keys = self._load_api_keys()

    def _load_api_keys(self) -> Dict[str, Dict]:
        """从文件加载API密钥。

        Returns:
            API密钥字典，键为API密钥，值为包含权限等信息的字典。
        """
        # 如果文件不存在，创建默认API密钥
        if not os.path.exists(self.api_keys_file):
            os.makedirs(os.path.dirname(self.api_keys_file), exist_ok=True)
            default_api_keys = {
                "admin_" + str(uuid.uuid4()): {
                    "name": "Admin API Key",
                    "permissions": ["*"],  # 所有权限
                    "created_at": time.time(),
                    "rate_limit": 100,  # 每分钟请求数
                    "models": ["*"]  # 所有模型
                }
            }
            with open(self.api_keys_file, "w") as f:
                json.dump(default_api_keys, f, indent=2)
            logger.info(f"创建了默认API密钥文件: {self.api_keys_file}")
            return default_api_keys

        # 从文件加载API密钥
        try:
            with open(self.api_keys_file, "r") as f:
                api_keys = json.load(f)
            logger.info(f"成功加载API密钥，数量: {len(api_keys)}")
            return api_keys
        except Exception as e:
            logger.error(f"加载API密钥失败: {e}")
            return {}

    def save_api_keys(self) -> None:
        """保存API密钥到文件。"""
        try:
            with open(self.api_keys_file, "w") as f:
                json.dump(self.api_keys, f, indent=2)
            logger.info(f"成功保存API密钥到文件: {self.api_keys_file}")
        except Exception as e:
            logger.error(f"保存API密钥失败: {e}")

    def create_api_key(self, name: str, permissions: List[str], rate_limit: int, models: List[str]) -> str:
        """创建新的API密钥。

        Args:
            name: API密钥名称。
            permissions: 权限列表。
            rate_limit: 速率限制（每分钟请求数）。
            models: 允许访问的模型列表。

        Returns:
            新创建的API密钥。
        """
        api_key = str(uuid.uuid4())
        self.api_keys[api_key] = {
            "name": name,
            "permissions": permissions,
            "created_at": time.time(),
            "rate_limit": rate_limit,
            "models": models
        }
        self.save_api_keys()
        return api_key

    def delete_api_key(self, api_key: str) -> bool:
        """删除API密钥。

        Args:
            api_key: 要删除的API密钥。

        Returns:
            是否成功删除。
        """
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            self.save_api_keys()
            return True
        return False

    def get_api_key_info(self, api_key: str) -> Optional[Dict]:
        """获取API密钥信息。

        Args:
            api_key: API密钥。

        Returns:
            API密钥信息，如果不存在则返回None。
        """
        return self.api_keys.get(api_key)

    def validate_api_key(self, api_key: str) -> bool:
        """验证API密钥是否有效。

        Args:
            api_key: API密钥。

        Returns:
            API密钥是否有效。
        """
        return api_key in self.api_keys

    def check_permission(self, api_key: str, permission: str) -> bool:
        """检查API密钥是否有指定权限。

        Args:
            api_key: API密钥。
            permission: 权限名称。

        Returns:
            是否有权限。
        """
        if not self.validate_api_key(api_key):
            return False

        api_key_info = self.api_keys[api_key]
        permissions = api_key_info.get("permissions", [])

        # 如果有通配符权限，则允许所有操作
        if "*" in permissions:
            return True

        return permission in permissions

    def check_model_access(self, api_key: str, model: str) -> bool:
        """检查API密钥是否有权访问指定模型。

        Args:
            api_key: API密钥。
            model: 模型名称。

        Returns:
            是否有权访问。
        """
        if not self.validate_api_key(api_key):
            return False

        api_key_info = self.api_keys[api_key]
        allowed_models = api_key_info.get("models", [])

        # 如果有通配符，则允许访问所有模型
        if "*" in allowed_models:
            return True

        return model in allowed_models

    def get_rate_limit(self, api_key: str) -> int:
        """获取API密钥的速率限制。

        Args:
            api_key: API密钥。

        Returns:
            速率限制（每分钟请求数）。
        """
        if not self.validate_api_key(api_key):
            return 0

        api_key_info = self.api_keys[api_key]
        return api_key_info.get("rate_limit", 0)


# 创建全局API密钥管理器实例
api_key_manager = APIKeyManager()

# 创建API密钥头部依赖
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    """获取并验证API密钥。

    Args:
        api_key: API密钥。

    Returns:
        验证通过的API密钥。

    Raises:
        HTTPException: 如果API密钥无效。
    """
    if api_key is None:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="缺少API密钥",
        )

    if not api_key_manager.validate_api_key(api_key):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="无效的API密钥",
        )

    return api_key


async def check_api_permission(permission: str, api_key: str = Depends(get_api_key)) -> None:
    """检查API密钥是否有指定权限。

    Args:
        permission: 权限名称。
        api_key: API密钥。

    Raises:
        HTTPException: 如果没有权限。
    """
    if not api_key_manager.check_permission(api_key, permission):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"没有权限: {permission}",
        )


async def check_model_access(model: str, api_key: str = Depends(get_api_key)) -> None:
    """检查API密钥是否有权访问指定模型。

    Args:
        model: 模型名称。
        api_key: API密钥。

    Raises:
        HTTPException: 如果没有权限访问模型。
    """
    if not api_key_manager.check_model_access(api_key, model):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"没有权限访问模型: {model}",
        )


def extract_api_key_from_request(request: Request) -> Optional[str]:
    """从请求中提取API密钥。

    Args:
        request: 请求对象。

    Returns:
        API密钥，如果不存在则返回None。
    """
    # 从头部获取
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    # 从Authorization头部获取
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # 移除"Bearer "前缀

    # 从查询参数获取
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key

    # 从cookie获取
    api_key = request.cookies.get("api_key")
    if api_key:
        return api_key

    return None
