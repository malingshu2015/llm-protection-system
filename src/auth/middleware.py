"""认证中间件。"""

from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth.models.user import User, UserRole
from src.auth.services.auth_service import auth_service
from src.logger import logger

security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件,用于保护需要登录的API。"""

    # 白名单路径,不需要认证
    WHITELIST_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static",
        "/favicon.ico",
        "/"
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求。

        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器

        Returns:
            HTTP响应
        """
        # 检查是否在白名单中
        if self._is_whitelisted(request.url.path):
            return await call_next(request)

        # 从请求头中获取令牌
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未提供认证令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 解析令牌
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的认证方案,应使用Bearer",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证格式",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 验证令牌
        user = await auth_service.verify_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌或用户不存在",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 将用户信息附加到请求状态
        request.state.user = user

        # 继续处理请求
        return await call_next(request)

    def _is_whitelisted(self, path: str) -> bool:
        """检查路径是否在白名单中。

        Args:
            path: 请求路径

        Returns:
            是否在白名单中
        """
        for whitelist_path in self.WHITELIST_PATHS:
            if path.startswith(whitelist_path):
                return True
        return False


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """从请求中获取当前用户(依赖注入函数)。

    Args:
        request: HTTP请求
        credentials: HTTP认证凭据

    Returns:
        当前用户对象

    Raises:
        HTTPException: 用户未认证
    """
    # 优先从request.state中获取(如果中间件已设置)
    if hasattr(request.state, "user"):
        return request.state.user

    # 否则从Authorization头中提取并验证JWT token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    # 验证JWT token
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌或用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 缓存到request.state中
    request.state.user = user
    return user


async def require_role(required_role: UserRole):
    """角色权限检查装饰器。

    Args:
        required_role: 需要的角色

    Returns:
        依赖注入函数
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        """检查用户角色。

        Args:
            user: 当前用户

        Returns:
            当前用户

        Raises:
            HTTPException: 权限不足
        """
        # 超级管理员拥有所有权限
        if user.role == UserRole.SUPER_ADMIN:
            return user

        # 检查角色权限
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.DEVELOPER: 2,
            UserRole.SECURITY_ANALYST: 3,
            UserRole.ADMIN: 4,
            UserRole.SUPER_ADMIN: 5
        }

        if role_hierarchy.get(user.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )

        return user

    return role_checker


# 便捷的角色依赖
async def require_admin(request: Request) -> User:
    """要求管理员权限。"""
    user = await get_current_user(request)
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user


async def require_super_admin(request: Request) -> User:
    """要求超级管理员权限。"""
    user = await get_current_user(request)
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return user
