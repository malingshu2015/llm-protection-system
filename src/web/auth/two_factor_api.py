"""双因素认证(2FA) API路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.models.two_factor import (
    Disable2FARequest,
    Enable2FARequest,
    Setup2FAResponse,
    TwoFactorStatus,
    Verify2FARequest,
)
from src.auth.services.auth_service import auth_service
from src.auth.services.two_factor_service import two_factor_service
from src.auth.utils.password import PasswordHasher
from src.logger import logger

router = APIRouter(prefix="/api/v1/2fa", tags=["双因素认证"])
security = HTTPBearer()


@router.post("/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Setup2FAResponse:
    """设置2FA(生成密钥和QR码)。

    Args:
        credentials: HTTP授权凭证

    Returns:
        设置响应(包含密钥、QR码、备用码)

    Raises:
        HTTPException: 设置失败
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

        # 设置2FA
        response = await two_factor_service.setup_2fa(
            user_id=user.id,
            username=user.username
        )

        return response

    except ValueError as e:
        logger.warning(f"设置2FA失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"设置2FA异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置2FA失败"
        )


@router.post("/enable", status_code=status.HTTP_200_OK)
async def enable_2fa(
    request: Enable2FARequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """启用2FA(需要验证一次TOTP码)。

    Args:
        request: 启用请求(包含验证码)
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 启用失败
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

        # 启用2FA
        await two_factor_service.enable_2fa(
            user_id=user.id,
            code=request.code
        )

        return {"message": "2FA已成功启用"}

    except ValueError as e:
        logger.warning(f"启用2FA失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"启用2FA异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="启用2FA失败"
        )


@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_2fa(
    request: Verify2FARequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """验证2FA码。

    Args:
        request: 验证请求
        credentials: HTTP授权凭证

    Returns:
        验证结果

    Raises:
        HTTPException: 验证失败
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

        # 验证2FA码
        is_valid = await two_factor_service.verify_2fa(
            user_id=user.id,
            code=request.code
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码无效或已过期"
            )

        return {"message": "验证成功", "valid": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证2FA异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证2FA失败"
        )


@router.post("/disable", status_code=status.HTTP_200_OK)
async def disable_2fa(
    request: Disable2FARequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """禁用2FA。

    Args:
        request: 禁用请求(需要密码验证)
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 禁用失败
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

        # 验证密码
        if not PasswordHasher.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码错误"
            )

        # 如果提供了2FA码,也需要验证
        if request.code:
            is_valid = await two_factor_service.verify_2fa(
                user_id=user.id,
                code=request.code
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="验证码无效"
                )

        # 禁用2FA
        await two_factor_service.disable_2fa(user_id=user.id)

        return {"message": "2FA已禁用"}

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"禁用2FA失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"禁用2FA异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="禁用2FA失败"
        )


@router.post("/regenerate-backup-codes", status_code=status.HTTP_200_OK)
async def regenerate_backup_codes(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """重新生成备用码。

    Args:
        credentials: HTTP授权凭证

    Returns:
        新的备用码列表

    Raises:
        HTTPException: 重新生成失败
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

        # 重新生成备用码
        backup_codes = await two_factor_service.regenerate_backup_codes(user_id=user.id)

        return {
            "message": "备用码已重新生成",
            "backup_codes": backup_codes
        }

    except ValueError as e:
        logger.warning(f"重新生成备用码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"重新生成备用码异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新生成备用码失败"
        )


@router.get("/status", response_model=TwoFactorStatus)
async def get_2fa_status(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TwoFactorStatus:
    """获取2FA状态。

    Args:
        credentials: HTTP授权凭证

    Returns:
        2FA状态

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

        # 获取状态
        status_dict = await two_factor_service.get_2fa_status(user_id=user.id)

        return TwoFactorStatus(**status_dict)

    except Exception as e:
        logger.error(f"获取2FA状态异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取2FA状态失败"
        )
