"""WebAuthn/FIDO2认证 API路由。"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.models.webauthn import (
    RegisterChallengeRequest,
    RegisterChallengeResponse,
    RegisterCredentialRequest,
    AuthenticationChallengeRequest,
    AuthenticationChallengeResponse,
    AuthenticationCredentialRequest,
    WebAuthnLoginResponse,
    WebAuthnCredentialResponse,
)
from src.auth.models.audit import AuditActionType, AuditLogLevel
from src.auth.models.user import UserResponse
from src.auth.services.webauthn_service_pro import webauthn_service
from src.auth.services.auth_service import auth_service
from src.auth.services.user_db import user_db
from src.auth.services.audit_service import audit_service
from src.logger import logger

router = APIRouter(prefix="/api/v1/webauthn", tags=["WebAuthn认证"])
security = HTTPBearer()


@router.post("/register/challenge")
async def create_register_challenge(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """创建注册挑战 (使用专业库)。

    Args:
        credentials: HTTP授权凭证

    Returns:
        注册选项 (JSON格式)

    Raises:
        HTTPException: 创建失败
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

        # 创建挑战 (专业库返回JSON格式)
        options_json = await webauthn_service.create_registration_challenge(
            user_id=user.id,
            username=user.username,
            display_name=user.username
        )

        return options_json

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建注册挑战异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建注册挑战失败"
        )


@router.post("/register/verify", status_code=status.HTTP_201_CREATED)
async def verify_and_save_credential(
    request: RegisterCredentialRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """验证并保存凭证 (使用专业库)。

    Args:
        request: 注册凭证请求
        credentials: HTTP授权凭证

    Returns:
        成功消息

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

        # 提取 challenge
        # 优先使用客户端传递的 challenge (更安全,因为服务器端也会验证)
        # 作为备选方案,从 client_data_json 中提取
        import json
        import base64

        if request.challenge:
            challenge = request.challenge
        else:
            # 备选: 从 client_data_json 中提取
            client_data = json.loads(base64.urlsafe_b64decode(request.client_data_json + '=='))
            challenge = client_data.get('challenge')

        # 构建完整的凭证JSON (符合webauthn库的格式)
        credential_json = json.dumps({
            "id": request.credential_id,
            "rawId": request.credential_id,
            "response": {
                "clientDataJSON": request.client_data_json,
                "attestationObject": request.attestation_object,
                "transports": request.transports or []
            },
            "type": "public-key",
            "clientExtensionResults": {}
        })

        # 使用专业库验证并保存
        credential = await webauthn_service.verify_and_save_credential(
            credential_json=credential_json,
            expected_challenge=challenge,
            device_name=request.device_name
        )

        # 记录审计日志
        await audit_service.log_action(
            action_type=AuditActionType.SYSTEM_CONFIG_CHANGE,
            action_description=f"注册WebAuthn凭证: {request.device_name}",
            user_id=user.id,
            username=user.username,
            level=AuditLogLevel.INFO,
            success=True,
            metadata={"credential_id": credential.credential_id[:20], "device_name": request.device_name}
        )

        return {
            "message": "凭证注册成功",
            "credential_id": credential.credential_id
        }

    except ValueError as e:
        logger.warning(f"注册凭证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册凭证异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册凭证失败"
        )


@router.post("/authenticate/challenge")
async def create_authentication_challenge(
    request: AuthenticationChallengeRequest
) -> dict:
    """创建认证挑战 (使用专业库)。

    Args:
        request: 认证挑战请求

    Returns:
        认证选项 (JSON格式)

    Raises:
        HTTPException: 创建失败
    """
    try:
        user_id = None

        # 如果提供了用户名，查找用户ID
        if request.username:
            user = await user_db.get_user_by_username(request.username)
            if user:
                user_id = user.id

        # 创建挑战 (专业库返回JSON格式)
        options_json = await webauthn_service.create_authentication_challenge(
            user_id=user_id
        )

        return options_json

    except Exception as e:
        logger.error(f"创建认证挑战异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建认证挑战失败"
        )


@router.post("/authenticate/verify", response_model=WebAuthnLoginResponse)
async def verify_authentication(
    request: AuthenticationCredentialRequest,
    http_request: Request
) -> WebAuthnLoginResponse:
    """验证认证并登录 (使用专业库)。

    Args:
        request: 认证凭证请求
        http_request: HTTP请求对象

    Returns:
        登录响应

    Raises:
        HTTPException: 验证失败
    """
    try:
        # 提取 challenge
        # 优先使用客户端传递的 challenge (更安全,因为服务器端也会验证)
        # 作为备选方案,从 client_data_json 中提取
        import json
        import base64

        if request.challenge:
            challenge = request.challenge
        else:
            # 备选: 从 client_data_json 中提取
            client_data = json.loads(base64.urlsafe_b64decode(request.client_data_json + '=='))
            challenge = client_data.get('challenge')

        # 构建完整的凭证JSON (符合webauthn库的格式)
        credential_json = json.dumps({
            "id": request.credential_id,
            "rawId": request.credential_id,
            "response": {
                "clientDataJSON": request.client_data_json,
                "authenticatorData": request.authenticator_data,
                "signature": request.signature,
                "userHandle": request.user_handle
            },
            "type": "public-key",
            "clientExtensionResults": {}
        })

        # 使用专业库验证认证
        user_id = await webauthn_service.verify_authentication(
            credential_json=credential_json,
            expected_challenge=challenge
        )

        # 获取用户
        user = await user_db.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")

        # 获取客户端信息
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 使用现有登录方法创建会话
        login_response, session = await auth_service.login_with_user(
            user=user,
            ip_address=client_ip,
            user_agent=user_agent,
            remember_me=True
        )

        # 记录审计日志
        await audit_service.log_action(
            action_type=AuditActionType.USER_LOGIN,
            action_description="通过WebAuthn登录成功",
            user_id=user.id,
            username=user.username,
            ip_address=client_ip,
            level=AuditLogLevel.INFO,
            success=True,
            metadata={"method": "webauthn", "credential_id": request.credential_id[:20]}
        )

        return WebAuthnLoginResponse(
            access_token=login_response.access_token,
            refresh_token=login_response.refresh_token,
            token_type=login_response.token_type,
            expires_in=login_response.expires_in,
            user=login_response.user
        )

    except ValueError as e:
        logger.warning(f"WebAuthn认证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"WebAuthn认证异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="认证失败"
        )


@router.get("/credentials", response_model=list[WebAuthnCredentialResponse])
async def get_credentials(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> list[WebAuthnCredentialResponse]:
    """获取用户的所有WebAuthn凭证。

    Args:
        credentials: HTTP授权凭证

    Returns:
        凭证列表

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

        # 获取凭证列表
        credential_list = await webauthn_service.get_user_credentials(user.id)

        return credential_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取凭证列表异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取凭证列表失败"
        )


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_200_OK)
async def delete_credential(
    credential_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """删除WebAuthn凭证。

    Args:
        credential_id: 凭证ID
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 删除失败
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

        # 删除凭证
        await webauthn_service.delete_credential(user.id, credential_id)

        # 记录审计日志
        await audit_service.log_action(
            action_type=AuditActionType.SYSTEM_CONFIG_CHANGE,
            action_description=f"删除WebAuthn凭证",
            user_id=user.id,
            username=user.username,
            level=AuditLogLevel.INFO,
            success=True,
            metadata={"credential_id": credential_id[:20]}
        )

        return {"message": "凭证已删除"}

    except ValueError as e:
        logger.warning(f"删除凭证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除凭证异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除凭证失败"
        )


@router.patch("/credentials/{credential_id}/name", status_code=status.HTTP_200_OK)
async def update_credential_name(
    credential_id: str,
    device_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """更新WebAuthn凭证名称。

    Args:
        credential_id: 凭证ID
        device_name: 新设备名称
        credentials: HTTP授权凭证

    Returns:
        成功消息

    Raises:
        HTTPException: 更新失败
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

        # 更新名称
        await webauthn_service.update_credential_name(user.id, credential_id, device_name)

        return {"message": "凭证名称已更新"}

    except ValueError as e:
        logger.warning(f"更新凭证名称失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新凭证名称异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新凭证名称失败"
        )
