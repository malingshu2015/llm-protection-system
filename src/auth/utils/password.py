"""密码加密工具类。"""

import bcrypt


class PasswordHasher:
    """密码加密和验证工具类。"""

    @staticmethod
    def hash_password(password: str) -> str:
        """使用bcrypt加密密码。

        Args:
            password: 原始密码

        Returns:
            加密后的密码哈希
        """
        # 生成salt并加密密码
        salt = bcrypt.gensalt(rounds=12)  # 使用12轮加密,安全性高
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
        return password_hash.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码是否正确。

        Args:
            password: 待验证的原始密码
            password_hash: 存储的密码哈希

        Returns:
            密码是否匹配
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8")
            )
        except Exception:
            return False

    @staticmethod
    def needs_rehash(password_hash: str, rounds: int = 12) -> bool:
        """检查密码哈希是否需要重新加密(例如安全策略升级)。

        Args:
            password_hash: 密码哈希
            rounds: 期望的加密轮数

        Returns:
            是否需要重新加密
        """
        try:
            # 提取当前哈希使用的轮数
            current_rounds = int(password_hash.split("$")[2])
            return current_rounds < rounds
        except Exception:
            # 如果无法解析,建议重新加密
            return True
