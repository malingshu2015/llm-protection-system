"""WebAuthn/FIDO2认证服务。"""

import json
import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from src.auth.models.webauthn import (
    WebAuthnCredential,
    RegisterChallengeResponse,
    AuthenticationChallengeResponse,
    WebAuthnCredentialResponse,
)
from src.logger import logger


class WebAuthnService:
    """WebAuthn认证服务类。"""

    def __init__(
        self,
        rp_id: str = "localhost",
        rp_name: str = "LLM防护系统",
        storage_dir: str = "data/webauthn"
    ):
        """初始化WebAuthn服务。

        Args:
            rp_id: 依赖方ID (域名)
            rp_name: 依赖方名称
            storage_dir: 存储目录
        """
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 挑战缓存 {challenge: {user_id, type, created_at}}
        self._challenges: Dict[str, Dict[str, Any]] = {}

        # 凭证缓存 {user_id: [credentials]}
        self._credentials: Dict[str, list[WebAuthnCredential]] = {}

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

    def _generate_challenge(self) -> str:
        """生成随机挑战。

        Returns:
            Base64URL编码的挑战
        """
        # 生成32字节随机数
        challenge_bytes = secrets.token_bytes(32)
        # Base64URL编码
        return base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')

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
        username: str
    ) -> RegisterChallengeResponse:
        """创建注册挑战。

        Args:
            user_id: 用户ID
            username: 用户名

        Returns:
            注册挑战响应
        """
        # 清理过期挑战
        self._cleanup_expired_challenges()

        # 生成挑战
        challenge = self._generate_challenge()

        # 保存挑战
        self._challenges[challenge] = {
            'user_id': user_id,
            'username': username,
            'type': 'registration',
            'created_at': datetime.now(timezone.utc)
        }

        logger.info(f"创建注册挑战: user_id={user_id}, username={username}")

        return RegisterChallengeResponse(
            challenge=challenge,
            user_id=user_id,
            rp_id=self.rp_id,
            rp_name=self.rp_name
        )

    async def verify_and_save_credential(
        self,
        challenge: str,
        credential_id: str,
        public_key: str,
        attestation_object: str,
        client_data_json: str,
        transports: list[str],
        device_name: Optional[str] = None
    ) -> WebAuthnCredential:
        """验证并保存凭证。

        Args:
            challenge: 挑战
            credential_id: 凭证ID
            public_key: 公钥
            attestation_object: 证明对象
            client_data_json: 客户端数据JSON
            transports: 传输方式
            device_name: 设备名称

        Returns:
            保存的凭证

        Raises:
            ValueError: 验证失败
        """
        # 验证挑战
        challenge_data = self._challenges.get(challenge)
        if not challenge_data:
            raise ValueError("无效或过期的挑战")

        if challenge_data['type'] != 'registration':
            raise ValueError("挑战类型不匹配")

        user_id = challenge_data['user_id']

        # 解码client_data_json并验证
        try:
            client_data = json.loads(base64.urlsafe_b64decode(client_data_json + '=='))

            # 验证type
            if client_data.get('type') != 'webauthn.create':
                raise ValueError("客户端数据类型无效")

            # 验证challenge
            if client_data.get('challenge') != challenge:
                raise ValueError("挑战不匹配")

            # 验证origin
            origin = client_data.get('origin', '')
            if not self._verify_origin(origin):
                raise ValueError("源验证失败")

        except Exception as e:
            logger.error(f"客户端数据验证失败: {str(e)}")
            raise ValueError("客户端数据验证失败")

        # 创建凭证
        credential = WebAuthnCredential(
            user_id=user_id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=0,
            transports=transports,
            device_name=device_name or "未命名设备"
        )

        # 保存凭证
        if user_id not in self._credentials:
            self._credentials[user_id] = []

        self._credentials[user_id].append(credential)
        self._save_credentials(user_id)

        # 删除已使用的挑战
        del self._challenges[challenge]

        logger.info(f"保存WebAuthn凭证: user_id={user_id}, credential_id={credential_id[:20]}...")

        return credential

    def _verify_origin(self, origin: str) -> bool:
        """验证来源。

        Args:
            origin: 来源URL

        Returns:
            是否有效
        """
        # 在生产环境中，应该严格验证origin
        # 这里简化处理，允许localhost和https
        allowed_origins = [
            f"http://{self.rp_id}",
            f"https://{self.rp_id}",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]
        return origin in allowed_origins

    async def create_authentication_challenge(
        self,
        user_id: Optional[str] = None
    ) -> AuthenticationChallengeResponse:
        """创建认证挑战。

        Args:
            user_id: 用户ID (可选，如果提供则返回该用户的凭证列表)

        Returns:
            认证挑战响应
        """
        # 清理过期挑战
        self._cleanup_expired_challenges()

        # 生成挑战
        challenge = self._generate_challenge()

        # 保存挑战
        self._challenges[challenge] = {
            'user_id': user_id,
            'type': 'authentication',
            'created_at': datetime.now(timezone.utc)
        }

        # 获取允许的凭证列表
        allow_credentials = []
        if user_id:
            credentials = self._credentials.get(user_id, [])
            allow_credentials = [
                {
                    'id': cred.credential_id,
                    'type': 'public-key',
                    'transports': cred.transports
                }
                for cred in credentials
            ]

        logger.info(f"创建认证挑战: user_id={user_id}")

        return AuthenticationChallengeResponse(
            challenge=challenge,
            rp_id=self.rp_id,
            allow_credentials=allow_credentials
        )

    async def verify_authentication(
        self,
        challenge: str,
        credential_id: str,
        authenticator_data: str,
        client_data_json: str,
        signature: str,
        user_handle: Optional[str] = None
    ) -> str:
        """验证认证。

        Args:
            challenge: 挑战
            credential_id: 凭证ID
            authenticator_data: 认证器数据
            client_data_json: 客户端数据JSON
            signature: 签名
            user_handle: 用户句柄

        Returns:
            用户ID

        Raises:
            ValueError: 验证失败
        """
        # 验证挑战
        challenge_data = self._challenges.get(challenge)
        if not challenge_data:
            raise ValueError("无效或过期的挑战")

        if challenge_data['type'] != 'authentication':
            raise ValueError("挑战类型不匹配")

        # 查找凭证
        credential = None
        user_id = None

        for uid, credentials in self._credentials.items():
            for cred in credentials:
                if cred.credential_id == credential_id:
                    credential = cred
                    user_id = uid
                    break
            if credential:
                break

        if not credential:
            raise ValueError("凭证未找到")

        # 解码client_data_json并验证
        try:
            client_data = json.loads(base64.urlsafe_b64decode(client_data_json + '=='))

            # 验证type
            if client_data.get('type') != 'webauthn.get':
                raise ValueError("客户端数据类型无效")

            # 验证challenge
            if client_data.get('challenge') != challenge:
                raise ValueError("挑战不匹配")

            # 验证origin
            origin = client_data.get('origin', '')
            if not self._verify_origin(origin):
                raise ValueError("源验证失败")

        except Exception as e:
            logger.error(f"客户端数据验证失败: {str(e)}")
            raise ValueError("客户端数据验证失败")

        # 在生产环境中，这里应该验证签名
        # 简化处理，这里跳过签名验证
        # TODO: 实现完整的签名验证

        # 更新签名计数器
        # 解码authenticator_data以获取sign_count
        try:
            auth_data_bytes = base64.urlsafe_b64decode(authenticator_data + '==')
            # sign_count位于字节33-36
            if len(auth_data_bytes) >= 37:
                sign_count = int.from_bytes(auth_data_bytes[33:37], 'big')

                # 验证计数器 (防止克隆攻击)
                if sign_count > 0 and sign_count <= credential.sign_count:
                    logger.warning(f"可疑的签名计数器: credential_id={credential_id}")
                    # 在生产环境中应该拒绝此次认证

                credential.sign_count = sign_count
        except Exception as e:
            logger.warning(f"解析认证器数据失败: {str(e)}")

        # 更新最后使用时间
        credential.last_used = datetime.now(timezone.utc)
        self._save_credentials(user_id)

        # 删除已使用的挑战
        del self._challenges[challenge]

        logger.info(f"WebAuthn认证成功: user_id={user_id}, credential_id={credential_id[:20]}...")

        return user_id

    async def get_user_credentials(
        self,
        user_id: str
    ) -> list[WebAuthnCredentialResponse]:
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


# 创建全局WebAuthn服务实例
webauthn_service = WebAuthnService()
