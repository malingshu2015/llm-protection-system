"""用户认证服务。"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from pydantic import EmailStr

from src.auth.models.audit import AuditActionType, AuditLogLevel
from src.auth.models.session import LoginResponse, UserSession
from src.auth.models.user import User, UserCreate, UserResponse, UserRole
from src.auth.models.verification import VerificationType
from src.auth.services.audit_service import audit_service
from src.auth.services.user_db import user_db
from src.auth.services.verification_service import verification_service
from src.auth.utils.jwt import JWTManager
from src.auth.utils.password import PasswordHasher
from src.logger import logger


class AuthService:
    """用户认证服务类。"""

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    async def register_user(
        self,
        user_data: UserCreate,
        ip_address: Optional[str] = None
    ) -> UserResponse:
        """注册新用户。

        Args:
            user_data: 用户创建数据
            ip_address: 请求IP地址

        Returns:
            创建的用户响应

        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = await user_db.get_user_by_username(user_data.username)
        if existing_user:
            # 记录失败的注册尝试
            await audit_service.log_action(
                action_type=AuditActionType.USER_REGISTER,
                action_description=f"用户注册失败: 用户名已存在 - {user_data.username}",
                username=user_data.username,
                ip_address=ip_address,
                level=AuditLogLevel.WARNING,
                success=False,
                error_message="用户名已存在"
            )
            raise ValueError("用户名已存在")

        # 检查邮箱是否已存在
        existing_email = await user_db.get_user_by_email(user_data.email)
        if existing_email:
            await audit_service.log_action(
                action_type=AuditActionType.USER_REGISTER,
                action_description=f"用户注册失败: 邮箱已被注册 - {user_data.email}",
                username=user_data.username,
                ip_address=ip_address,
                level=AuditLogLevel.WARNING,
                success=False,
                error_message="邮箱已被注册"
            )
            raise ValueError("邮箱已被注册")

        # 加密密码
        password_hash = PasswordHasher.hash_password(user_data.password)

        # 创建用户对象
        user = User(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            password_hash=password_hash,
            role=user_data.role,
            department=user_data.department,
            salt="",  # bcrypt自带salt,这里保留字段用于未来扩展
        )

        # 保存到数据库
        created_user = await user_db.create_user(user)

        logger.info(f"用户注册成功: {created_user.username}")

        # 记录成功的注册
        await audit_service.log_action(
            action_type=AuditActionType.USER_REGISTER,
            action_description=f"用户注册成功: {created_user.username}",
            user_id=created_user.id,
            username=created_user.username,
            resource_type="user",
            resource_id=created_user.id,
            ip_address=ip_address,
            level=AuditLogLevel.INFO,
            success=True,
            metadata={
                "email": created_user.email,
                "role": created_user.role.value,
                "department": created_user.department
            }
        )

        # 返回用户响应(不包含敏感信息)
        return UserResponse(
            id=created_user.id,
            username=created_user.username,
            email=created_user.email,
            phone=created_user.phone,
            role=created_user.role,
            department=created_user.department,
            is_active=created_user.is_active,
            is_verified=created_user.is_verified,
            created_at=created_user.created_at,
            updated_at=created_user.updated_at,
            last_login=created_user.last_login,
            avatar_url=created_user.avatar_url
        )

    async def login(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False
    ) -> Tuple[LoginResponse, UserSession]:
        """用户登录。

        Args:
            username: 用户名
            password: 密码
            ip_address: IP地址
            user_agent: 用户代理
            remember_me: 是否记住登录

        Returns:
            登录响应和会话对象

        Raises:
            ValueError: 登录失败
        """
        # 获取用户
        user = await user_db.get_user_by_username(username)
        if not user:
            raise ValueError("用户名或密码错误")

        # 检查账号是否被锁定
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining_time = (user.locked_until - datetime.utcnow()).total_seconds() / 60
            raise ValueError(f"账号已被锁定,请在 {int(remaining_time)} 分钟后重试")

        # 检查账号是否激活
        if not user.is_active:
            raise ValueError("账号已被禁用")

        # 验证密码
        if not PasswordHasher.verify_password(password, user.password_hash):
            # 增加登录失败次数
            login_attempts = user.login_attempts + 1
            updates = {"login_attempts": login_attempts}

            # 如果失败次数达到上限,锁定账号
            if login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                locked_until = datetime.utcnow() + timedelta(
                    minutes=self.LOCKOUT_DURATION_MINUTES
                )
                updates["locked_until"] = locked_until.isoformat()
                logger.warning(f"用户 {username} 登录失败次数过多,账号已被锁定")

            await user_db.update_user(user.id, updates)
            raise ValueError("用户名或密码错误")

        # 登录成功,重置登录失败次数
        await user_db.update_user(user.id, {
            "login_attempts": 0,
            "locked_until": None,
            "last_login": datetime.utcnow().isoformat()
        })

        # 生成JWT令牌
        access_token_expires = timedelta(
            days=7 if remember_me else 0,
            minutes=0 if remember_me else JWTManager.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        access_token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            expires_delta=access_token_expires if remember_me else None
        )

        refresh_token = JWTManager.create_refresh_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value
        )

        # 创建会话
        session = UserSession(
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=UserSession.calculate_expiry(
                minutes=7 * 24 * 60 if remember_me else JWTManager.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

        # 保存会话到数据库 (后续实现)
        # await session_db.create_session(session)

        logger.info(f"用户登录成功: {username}, IP: {ip_address}")

        # 构建登录响应
        user_response = UserResponse(
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

        login_response = LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()) if remember_me else JWTManager.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response.model_dump()
        )

        return login_response, session

    async def login_with_user(
        self,
        user: User,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False
    ) -> Tuple[LoginResponse, UserSession]:
        """使用已有用户对象进行登录(用于OAuth)。

        Args:
            user: 用户对象
            ip_address: IP地址
            user_agent: 用户代理
            remember_me: 是否记住登录

        Returns:
            登录响应和会话对象
        """
        # 检查账号是否激活
        if not user.is_active:
            raise ValueError("账号已被禁用")

        # 更新最后登录时间
        await user_db.update_user(user.id, {
            "last_login": datetime.utcnow().isoformat()
        })

        # 生成JWT令牌
        access_token_expires = timedelta(
            days=7 if remember_me else 0,
            minutes=0 if remember_me else JWTManager.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        access_token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            expires_delta=access_token_expires if remember_me else None
        )

        refresh_token = JWTManager.create_refresh_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value
        )

        # 创建会话
        session = UserSession(
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=UserSession.calculate_expiry(
                minutes=7 * 24 * 60 if remember_me else JWTManager.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

        logger.info(f"用户通过OAuth登录成功: {user.username}, IP: {ip_address}")

        # 构建登录响应
        user_response = UserResponse(
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

        login_response = LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()) if remember_me else JWTManager.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response.model_dump()
        )

        return login_response, session

    async def refresh_token(self, refresh_token: str) -> Optional[str]:
        """刷新访问令牌。

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的访问令牌,如果失败则返回None
        """
        new_access_token = JWTManager.refresh_access_token(refresh_token)
        if new_access_token:
            logger.info("访问令牌刷新成功")
        return new_access_token

    async def verify_token(self, token: str) -> Optional[User]:
        """验证令牌并返回用户。

        Args:
            token: 访问令牌

        Returns:
            用户对象,如果验证失败则返回None
        """
        user_id = JWTManager.get_user_id_from_token(token)
        if not user_id:
            return None

        user = await user_db.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None

        return user

    async def logout(self, token: str) -> bool:
        """用户登出。

        Args:
            token: 访问令牌

        Returns:
            是否登出成功
        """
        # 将令牌加入黑名单或从会话表中删除
        # 后续实现会话管理时完善
        logger.info("用户登出")
        return True

    async def send_verification_email(
        self,
        user_id: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """发送邮箱验证邮件。

        Args:
            user_id: 用户ID
            ip_address: 请求IP地址

        Returns:
            是否发送成功

        Raises:
            ValueError: 用户不存在或邮箱已验证
        """
        # 获取用户信息
        user = await user_db.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")

        if user.is_verified:
            raise ValueError("邮箱已经验证过了")

        # 发送验证邮件
        success = await verification_service.send_verification_email(
            user_id=user.id,
            email=user.email,
            username=user.username,
            ip_address=ip_address
        )

        if not success:
            raise ValueError("发送验证邮件失败")

        return True

    async def verify_email(
        self,
        email: EmailStr,
        code: str
    ) -> bool:
        """验证邮箱。

        Args:
            email: 邮箱
            code: 验证码

        Returns:
            是否验证成功

        Raises:
            ValueError: 验证失败
        """
        # 验证验证码
        verification_code = await verification_service.verify_code(
            email=email,
            code=code,
            verification_type=VerificationType.EMAIL_VERIFICATION
        )

        if not verification_code:
            raise ValueError("验证码无效或已过期")

        # 获取用户
        user = await user_db.get_user_by_email(email)
        if not user:
            raise ValueError("用户不存在")

        # 更新用户验证状态
        await user_db.update_user(user.id, {"is_verified": True})

        logger.info(f"用户邮箱验证成功: {user.username}")
        return True

    async def send_password_reset_email(
        self,
        email: EmailStr,
        ip_address: Optional[str] = None
    ) -> bool:
        """发送密码重置邮件。

        Args:
            email: 邮箱
            ip_address: 请求IP地址

        Returns:
            是否发送成功

        Raises:
            ValueError: 用户不存在
        """
        # 获取用户信息
        user = await user_db.get_user_by_email(email)
        if not user:
            # 为了安全,即使用户不存在也返回成功,避免泄露用户信息
            logger.warning(f"尝试重置不存在的邮箱密码: {email}")
            return True

        if not user.is_active:
            raise ValueError("账号已被禁用")

        # 发送密码重置邮件
        success = await verification_service.send_password_reset_email(
            user_id=user.id,
            email=user.email,
            username=user.username,
            ip_address=ip_address
        )

        if not success:
            raise ValueError("发送密码重置邮件失败")

        return True

    async def reset_password(
        self,
        email: EmailStr,
        code: str,
        new_password: str
    ) -> bool:
        """重置密码。

        Args:
            email: 邮箱
            code: 验证码
            new_password: 新密码

        Returns:
            是否重置成功

        Raises:
            ValueError: 重置失败
        """
        # 验证验证码
        verification_code = await verification_service.verify_code(
            email=email,
            code=code,
            verification_type=VerificationType.PASSWORD_RESET
        )

        if not verification_code:
            raise ValueError("验证码无效或已过期")

        # 获取用户
        user = await user_db.get_user_by_email(email)
        if not user:
            raise ValueError("用户不存在")

        # 加密新密码
        password_hash = PasswordHasher.hash_password(new_password)

        # 更新密码
        await user_db.update_user(user.id, {
            "password_hash": password_hash,
            "login_attempts": 0,  # 重置登录失败次数
            "locked_until": None  # 解除锁定
        })

        logger.info(f"用户密码重置成功: {user.username}")
        return True


# 全局认证服务实例
auth_service = AuthService()
