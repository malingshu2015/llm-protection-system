"""双因素认证(2FA)服务。"""

import json
import pyotp
import qrcode
import io
import base64
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.auth.models.two_factor import TwoFactorAuth, Setup2FAResponse
from src.logger import logger


class TwoFactorService:
    """双因素认证服务类。"""

    def __init__(self, storage_dir: str = "data/two_factor"):
        """初始化2FA服务。

        Args:
            storage_dir: 2FA数据存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, TwoFactorAuth] = {}
        self._load_all()

    def _get_storage_path(self, user_id: str) -> Path:
        """获取用户2FA存储路径。

        Args:
            user_id: 用户ID

        Returns:
            存储路径
        """
        return self.storage_dir / f"{user_id}.json"

    def _load_all(self) -> None:
        """从磁盘加载所有2FA配置。"""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        tfa = TwoFactorAuth(**data)
                        self._cache[tfa.user_id] = tfa
                except Exception as e:
                    logger.error(f"加载2FA配置失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"加载2FA配置失败: {str(e)}")

    def _save(self, tfa: TwoFactorAuth) -> None:
        """保存2FA配置到磁盘。

        Args:
            tfa: 2FA配置对象
        """
        try:
            self._cache[tfa.user_id] = tfa
            file_path = self._get_storage_path(tfa.user_id)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(tfa.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            logger.error(f"保存2FA配置失败: {str(e)}")
            raise

    def _generate_backup_codes(self, count: int = 8) -> list[str]:
        """生成备用恢复码。

        Args:
            count: 生成数量

        Returns:
            备用码列表
        """
        codes = []
        for _ in range(count):
            # 生成8位数字备用码
            code = "".join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(code)
        return codes

    def _generate_qr_code(self, secret: str, username: str, issuer: str = "LLM防护系统") -> str:
        """生成TOTP的QR码。

        Args:
            secret: TOTP密钥
            username: 用户名
            issuer: 发行者名称

        Returns:
            Base64编码的QR码图片
        """
        # 创建TOTP URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name=issuer)

        # 生成QR码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        # 转换为图片
        img = qr.make_image(fill_color="black", back_color="white")

        # 转换为Base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()

        return f"data:image/png;base64,{img_base64}"

    async def setup_2fa(self, user_id: str, username: str) -> Setup2FAResponse:
        """为用户设置2FA。

        Args:
            user_id: 用户ID
            username: 用户名

        Returns:
            设置2FA响应

        Raises:
            ValueError: 2FA已启用
        """
        # 检查是否已启用
        existing = self._cache.get(user_id)
        if existing and existing.is_enabled:
            raise ValueError("2FA已启用，请先禁用后再重新设置")

        # 生成新的TOTP密钥
        secret = pyotp.random_base32()

        # 生成备用码
        backup_codes = self._generate_backup_codes()

        # 创建2FA配置(未启用状态)
        tfa = TwoFactorAuth(
            user_id=user_id,
            secret=secret,
            backup_codes=backup_codes,
            is_enabled=False
        )

        # 保存
        self._save(tfa)

        # 生成QR码
        qr_code_url = self._generate_qr_code(secret, username)

        logger.info(f"用户 {user_id} 开始设置2FA")

        return Setup2FAResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes,
            manual_entry_key=secret
        )

    async def enable_2fa(self, user_id: str, code: str) -> bool:
        """启用2FA(需要验证一次TOTP码)。

        Args:
            user_id: 用户ID
            code: TOTP验证码

        Returns:
            是否启用成功

        Raises:
            ValueError: 验证失败或未设置
        """
        tfa = self._cache.get(user_id)
        if not tfa:
            raise ValueError("请先设置2FA")

        if tfa.is_enabled:
            raise ValueError("2FA已启用")

        # 验证TOTP码
        totp = pyotp.TOTP(tfa.secret)
        if not totp.verify(code, valid_window=1):
            raise ValueError("验证码无效")

        # 启用2FA
        tfa.is_enabled = True
        tfa.enabled_at = datetime.now(timezone.utc)
        tfa.last_used = datetime.now(timezone.utc)

        # 保存
        self._save(tfa)

        logger.info(f"用户 {user_id} 启用了2FA")
        return True

    async def verify_2fa(self, user_id: str, code: str) -> bool:
        """验证2FA码。

        Args:
            user_id: 用户ID
            code: TOTP验证码或备用码

        Returns:
            是否验证成功
        """
        tfa = self._cache.get(user_id)
        if not tfa or not tfa.is_enabled:
            return False

        # 先尝试验证TOTP码
        totp = pyotp.TOTP(tfa.secret)
        if totp.verify(code, valid_window=1):
            tfa.last_used = datetime.now(timezone.utc)
            self._save(tfa)
            return True

        # 再尝试验证备用码
        if code in tfa.backup_codes:
            # 使用备用码后立即删除
            tfa.backup_codes.remove(code)
            tfa.last_used = datetime.now(timezone.utc)
            self._save(tfa)
            logger.warning(f"用户 {user_id} 使用了备用码，剩余 {len(tfa.backup_codes)} 个")
            return True

        return False

    async def disable_2fa(self, user_id: str) -> bool:
        """禁用2FA。

        Args:
            user_id: 用户ID

        Returns:
            是否禁用成功

        Raises:
            ValueError: 未启用2FA
        """
        tfa = self._cache.get(user_id)
        if not tfa or not tfa.is_enabled:
            raise ValueError("2FA未启用")

        # 删除2FA配置
        file_path = self._get_storage_path(user_id)
        if file_path.exists():
            file_path.unlink()

        # 从缓存中删除
        del self._cache[user_id]

        logger.info(f"用户 {user_id} 禁用了2FA")
        return True

    async def regenerate_backup_codes(self, user_id: str) -> list[str]:
        """重新生成备用码。

        Args:
            user_id: 用户ID

        Returns:
            新的备用码列表

        Raises:
            ValueError: 未启用2FA
        """
        tfa = self._cache.get(user_id)
        if not tfa or not tfa.is_enabled:
            raise ValueError("2FA未启用")

        # 生成新的备用码
        backup_codes = self._generate_backup_codes()
        tfa.backup_codes = backup_codes

        # 保存
        self._save(tfa)

        logger.info(f"用户 {user_id} 重新生成了备用码")
        return backup_codes

    async def get_2fa_status(self, user_id: str) -> dict:
        """获取用户2FA状态。

        Args:
            user_id: 用户ID

        Returns:
            2FA状态信息
        """
        tfa = self._cache.get(user_id)

        if not tfa:
            return {
                "is_enabled": False,
                "enabled_at": None,
                "backup_codes_remaining": 0
            }

        return {
            "is_enabled": tfa.is_enabled,
            "enabled_at": tfa.enabled_at,
            "backup_codes_remaining": len(tfa.backup_codes)
        }


# 创建全局2FA服务实例
two_factor_service = TwoFactorService()
