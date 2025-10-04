"""OAuth2认证 API路由。"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.models.oauth import (
    OAuthProvider,
    OAuthAuthorizationRequest,
    OAuthCallbackRequest,
    OAuthAccountResponse,
    OAuthLoginResponse,
)
from src.auth.models.user import UserCreate, UserRole
from src.auth.models.audit import AuditActionType, AuditLogLevel
from src.auth.services.oauth_service import oauth_service
from src.auth.services.auth_service import auth_service
from src.auth.services.user_db import user_db
from src.auth.services.audit_service import audit_service
from src.logger import logger

router = APIRouter(prefix="/api/v1/oauth", tags=["OAuth2认证"])
security = HTTPBearer()


@router.get("/authorize/{provider}")
async def oauth_authorize(provider: str) -> dict:
    """获取OAuth授权URL。

    Args:
        provider: OAuth提供商 (google/github)

    Returns:
        授权URL

    Raises:
        HTTPException: 获取失败
    """
    try:
        # 验证提供商
        try:
            oauth_provider = OAuthProvider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth提供商: {provider}"
            )

        # 获取授权URL
        auth_url = await oauth_service.get_authorization_url(oauth_provider)

        return {
            "authorization_url": auth_url,
            "provider": provider
        }

    except ValueError as e:
        logger.warning(f"获取OAuth授权URL失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取OAuth授权URL异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取授权URL失败"
        )


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request
) -> RedirectResponse:
    """OAuth回调处理。

    Args:
        provider: OAuth提供商
        code: 授权码
        state: state参数
        request: HTTP请求对象

    Returns:
        重定向响应

    Raises:
        HTTPException: 处理失败
    """
    try:
        # 验证提供商
        try:
            oauth_provider = OAuthProvider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth提供商: {provider}"
            )

        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 交换令牌
        token_data = await oauth_service.exchange_code_for_token(
            oauth_provider, code, state
        )

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        # 获取用户信息
        user_info = await oauth_service.get_user_info(oauth_provider, access_token)

        provider_user_id = user_info["provider_user_id"]
        provider_username = user_info.get("username")
        provider_email = user_info.get("email")

        # 查找是否已有用户链接此OAuth账户
        user_id = await oauth_service.find_user_by_provider_id(
            oauth_provider, provider_user_id
        )

        is_new_user = False

        if user_id:
            # 已有用户，更新OAuth账户信息
            user = await user_db.get_user_by_id(user_id)
            if not user:
                raise ValueError("用户不存在")

            # 更新OAuth账户
            await oauth_service.link_account(
                user_id=user_id,
                provider=oauth_provider,
                provider_user_id=provider_user_id,
                provider_username=provider_username,
                provider_email=provider_email,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )

            # 记录审计日志
            await audit_service.log_action(
                action_type=AuditActionType.USER_LOGIN,
                action_description=f"通过{provider}登录成功",
                user_id=user.id,
                username=user.username,
                ip_address=client_ip,
                level=AuditLogLevel.INFO,
                success=True,
                metadata={"provider": provider, "provider_username": provider_username}
            )

        else:
            # 新用户，创建账户
            if not provider_email:
                raise ValueError("OAuth提供商未返回邮箱地址，无法创建账户")

            # 生成唯一用户名
            base_username = provider_username or provider_email.split("@")[0]
            username = base_username
            counter = 1
            while await user_db.get_user_by_username(username):
                username = f"{base_username}{counter}"
                counter += 1

            # 创建用户
            user_create = UserCreate(
                username=username,
                email=provider_email,
                password="",  # OAuth用户无密码
                role=UserRole.USER,
            )

            user = await auth_service.register_user(user_create, ip_address=client_ip)
            user_id = user.id
            is_new_user = True

            # 链接OAuth账户
            await oauth_service.link_account(
                user_id=user_id,
                provider=oauth_provider,
                provider_user_id=provider_user_id,
                provider_username=provider_username,
                provider_email=provider_email,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )

            # 自动验证邮箱
            user.is_verified = True
            await user_db.update_user(user)

            # 记录审计日志
            await audit_service.log_action(
                action_type=AuditActionType.USER_REGISTER,
                action_description=f"通过{provider}注册并登录",
                user_id=user.id,
                username=user.username,
                ip_address=client_ip,
                level=AuditLogLevel.INFO,
                success=True,
                metadata={"provider": provider, "provider_username": provider_username}
            )

        # 创建会话
        user_agent = request.headers.get("user-agent", "unknown")
        login_response, session = await auth_service.login_with_user(
            user=user,
            ip_address=client_ip,
            user_agent=user_agent,
            remember_me=True
        )

        # 重定向到前端，带上令牌
        redirect_url = f"/static/index.html?access_token={login_response.access_token}&refresh_token={login_response.refresh_token}&is_new_user={is_new_user}"
        return RedirectResponse(url=redirect_url, status_code=302)

    except ValueError as e:
        logger.warning(f"OAuth回调处理失败: {str(e)}")
        # 重定向到登录页面并显示错误
        return RedirectResponse(
            url=f"/static/admin/login.html?error={str(e)}",
            status_code=302
        )
    except Exception as e:
        logger.error(f"OAuth回调处理异常: {str(e)}")
        return RedirectResponse(
            url="/static/admin/login.html?error=登录失败",
            status_code=302
        )


@router.post("/link/{provider}", status_code=status.HTTP_200_OK)
async def link_oauth_account(
    provider: str,
    code: str,
    state: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """链接OAuth账户到当前用户。

    Args:
        provider: OAuth提供商
        code: 授权码
        state: state参数
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 链接失败
    """
    try:
        # 验证提供商
        try:
            oauth_provider = OAuthProvider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth提供商: {provider}"
            )

        # 验证令牌
        token = credentials.credentials
        user = await auth_service.verify_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 交换令牌
        token_data = await oauth_service.exchange_code_for_token(
            oauth_provider, code, state
        )

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        # 获取用户信息
        user_info = await oauth_service.get_user_info(oauth_provider, access_token)

        # 链接账户
        await oauth_service.link_account(
            user_id=user.id,
            provider=oauth_provider,
            provider_user_id=user_info["provider_user_id"],
            provider_username=user_info.get("username"),
            provider_email=user_info.get("email"),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

        # 记录审计日志
        await audit_service.log_action(
            action_type=AuditActionType.SYSTEM_CONFIG_CHANGE,
            action_description=f"链接{provider}账户",
            user_id=user.id,
            username=user.username,
            level=AuditLogLevel.INFO,
            success=True,
            metadata={"provider": provider, "provider_username": user_info.get("username")}
        )

        return {
            "message": f"{provider}账户链接成功",
            "provider": provider,
            "provider_username": user_info.get("username")
        }

    except ValueError as e:
        logger.warning(f"链接OAuth账户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"链接OAuth账户异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="链接账户失败"
        )


@router.delete("/unlink/{provider}", status_code=status.HTTP_200_OK)
async def unlink_oauth_account(
    provider: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """取消链接OAuth账户。

    Args:
        provider: OAuth提供商
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 取消链接失败
    """
    try:
        # 验证提供商
        try:
            oauth_provider = OAuthProvider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth提供商: {provider}"
            )

        # 验证令牌
        token = credentials.credentials
        user = await auth_service.verify_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 取消链接
        await oauth_service.unlink_account(user.id, oauth_provider)

        # 记录审计日志
        await audit_service.log_action(
            action_type=AuditActionType.SYSTEM_CONFIG_CHANGE,
            action_description=f"取消链接{provider}账户",
            user_id=user.id,
            username=user.username,
            level=AuditLogLevel.INFO,
            success=True,
            metadata={"provider": provider}
        )

        return {"message": f"{provider}账户已取消链接"}

    except ValueError as e:
        logger.warning(f"取消链接OAuth账户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消链接OAuth账户异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消链接失败"
        )


@router.get("/accounts", response_model=list[OAuthAccountResponse])
async def get_oauth_accounts(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> list[OAuthAccountResponse]:
    """获取当前用户的所有OAuth账户。

    Args:
        credentials: HTTP授权凭证

    Returns:
        OAuth账户列表

    Raises:
        HTTPException: 获取失败
    """
    try:
        # 验证令牌
        token = credentials.credentials
        user = await auth_service.verify_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 获取OAuth账户
        accounts = await oauth_service.get_all_accounts(user.id)
        return accounts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取OAuth账户异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取账户列表失败"
        )
