"""API密钥认证工具。"""

from typing import Optional

from fastapi import Header, HTTPException, Request, status

from src.auth.models.user import User
from src.auth.services.api_key_service import api_key_service
from src.logger import logger


async def get_user_from_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[User]:
    """从请求头中的API密钥获取用户(依赖注入函数)。

    Args:
        request: HTTP请求
        x_api_key: API密钥(从X-API-Key请求头获取)

    Returns:
        用户对象,如果验证失败则返回None
    """
    if not x_api_key:
        return None

    # 获取客户端IP
    client_ip = request.client.host if request.client else None

    # 验证API密钥
    result = await api_key_service.verify_api_key(x_api_key, client_ip)

    if not result:
        return None

    api_key, user = result
    logger.debug(f"API密钥认证成功: {api_key.name} (用户: {user.username})")

    return user


async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> User:
    """要求API密钥认证(依赖注入函数)。

    Args:
        request: HTTP请求
        x_api_key: API密钥

    Returns:
        用户对象

    Raises:
        HTTPException: API密钥无效或缺失
    """
    user = await get_user_from_api_key(request, x_api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥或密钥已过期",
            headers={"WWW-Authenticate": "X-API-Key"}
        )

    return user


async def get_user_from_token_or_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[User]:
    """支持JWT Token或API密钥认证(优先使用JWT)。

    Args:
        request: HTTP请求
        x_api_key: API密钥

    Returns:
        用户对象,如果两种方式都失败则返回None
    """
    # 首先尝试从JWT Token获取用户
    if hasattr(request.state, "user"):
        return request.state.user

    # 如果没有JWT Token,尝试使用API密钥
    return await get_user_from_api_key(request, x_api_key)


async def require_auth(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> User:
    """要求JWT Token或API密钥认证。

    Args:
        request: HTTP请求
        x_api_key: API密钥

    Returns:
        用户对象

    Raises:
        HTTPException: 未认证
    """
    user = await get_user_from_token_or_api_key(request, x_api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证:请提供JWT Token或API密钥",
            headers={"WWW-Authenticate": "Bearer, X-API-Key"}
        )

    return user
