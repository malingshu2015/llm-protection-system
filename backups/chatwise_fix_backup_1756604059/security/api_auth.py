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
                # 管理员密钥（随机生成）
                "admin_" + str(uuid.uuid4()): {
                    "name": "Admin API Key",
                    "permissions": ["*"],  # 所有权限
                    "created_at": time.time(),
                    "rate_limit": 100,  # 每分钟请求数
                    "models": ["*"]  # 所有模型
                },
                # 第三方客户端预设密钥（固定，便于配置）
                "cherry-studio-key": {
                    "name": "Cherry Studio Client",
                    "permissions": ["chat", "models"],
                    "created_at": time.time(),
                    "rate_limit": 60,
                    "models": ["*"],
                    "description": "预设密钥，供Cherry Studio等第三方客户端使用"
                },
                "chatbox-key": {
                    "name": "ChatBox Client",
                    "permissions": ["chat", "models"],
                    "created_at": time.time(),
                    "rate_limit": 60,
                    "models": ["*"],
                    "description": "预设密钥，供ChatBox等第三方客户端使用"
                },
                "chatwise-key": {
                    "name": "ChatWise Client",
                    "permissions": ["chat", "models"],
                    "created_at": time.time(),
                    "rate_limit": 100,
                    "models": ["*"],
                    "description": "预设密钥，供ChatWise等第三方客户端使用",
                    "license": {
                        "max_clients": 50,
                        "license_type": "standard",
                        "client_timeout": 300
                    }
                },
                "api_key_123456": {
                    "name": "ChatWise Compatible Key",
                    "permissions": ["chat", "models"],
                    "created_at": time.time(),
                    "rate_limit": 100,
                    "models": ["*"],
                    "description": "兼容性密钥，支持api_key_开头格式",
                    "license": {
                        "max_clients": 50,
                        "license_type": "standard",
                        "client_timeout": 300
                    }
                },
                "demo-key-12345": {
                    "name": "Demo API Key",
                    "permissions": ["chat", "models"],
                    "created_at": time.time(),
                    "rate_limit": 30,
                    "models": ["*"],
                    "description": "演示密钥，用于测试和文档示例"
                }
            }
            with open(self.api_keys_file, "w") as f:
                json.dump(default_api_keys, f, indent=2)
            logger.info(f"创建了默认API密钥文件: {self.api_keys_file}")
            logger.info("添加了以下预设API密钥：")
            logger.info("- cherry-studio-key (Cherry Studio客户端)")
            logger.info("- chatbox-key (ChatBox客户端)")
            logger.info("- chatwise-key (ChatWise客户端)")
            logger.info("- api_key_123456 (ChatWise兼容密钥)")
            logger.info("- demo-key-12345 (演示密钥)")
            return default_api_keys

        # 从文件加载API密钥
        try:
            with open(self.api_keys_file, "r") as f:
                api_keys = json.load(f)
            logger.info(f"成功加载API密钥，数量: {len(api_keys)}")
            
            # 确保预设密钥存在
            api_keys = self._ensure_preset_keys(api_keys)
            return api_keys
        except Exception as e:
            logger.error(f"加载API密钥失败: {e}")
            return {}

    def _ensure_preset_keys(self, api_keys: Dict[str, Dict]) -> Dict[str, Dict]:
        """确保预设密钥存在。
        
        Args:
            api_keys: 现有的API密钥字典
            
        Returns:
            更新后的API密钥字典
        """
        preset_keys = {
            "cherry-studio-key": {
                "name": "Cherry Studio Client",
                "permissions": ["chat", "models"],
                "created_at": time.time(),
                "rate_limit": 60,
                "models": ["*"],
                "description": "预设密钥，供Cherry Studio等第三方客户端使用"
            },
            "chatbox-key": {
                "name": "ChatBox Client",
                "permissions": ["chat", "models"],
                "created_at": time.time(),
                "rate_limit": 60,
                "models": ["*"],
                "description": "预设密钥，供ChatBox等第三方客户端使用"
            },
            "chatwise-key": {
                "name": "ChatWise Client",
                "permissions": ["chat", "models"],
                "created_at": time.time(),
                "rate_limit": 100,
                "models": ["*"],
                "description": "预设密钥，供ChatWise等第三方客户端使用",
                "license": {
                    "max_clients": 50,
                    "license_type": "standard",
                    "client_timeout": 300
                }
            },
            "api_key_123456": {
                "name": "ChatWise Compatible Key",
                "permissions": ["chat", "models"],
                "created_at": time.time(),
                "rate_limit": 100,
                "models": ["*"],
                "description": "兼容性密钥，支持api_key_开头格式",
                "license": {
                    "max_clients": 50,
                    "license_type": "standard",
                    "client_timeout": 300
                }
            },
            "demo-key-12345": {
                "name": "Demo API Key",
                "permissions": ["chat", "models"],
                "created_at": time.time(),
                "rate_limit": 30,
                "models": ["*"],
                "description": "演示密钥，用于测试和文档示例"
            }
        }
        
        # 检查并添加缺失的预设密钥
        updated = False
        for key, config in preset_keys.items():
            if key not in api_keys:
                api_keys[key] = config
                updated = True
                logger.info(f"添加缺失的预设密钥: {key}")
        
        # 如果有更新，保存到文件
        if updated:
            try:
                with open(self.api_keys_file, "w") as f:
                    json.dump(api_keys, f, indent=2)
                logger.info("已更新API密钥文件，添加了缺失的预设密钥")
            except Exception as e:
                logger.error(f"保存更新的API密钥失败: {e}")
        
        return api_keys

    def save_api_keys(self) -> None:
        """保存API密钥到文件。"""
        try:
            with open(self.api_keys_file, "w") as f:
                json.dump(self.api_keys, f, indent=2)
            logger.info(f"成功保存API密钥到文件: {self.api_keys_file}")
        except Exception as e:
            logger.error(f"保存API密钥失败: {e}")

    def create_api_key(self, name: str, permissions: List[str], rate_limit: int, 
                      models: List[str], max_clients: int = 10, 
                      license_type: str = "standard") -> str:
        """创建新的API密钥。

        Args:
            name: API密钥名称。
            permissions: 权限列表。
            rate_limit: 速率限制（每分钟请求数）。
            models: 允许访问的模型列表。
            max_clients: 最大客户端连接数。
            license_type: 许可证类型。

        Returns:
            新创建的API密钥。
        """
        # 生成更适合第三方客户端的API密钥格式
        # 使用 'ck-' 前缀 (client key) + 8位随机字符串
        import secrets
        import string
        
        # 生成安全的随机字符串
        chars = string.ascii_letters + string.digits
        random_suffix = ''.join(secrets.choice(chars) for _ in range(24))
        api_key = f"ck-{random_suffix}"
        self.api_keys[api_key] = {
            "name": name,
            "permissions": permissions,
            "created_at": time.time(),
            "rate_limit": rate_limit,
            "models": models,
            "license": {
                "max_clients": max_clients,
                "license_type": license_type,
                "client_timeout": 300  # 默认5分钟超时
            }
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

    def get_license_config(self, api_key: str) -> Dict:
        """获取API密钥的许可证配置。

        Args:
            api_key: API密钥。

        Returns:
            许可证配置字典。
        """
        if not self.validate_api_key(api_key):
            return {"max_clients": 0, "license_type": "invalid"}

        api_key_info = self.api_keys[api_key]
        license_config = api_key_info.get("license", {})
        
        # 提供默认值
        return {
            "max_clients": license_config.get("max_clients", 10),
            "license_type": license_config.get("license_type", "standard"),
            "client_timeout": license_config.get("client_timeout", 300)
        }

    def update_license_config(self, api_key: str, max_clients: int = None, 
                            license_type: str = None) -> bool:
        """更新API密钥的许可证配置。

        Args:
            api_key: API密钥。
            max_clients: 新的最大客户端数。
            license_type: 新的许可证类型。

        Returns:
            是否更新成功。
        """
        if not self.validate_api_key(api_key):
            return False

        api_key_info = self.api_keys[api_key]
        
        # 确保license字段存在
        if "license" not in api_key_info:
            api_key_info["license"] = {}

        if max_clients is not None:
            api_key_info["license"]["max_clients"] = max_clients
        
        if license_type is not None:
            api_key_info["license"]["license_type"] = license_type

        self.save_api_keys()
        return True


# 创建全局API密钥管理器实例
api_key_manager = APIKeyManager()

# 创建API密钥头部依赖
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(request: Request, api_key_from_header: str = Depends(api_key_header)) -> str:
    """获取并验证API密钥。
    
    优先从Authorization Bearer头部获取，其次从X-API-Key头部获取。

    Args:
        request: 请求对象。
        api_key_from_header: 从X-API-Key头部获取的API密钥。

    Returns:
        验证通过的API密钥。

    Raises:
        HTTPException: 如果API密钥无效。
    """
    # 首先尝试从Authorization Bearer头部获取（标准方式）
    api_key = extract_api_key_from_request(request)
    
    # 如果没有从Authorization获取到，尝试从X-API-Key头部获取（兼容性）
    if not api_key:
        api_key = api_key_from_header
        
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


async def check_client_license(request: Request, api_key: str = Depends(get_api_key)) -> str:
    """检查客户端许可证限制并生成客户端ID。

    Args:
        request: 请求对象。
        api_key: API密钥。

    Returns:
        客户端ID。

    Raises:
        HTTPException: 如果超出许可证限制。
    """
    from src.security.license_manager import client_tracker
    
    # 生成客户端ID（基于IP和用户代理）
    client_ip = request.client.host if hasattr(request, 'client') else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    client_id = f"{api_key[:8]}_{client_ip}_{hash(user_agent) % 10000}"
    
    # 检查许可证限制
    license_config = api_key_manager.get_license_config(api_key)
    max_clients = license_config["max_clients"]
    current_count = client_tracker.get_active_count(api_key)
    
    if current_count >= max_clients:
        raise HTTPException(
            status_code=429,
            detail=f"客户端连接数超出许可证限制: {current_count}/{max_clients}"
        )
    
    # 注册客户端
    registered = await client_tracker.register_client(api_key, client_id, client_ip, user_agent)
    if not registered:
        raise HTTPException(
            status_code=429,
            detail="客户端注册失败，请稍后重试"
        )
    
    return client_id


def extract_api_key_from_request(request: Request) -> Optional[str]:
    """从请求中提取API密钥。

    Args:
        request: 请求对象。

    Returns:
        API密钥，如果不存在则返回None。
    """
    # 从Authorization头部获取 Bearer Token（优先级最高，大多数第三方客户端使用此方式）
    auth_header = request.headers.get("Authorization")
    if auth_header:
        auth_header = auth_header.strip()
        if not auth_header:
            # 空的Authorization头，继续尝试其他方式
            pass
        elif auth_header.startswith("Bearer "):
            # 标准Bearer Token格式
            api_key = auth_header[7:].strip()
            if api_key and len(api_key) >= 3:  # 最小长度检查
                logger.debug(f"从Authorization头部提取API密钥: Bearer {api_key[:8]}...")
                # 调试日志：记录提取的完整密钥（仅显示前8个字符保护隐私）
                logger.debug(f"提取的API密钥（前8位）: {api_key[:8]}...")
                return api_key
        elif auth_header.startswith("Token "):
            # Token前缀格式（一些客户端使用）
            api_key = auth_header[6:].strip()
            if api_key and len(api_key) >= 3:
                logger.debug(f"从Authorization头部提取API密钥: Token {api_key[:8]}...")
                return api_key
        elif not auth_header.startswith("Basic ") and not auth_header.startswith("Digest "):
            # 直接使用Authorization头部的值（排除HTTP Basic和Digest认证）
            api_key = auth_header.strip()
            if api_key and len(api_key) >= 3:
                logger.debug(f"从Authorization头部提取API密钥（直接）: {api_key[:8]}...")
                return api_key

    # 定义要检查的头部列表（按优先级排序）
    header_names = [
        "X-API-Key",     # 标准API密钥头
        "x-api-key",     # 小写版本
        "api-key",       # 简化版本
        "API-Key",       # 大写版本
        "openai-api-key", # OpenAI特定
    ]
    
    for header_name in header_names:
        api_key = request.headers.get(header_name)
        if api_key:
            api_key = api_key.strip()
            if api_key and len(api_key) >= 3:
                logger.debug(f"从{header_name}头部提取API密钥: {api_key[:8]}...")
                return api_key

    # 从查询参数获取（按优先级排序）
    query_param_names = ["api_key", "token", "key"]
    for param_name in query_param_names:
        api_key = request.query_params.get(param_name)
        if api_key:
            api_key = api_key.strip()
            if api_key and len(api_key) >= 3:
                logger.debug(f"从{param_name}查询参数提取API密钥: {api_key[:8]}...")
                return api_key

    # 从cookie获取（最低优先级）
    cookie_names = ["api_key", "token", "auth_token"]
    for cookie_name in cookie_names:
        api_key = request.cookies.get(cookie_name)
        if api_key:
            api_key = api_key.strip()
            if api_key and len(api_key) >= 3:
                logger.debug(f"从{cookie_name} cookie提取API密钥: {api_key[:8]}...")
                return api_key

    logger.debug("未找到有效的API密钥")
    return None
