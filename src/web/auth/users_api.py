"""用户管理API路由。"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.auth.middleware import get_current_user, require_admin
from src.auth.models.user import (
    ChangePasswordRequest,
    User,
    UserResponse,
    UserRole,
    UserUpdate,
)
from src.auth.services.user_db import user_db
from src.auth.utils.password import PasswordHasher
from src.logger import logger

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    role: Optional[UserRole] = None,
    current_user: User = Depends(require_admin)
) -> List[UserResponse]:
    """获取用户列表(仅管理员)。

    Args:
        limit: 返回数量限制
        offset: 偏移量
        role: 角色过滤
        current_user: 当前用户

    Returns:
        用户列表
    """
    try:
        users = await user_db.list_users(limit=limit, offset=offset, role=role)
        return [
            UserResponse(
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
            for user in users
        ]
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """获取用户详情。

    Args:
        user_id: 用户ID
        current_user: 当前用户

    Returns:
        用户详情

    Raises:
        HTTPException: 用户不存在或无权访问
    """
    # 只能查看自己的信息,或管理员可以查看所有用户
    if current_user.id != user_id and current_user.role not in [
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他用户信息"
        )

    try:
        user = await user_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
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
        logger.error(f"获取用户详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户详情失败"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """更新用户信息。

    Args:
        user_id: 用户ID
        user_update: 更新数据
        current_user: 当前用户

    Returns:
        更新后的用户信息

    Raises:
        HTTPException: 更新失败
    """
    # 只能更新自己的信息,或管理员可以更新所有用户
    if current_user.id != user_id and current_user.role not in [
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改其他用户信息"
        )

    try:
        # 检查用户是否存在
        user = await user_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 准备更新数据
        updates = {}
        if user_update.email is not None:
            updates["email"] = user_update.email
        if user_update.phone is not None:
            updates["phone"] = user_update.phone
        if user_update.department is not None:
            updates["department"] = user_update.department
        if user_update.avatar_url is not None:
            updates["avatar_url"] = user_update.avatar_url
        if user_update.preferences is not None:
            import json
            updates["preferences"] = json.dumps(user_update.preferences)

        # 角色和状态只有管理员可以修改
        if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            if user_update.role is not None:
                updates["role"] = user_update.role.value
            if user_update.is_active is not None:
                updates["is_active"] = int(user_update.is_active)

        # 执行更新
        if updates:
            await user_db.update_user(user_id, updates)

        # 返回更新后的用户信息
        updated_user = await user_db.get_user_by_id(user_id)
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            phone=updated_user.phone,
            role=updated_user.role,
            department=updated_user.department,
            is_active=updated_user.is_active,
            is_verified=updated_user.is_verified,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            last_login=updated_user.last_login,
            avatar_url=updated_user.avatar_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin)
) -> None:
    """删除用户(仅管理员)。

    Args:
        user_id: 用户ID
        current_user: 当前用户

    Raises:
        HTTPException: 删除失败
    """
    # 不能删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号"
        )

    try:
        success = await user_db.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
) -> None:
    """修改当前用户密码。

    Args:
        password_data: 密码修改数据
        current_user: 当前用户

    Raises:
        HTTPException: 修改失败
    """
    try:
        # 验证旧密码
        if not PasswordHasher.verify_password(
            password_data.old_password,
            current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原密码错误"
            )

        # 加密新密码
        new_password_hash = PasswordHasher.hash_password(password_data.new_password)

        # 更新密码
        await user_db.update_user(current_user.id, {
            "password_hash": new_password_hash
        })

        logger.info(f"用户 {current_user.username} 修改密码成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )
