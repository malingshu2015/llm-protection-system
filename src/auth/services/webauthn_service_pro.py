"""WebAuthn/FIDO2认证服务 - 使用专业库实现完整验证。"""

import json
import base64
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
)
from webauthn.helpers.structs import (
    RegistrationCredential,
    AuthenticationCredential,
    PublicKeyCredentialDescriptor,
    AuthenticatorTransport,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    AttestationConveyancePreference,
)

from src.auth.models.webauthn import (
    WebAuthnCredential,
    RegisterChallengeResponse,
    AuthenticationChallengeResponse,
    WebAuthnCredentialResponse,
)
from src.logger import logger


class WebAuthnService:
    """WebAuthn认证服务类 - 使用专业库。"""

    def __init__(
        self,
        rp_id: str = "localhost",
        rp_name: str = "LLM防护系统",
        rp_origin: str = "http://localhost:8000",
        storage_dir: str = "data/webauthn"
    ):
        """初始化WebAuthn服务。

        Args:
            rp_id: 依赖方ID (域名)
            rp_name: 依赖方名称
            rp_origin: 依赖方源 (协议+域名+端口)
            storage_dir: 存储目录
        """
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.rp_origin = rp_origin
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 挑战缓存 {challenge: {user_id, type, created_at, options}}
        self._challenges: Dict[str, Dict[str, Any]] = {}

        # 凭证缓存 {user_id: [credentials]}
        self._credentials: Dict[str, List[WebAuthnCredential]] = {}

        self._load_all()

    def _get_credentials_path(self, user_id: str) -> Path:
        """获取用户凭证存储路径。"""
        return self.storage_dir / f"{user_id}.json"

    def _load_all(self) -> None:
        """从磁盘加载所有凭证。"""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        user_id = file_path.stem
                        self._credentials[user_id] = [
                            WebAuthnCredential(**cred) for cred in data
                        ]
                except Exception as e:
                    logger.error(f"加载WebAuthn凭证失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"加载WebAuthn凭证失败: {str(e)}")

    def _save_credentials(self, user_id: str) -> None:
        """保存用户凭证到磁盘。"""
        try:
            file_path = self._get_credentials_path(user_id)
            credentials = self._credentials.get(user_id, [])

            data = [cred.model_dump(mode="json") for cred in credentials]

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存WebAuthn凭证失败: {str(e)}")
            raise

    def _cleanup_expired_challenges(self) -> None:
        """清理过期的挑战。"""
        now = datetime.now(timezone.utc)
        expired_challenges = [
            challenge for challenge, data in self._challenges.items()
            if now - data['created_at'] > timedelta(minutes=5)
        ]
        for challenge in expired_challenges:
            del self._challenges[challenge]

    async def create_registration_challenge(
        self,
        user_id: str,
        username: str,
        display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建注册挑战 - 使用专业库。

        Args:
            user_id: 用户ID
            username: 用户名
            display_name: 显示名称

        Returns:
            注册选项 (JSON格式)
        """
        # 清理过期挑战
        self._cleanup_expired_challenges()

        # 获取已存在的凭证ID列表 (排除重复注册)
        existing_credentials = []
        if user_id in self._credentials:
            existing_credentials = [
                PublicKeyCredentialDescriptor(
                    id=base64url_to_bytes(cred.credential_id)
                )
                for cred in self._credentials[user_id]
            ]

        # 生成注册选项
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user_id.encode('utf-8'),
            user_name=username,
            user_display_name=display_name or username,
            exclude_credentials=existing_credentials,
            authenticator_selection={
                "authenticator_attachment": AuthenticatorAttachment.CROSS_PLATFORM,
                "user_verification": UserVerificationRequirement.PREFERRED,
            },
            attestation=AttestationConveyancePreference.NONE,
            timeout=60000,
        )

        # 转换为JSON
        options_json = options_to_json(options)

        # 保存挑战用于后续验证
        challenge_b64 = options_json['challenge']
        self._challenges[challenge_b64] = {
            'user_id': user_id,
            'username': username,
            'type': 'registration',
            'created_at': datetime.now(timezone.utc),
            'options': options_json
        }

        logger.info(f"创建注册挑战 (专业库): user_id={user_id}, username={username}")

        return options_json

    async def verify_and_save_credential(
        self,
        credential_json: str,
        expected_challenge: str,
        device_name: Optional[str] = None
    ) -> WebAuthnCredential:
        """验证并保存凭证 - 使用专业库。

        Args:
            credential_json: 凭证JSON字符串
            expected_challenge: 预期的挑战
            device_name: 设备名称

        Returns:
            保存的凭证

        Raises:
            ValueError: 验证失败
        """
        # 验证挑战是否存在
        challenge_data = self._challenges.get(expected_challenge)
        if not challenge_data:
            raise ValueError("无效或过期的挑战")

        if challenge_data['type'] != 'registration':
            raise ValueError("挑战类型不匹配")

        user_id = challenge_data['user_id']

        try:
            # 解析凭证
            credential_dict = json.loads(credential_json)
            credential = RegistrationCredential.parse_obj(credential_dict)

            # 验证注册响应
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_origin=self.rp_origin,
                expected_rp_id=self.rp_id,
            )

            # 提取验证后的数据
            credential_id = bytes_to_base64url(verification.credential_id)
            public_key = bytes_to_base64url(verification.credential_public_key)
            sign_count = verification.sign_count
            aaguid = verification.aaguid.hex() if verification.aaguid else None

            # 获取传输方式
            transports = []
            if hasattr(credential.response, 'transports') and credential.response.transports:
                transports = [t.value for t in credential.response.transports]

            # 创建凭证
            webauthn_cred = WebAuthnCredential(
                user_id=user_id,
                credential_id=credential_id,
                public_key=public_key,
                sign_count=sign_count,
                aaguid=aaguid,
                transports=transports,
                device_name=device_name or "未命名设备",
                is_backup_eligible=verification.backup_eligible,
                is_backed_up=verification.backup_state,
            )

            # 保存凭证
            if user_id not in self._credentials:
                self._credentials[user_id] = []

            self._credentials[user_id].append(webauthn_cred)
            self._save_credentials(user_id)

            # 删除已使用的挑战
            del self._challenges[expected_challenge]

            logger.info(f"保存WebAuthn凭证 (已验证): user_id={user_id}, credential_id={credential_id[:20]}...")

            return webauthn_cred

        except Exception as e:
            logger.error(f"凭证验证失败: {str(e)}")
            raise ValueError(f"凭证验证失败: {str(e)}")

    async def create_authentication_challenge(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建认证挑战 - 使用专业库。

        Args:
            user_id: 用户ID (可选)

        Returns:
            认证选项 (JSON格式)
        """
        # 清理过期挑战
        self._cleanup_expired_challenges()

        # 获取允许的凭证列表
        allow_credentials = []
        if user_id and user_id in self._credentials:
            credentials = self._credentials[user_id]
            allow_credentials = [
                PublicKeyCredentialDescriptor(
                    id=base64url_to_bytes(cred.credential_id),
                    transports=[AuthenticatorTransport(t) for t in cred.transports] if cred.transports else []
                )
                for cred in credentials
            ]

        # 生成认证选项
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
            timeout=60000,
        )

        # 转换为JSON
        options_json = options_to_json(options)

        # 保存挑战用于后续验证
        challenge_b64 = options_json['challenge']
        self._challenges[challenge_b64] = {
            'user_id': user_id,
            'type': 'authentication',
            'created_at': datetime.now(timezone.utc),
            'options': options_json
        }

        logger.info(f"创建认证挑战 (专业库): user_id={user_id}")

        return options_json

    async def verify_authentication(
        self,
        credential_json: str,
        expected_challenge: str
    ) -> str:
        """验证认证 - 使用专业库。

        Args:
            credential_json: 凭证JSON字符串
            expected_challenge: 预期的挑战

        Returns:
            用户ID

        Raises:
            ValueError: 验证失败
        """
        # 验证挑战是否存在
        challenge_data = self._challenges.get(expected_challenge)
        if not challenge_data:
            raise ValueError("无效或过期的挑战")

        if challenge_data['type'] != 'authentication':
            raise ValueError("挑战类型不匹配")

        try:
            # 解析凭证
            credential_dict = json.loads(credential_json)
            credential = AuthenticationCredential.parse_obj(credential_dict)

            # 查找对应的凭证记录
            credential_id_b64 = bytes_to_base64url(credential.raw_id)

            stored_credential = None
            user_id = None

            for uid, credentials in self._credentials.items():
                for cred in credentials:
                    if cred.credential_id == credential_id_b64:
                        stored_credential = cred
                        user_id = uid
                        break
                if stored_credential:
                    break

            if not stored_credential:
                raise ValueError("凭证未找到")

            # 验证认证响应
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_origin=self.rp_origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64url_to_bytes(stored_credential.public_key),
                credential_current_sign_count=stored_credential.sign_count,
            )

            # 更新签名计数器
            stored_credential.sign_count = verification.new_sign_count
            stored_credential.last_used = datetime.now(timezone.utc)
            self._save_credentials(user_id)

            # 删除已使用的挑战
            del self._challenges[expected_challenge]

            logger.info(f"WebAuthn认证成功 (已验证): user_id={user_id}, credential_id={credential_id_b64[:20]}...")

            return user_id

        except Exception as e:
            logger.error(f"认证验证失败: {str(e)}")
            raise ValueError(f"认证验证失败: {str(e)}")

    async def get_user_credentials(
        self,
        user_id: str
    ) -> List[WebAuthnCredentialResponse]:
        """获取用户的所有凭证。

        Args:
            user_id: 用户ID

        Returns:
            凭证列表
        """
        credentials = self._credentials.get(user_id, [])

        return [
            WebAuthnCredentialResponse(
                id=cred.id,
                credential_id=cred.credential_id,
                device_name=cred.device_name,
                transports=cred.transports,
                created_at=cred.created_at,
                last_used=cred.last_used,
                sign_count=cred.sign_count
            )
            for cred in credentials
        ]

    async def delete_credential(
        self,
        user_id: str,
        credential_id: str
    ) -> bool:
        """删除凭证。

        Args:
            user_id: 用户ID
            credential_id: 凭证ID

        Returns:
            是否删除成功

        Raises:
            ValueError: 凭证未找到
        """
        credentials = self._credentials.get(user_id, [])

        # 查找并删除凭证
        for i, cred in enumerate(credentials):
            if cred.credential_id == credential_id:
                credentials.pop(i)
                self._save_credentials(user_id)
                logger.info(f"删除WebAuthn凭证: user_id={user_id}, credential_id={credential_id[:20]}...")
                return True

        raise ValueError("凭证未找到")

    async def update_credential_name(
        self,
        user_id: str,
        credential_id: str,
        device_name: str
    ) -> bool:
        """更新凭证名称。

        Args:
            user_id: 用户ID
            credential_id: 凭证ID
            device_name: 新设备名称

        Returns:
            是否更新成功

        Raises:
            ValueError: 凭证未找到
        """
        credentials = self._credentials.get(user_id, [])

        for cred in credentials:
            if cred.credential_id == credential_id:
                cred.device_name = device_name
                self._save_credentials(user_id)
                logger.info(f"更新WebAuthn凭证名称: user_id={user_id}, name={device_name}")
                return True

        raise ValueError("凭证未找到")


# 创建全局WebAuthn服务实例 (从环境变量读取配置)
webauthn_service = WebAuthnService(
    rp_id=os.getenv("WEBAUTHN_RP_ID", "localhost"),
    rp_name=os.getenv("WEBAUTHN_RP_NAME", "LLM防护系统"),
    rp_origin=os.getenv("WEBAUTHN_RP_ORIGIN", "http://localhost:8000"),
    storage_dir=os.getenv("WEBAUTHN_STORAGE_DIR", "data/webauthn")
)
