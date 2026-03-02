"""验证码管理服务。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from pydantic import EmailStr

from src.auth.models.verification import (
    VerificationCode,
    VerificationType,
)
from src.auth.services.email_service import email_service
from src.logger import logger


class VerificationService:
    """验证码管理服务类。"""

    def __init__(self, storage_dir: str = "data/verification"):
        """初始化验证码服务。

        Args:
            storage_dir: 验证码存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._codes_cache: Dict[str, VerificationCode] = {}
        self._load_codes()

    def _get_storage_path(self, user_id: str) -> Path:
        """获取用户验证码存储路径。

        Args:
            user_id: 用户ID

        Returns:
            存储路径
        """
        return self.storage_dir / f"{user_id}.json"

    def _load_codes(self) -> None:
        """从磁盘加载所有验证码。"""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for code_data in data.values():
                            code = VerificationCode(**code_data)
                            self._codes_cache[code.id] = code
                except Exception as e:
                    logger.error(f"加载验证码文件失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"加载验证码失败: {str(e)}")

    def _save_code(self, code: VerificationCode) -> None:
        """保存验证码到磁盘。

        Args:
            code: 验证码对象
        """
        try:
            # 更新缓存
            self._codes_cache[code.id] = code

            # 保存到文件
            file_path = self._get_storage_path(code.user_id)
            existing_codes = {}

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_codes = json.load(f)

            existing_codes[code.id] = code.model_dump(mode="json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_codes, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            logger.error(f"保存验证码失败: {str(e)}")
            raise

    async def create_verification_code(
        self,
        user_id: str,
        email: EmailStr,
        verification_type: VerificationType,
        ip_address: Optional[str] = None
    ) -> VerificationCode:
        """创建新的验证码。

        Args:
            user_id: 用户ID
            email: 用户邮箱
            verification_type: 验证类型
            ip_address: 请求IP地址

        Returns:
            验证码对象
        """
        # 创建验证码
        code = VerificationCode.create_verification_code(
            user_id=user_id,
            email=email,
            verification_type=verification_type,
            ip_address=ip_address
        )

        # 保存验证码
        self._save_code(code)

        logger.info(
            f"创建验证码 - 类型: {verification_type}, "
            f"用户: {user_id}, 邮箱: {email}"
        )

        return code

    async def verify_code(
        self,
        email: EmailStr,
        code: str,
        verification_type: VerificationType
    ) -> Optional[VerificationCode]:
        """验证验证码。

        Args:
            email: 邮箱
            code: 验证码
            verification_type: 验证类型

        Returns:
            如果验证成功返回验证码对象,否则返回None
        """
        # 查找匹配的验证码
        for verification_code in self._codes_cache.values():
            if (
                verification_code.email == email
                and verification_code.code == code
                and verification_code.verification_type == verification_type
            ):
                # 检查验证码是否有效
                if not verification_code.is_valid():
                    logger.warning(
                        f"验证码已过期或已使用 - "
                        f"邮箱: {email}, 类型: {verification_type}"
                    )
                    return None

                # 标记为已使用
                verification_code.mark_as_used()
                self._save_code(verification_code)

                logger.info(
                    f"验证码验证成功 - "
                    f"邮箱: {email}, 类型: {verification_type}"
                )

                return verification_code

        logger.warning(
            f"验证码不匹配 - "
            f"邮箱: {email}, 类型: {verification_type}"
        )
        return None

    async def send_verification_email(
        self,
        user_id: str,
        email: EmailStr,
        username: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """发送邮箱验证邮件。

        Args:
            user_id: 用户ID
            email: 邮箱
            username: 用户名
            ip_address: 请求IP地址

        Returns:
            是否发送成功
        """
        try:
            # 创建验证码
            code = await self.create_verification_code(
                user_id=user_id,
                email=email,
                verification_type=VerificationType.EMAIL_VERIFICATION,
                ip_address=ip_address
            )

            # 发送邮件
            success = await email_service.send_verification_email(
                to_email=email,
                username=username,
                verification_code=code.code
            )

            if success:
                logger.info(f"验证邮件已发送到 {email}")
            else:
                logger.error(f"验证邮件发送失败: {email}")

            return success

        except Exception as e:
            logger.error(f"发送验证邮件异常: {str(e)}")
            return False

    async def send_password_reset_email(
        self,
        user_id: str,
        email: EmailStr,
        username: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """发送密码重置邮件。

        Args:
            user_id: 用户ID
            email: 邮箱
            username: 用户名
            ip_address: 请求IP地址

        Returns:
            是否发送成功
        """
        try:
            # 创建验证码
            code = await self.create_verification_code(
                user_id=user_id,
                email=email,
                verification_type=VerificationType.PASSWORD_RESET,
                ip_address=ip_address
            )

            # 发送邮件
            success = await email_service.send_password_reset_email(
                to_email=email,
                username=username,
                reset_code=code.code
            )

            if success:
                logger.info(f"密码重置邮件已发送到 {email}")
            else:
                logger.error(f"密码重置邮件发送失败: {email}")

            return success

        except Exception as e:
            logger.error(f"发送密码重置邮件异常: {str(e)}")
            return False

    def cleanup_expired_codes(self) -> int:
        """清理过期的验证码。

        Returns:
            清理的验证码数量
        """
        count = 0
        try:
            current_time = datetime.now(timezone.utc)

            # 找出过期的验证码
            expired_codes = [
                code for code in self._codes_cache.values()
                if code.expires_at < current_time
            ]

            # 从缓存中删除
            for code in expired_codes:
                del self._codes_cache[code.id]
                count += 1

            # 重新保存文件(按用户分组)
            user_codes: Dict[str, Dict[str, dict]] = {}
            for code in self._codes_cache.values():
                if code.user_id not in user_codes:
                    user_codes[code.user_id] = {}
                user_codes[code.user_id][code.id] = code.model_dump(mode="json")

            # 保存每个用户的验证码
            for user_id, codes in user_codes.items():
                file_path = self._get_storage_path(user_id)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(codes, f, ensure_ascii=False, indent=2, default=str)

            # 删除空文件
            for file_path in self.storage_dir.glob("*.json"):
                if file_path.stat().st_size == 0 or file_path.read_text().strip() == "{}":
                    file_path.unlink()

            if count > 0:
                logger.info(f"清理了 {count} 个过期验证码")

        except Exception as e:
            logger.error(f"清理过期验证码失败: {str(e)}")

        return count


# 创建全局验证码服务实例
verification_service = VerificationService()
