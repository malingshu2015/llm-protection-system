"""用户统计面板 API路由。"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.auth.models.user import UserRole
from src.auth.services.auth_service import auth_service
from src.auth.services.user_db import user_db
from src.auth.services.audit_service import audit_service
from src.logger import logger

router = APIRouter(prefix="/api/v1/statistics", tags=["用户统计"])
security = HTTPBearer()


class UserStatistics(BaseModel):
    """用户统计模型。"""

    total_users: int
    active_users: int
    verified_users: int
    locked_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int


class ActivityStatistics(BaseModel):
    """活动统计模型。"""

    total_actions: int
    successful_actions: int
    failed_actions: int
    logins_today: int
    logins_this_week: int
    logins_this_month: int


class RoleDistribution(BaseModel):
    """角色分布模型。"""

    user: int
    admin: int
    super_admin: int
    security_analyst: int
    developer: int
    auditor: int


class DashboardStatistics(BaseModel):
    """仪表板统计模型。"""

    user_stats: UserStatistics
    activity_stats: ActivityStatistics
    role_distribution: RoleDistribution
    top_active_users: list[dict]  # 最活跃用户


@router.get("/dashboard", response_model=DashboardStatistics)
async def get_dashboard_statistics(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    days: int = 30
) -> DashboardStatistics:
    """获取仪表板统计数据。

    Args:
        credentials: HTTP授权凭证
        days: 统计天数

    Returns:
        仪表板统计数据

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

        # 检查权限 (只有管理员和安全分析师可以查看)
        allowed_roles = [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECURITY_ANALYST]
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问统计数据"
            )

        # 获取所有用户
        all_users = await user_db.get_all_users()

        # 计算用户统计
        total_users = len(all_users)
        active_users = sum(1 for u in all_users if u.is_active)
        verified_users = sum(1 for u in all_users if u.is_verified)
        locked_users = sum(
            1 for u in all_users
            if u.locked_until and u.locked_until > datetime.now(timezone.utc)
        )

        # 计算时间统计
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        new_users_today = sum(1 for u in all_users if u.created_at >= today_start)
        new_users_this_week = sum(1 for u in all_users if u.created_at >= week_start)
        new_users_this_month = sum(1 for u in all_users if u.created_at >= month_start)

        user_stats = UserStatistics(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            locked_users=locked_users,
            new_users_today=new_users_today,
            new_users_this_week=new_users_this_week,
            new_users_this_month=new_users_this_month,
        )

        # 计算角色分布
        role_distribution = RoleDistribution(
            user=sum(1 for u in all_users if u.role == UserRole.USER),
            admin=sum(1 for u in all_users if u.role == UserRole.ADMIN),
            super_admin=sum(1 for u in all_users if u.role == UserRole.SUPER_ADMIN),
            security_analyst=sum(1 for u in all_users if u.role == UserRole.SECURITY_ANALYST),
            developer=sum(1 for u in all_users if u.role == UserRole.DEVELOPER),
            auditor=sum(1 for u in all_users if u.role == UserRole.AUDITOR),
        )

        # 获取活动统计
        from src.auth.models.audit import AuditLogQuery, AuditActionType

        # 查询所有审计日志
        query = AuditLogQuery(limit=10000)
        audit_response = await audit_service.query_logs(query)

        total_actions = audit_response.total
        successful_actions = sum(1 for log in audit_response.logs if log.success)
        failed_actions = total_actions - successful_actions

        # 计算登录统计
        login_logs = [
            log for log in audit_response.logs
            if log.action_type == AuditActionType.USER_LOGIN
        ]

        logins_today = sum(1 for log in login_logs if log.timestamp >= today_start)
        logins_this_week = sum(1 for log in login_logs if log.timestamp >= week_start)
        logins_this_month = sum(1 for log in login_logs if log.timestamp >= month_start)

        activity_stats = ActivityStatistics(
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            logins_today=logins_today,
            logins_this_week=logins_this_week,
            logins_this_month=logins_this_month,
        )

        # 计算最活跃用户
        user_activity_count = {}
        for log in audit_response.logs:
            if log.user_id:
                user_activity_count[log.user_id] = user_activity_count.get(log.user_id, 0) + 1

        # 排序并获取前10名
        top_users = sorted(user_activity_count.items(), key=lambda x: x[1], reverse=True)[:10]

        top_active_users = []
        for user_id, count in top_users:
            user_obj = await user_db.get_user_by_id(user_id)
            if user_obj:
                top_active_users.append({
                    "user_id": user_id,
                    "username": user_obj.username,
                    "email": user_obj.email,
                    "action_count": count,
                    "role": user_obj.role.value
                })

        return DashboardStatistics(
            user_stats=user_stats,
            activity_stats=activity_stats,
            role_distribution=role_distribution,
            top_active_users=top_active_users,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计数据异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计数据失败"
        )


@router.get("/user/{user_id}")
async def get_user_statistics(
    user_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    days: int = 30
) -> dict:
    """获取单个用户的统计数据。

    Args:
        user_id: 用户ID
        credentials: HTTP授权凭证
        days: 统计天数

    Returns:
        用户统计数据

    Raises:
        HTTPException: 获取失败
    """
    try:
        # 验证令牌
        token = credentials.credentials
        current_user = await auth_service.verify_token(token)

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 检查权限 (只能查看自己的统计，或管理员查看任意用户)
        allowed_roles = [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECURITY_ANALYST]
        if current_user.id != user_id and current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看其他用户的统计数据"
            )

        # 获取用户活动摘要
        summary = await audit_service.get_user_activity_summary(user_id, days)

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户统计异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户统计失败"
        )
