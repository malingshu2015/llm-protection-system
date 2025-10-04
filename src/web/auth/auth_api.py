"""用户认证API路由。"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.models.session import LoginRequest, LoginResponse, RefreshTokenRequest
from src.auth.models.user import UserCreate, UserResponse
from src.auth.models.verification import (
    SendPasswordResetEmailRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
    ResetPasswordRequest,
)
from src.auth.services.auth_service import auth_service
from src.logger import logger

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: Request, user_data: UserCreate) -> UserResponse:
    """用户注册接口。

    Args:
        request: HTTP请求对象
        user_data: 用户创建数据

    Returns:
        创建的用户信息

    Raises:
        HTTPException: 注册失败
    """
    try:
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        user = await auth_service.register_user(user_data, ip_address=client_ip)
        return user
    except ValueError as e:
        logger.warning(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用户注册异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败,请稍后重试"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, login_data: LoginRequest) -> LoginResponse:
    """用户登录接口。

    Args:
        request: HTTP请求对象
        login_data: 登录数据

    Returns:
        登录响应(包含令牌和用户信息)

    Raises:
        HTTPException: 登录失败
    """
    try:
        # 获取客户端IP和User-Agent
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        login_response, session = await auth_service.login(
            username=login_data.username,
            password=login_data.password,
            ip_address=client_ip,
            user_agent=user_agent,
            remember_me=login_data.remember_me
        )

        return login_response

    except ValueError as e:
        logger.warning(f"用户登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"用户登录异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败,请稍后重试"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: RefreshTokenRequest) -> dict:
    """刷新访问令牌接口。

    Args:
        refresh_data: 刷新令牌数据

    Returns:
        新的访问令牌

    Raises:
        HTTPException: 刷新失败
    """
    try:
        new_access_token = await auth_service.refresh_token(refresh_data.refresh_token)

        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌无效或已过期",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌刷新异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新失败"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)) -> None:
    """用户登出接口。

    Args:
        credentials: HTTP授权凭证

    Raises:
        HTTPException: 登出失败
    """
    try:
        token = credentials.credentials
        await auth_service.logout(token)
    except Exception as e:
        logger.error(f"用户登出异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """获取当前登录用户信息。

    Args:
        credentials: HTTP授权凭证

    Returns:
        当前用户信息

    Raises:
        HTTPException: 获取失败
    """
    try:
        token = credentials.credentials
        user = await auth_service.verify_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌或用户不存在",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            role=user.role,
            department=user.department,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            avatar_url=user.avatar_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.post("/send-verification-email", status_code=status.HTTP_200_OK)
async def send_verification_email(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """发送邮箱验证邮件。

    Args:
        request: HTTP请求对象
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 发送失败
    """
    try:
        token = credentials.credentials
        user = await auth_service.verify_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 发送验证邮件
        await auth_service.send_verification_email(
            user_id=user.id,
            ip_address=client_ip
        )

        return {"message": "验证邮件已发送,请查收邮箱"}

    except ValueError as e:
        logger.warning(f"发送验证邮件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"发送验证邮件异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证邮件失败"
        )


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(verify_data: VerifyEmailRequest) -> dict:
    """验证邮箱。

    Args:
        verify_data: 验证数据

    Returns:
        成功消息

    Raises:
        HTTPException: 验证失败
    """
    try:
        await auth_service.verify_email(
            email=verify_data.email,
            code=verify_data.code
        )

        return {"message": "邮箱验证成功"}

    except ValueError as e:
        logger.warning(f"邮箱验证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"邮箱验证异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮箱验证失败"
        )


@router.post("/send-password-reset-email", status_code=status.HTTP_200_OK)
async def send_password_reset_email(
    request: Request,
    reset_data: SendPasswordResetEmailRequest
) -> dict:
    """发送密码重置邮件。

    Args:
        request: HTTP请求对象
        reset_data: 重置数据

    Returns:
        成功消息

    Raises:
        HTTPException: 发送失败
    """
    try:
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 发送密码重置邮件
        await auth_service.send_password_reset_email(
            email=reset_data.email,
            ip_address=client_ip
        )

        return {"message": "如果该邮箱已注册,密码重置邮件将发送到您的邮箱"}

    except ValueError as e:
        logger.warning(f"发送密码重置邮件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"发送密码重置邮件异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送密码重置邮件失败"
        )


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(reset_data: ResetPasswordRequest) -> dict:
    """重置密码。

    Args:
        reset_data: 重置数据

    Returns:
        成功消息

    Raises:
        HTTPException: 重置失败
    """
    try:
        await auth_service.reset_password(
            email=reset_data.email,
            code=reset_data.code,
            new_password=reset_data.new_password
        )

        return {"message": "密码重置成功,请使用新密码登录"}

    except ValueError as e:
        logger.warning(f"密码重置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"密码重置异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置失败"
        )

