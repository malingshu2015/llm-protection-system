"""审计日志API路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.models.audit import AuditLogQuery, AuditLogResponse
from src.auth.services.audit_service import audit_service
from src.auth.services.auth_service import auth_service
from src.logger import logger

router = APIRouter(prefix="/api/v1/audit", tags=["审计日志"])
security = HTTPBearer()


@router.post("/logs", response_model=AuditLogResponse)
async def query_audit_logs(
    query: AuditLogQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuditLogResponse:
    """查询审计日志。

    Args:
        query: 查询参数
        credentials: HTTP授权凭证

    Returns:
        审计日志查询响应

    Raises:
        HTTPException: 查询失败或无权限
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

        # 检查权限(只有管理员和security_analyst可以查看审计日志)
        allowed_roles = ["admin", "super_admin", "security_analyst"]
        if user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限查看审计日志"
            )

        # 查询审计日志
        result = await audit_service.query_logs(query)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询审计日志异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询审计日志失败"
        )


@router.get("/summary/{user_id}")
async def get_user_activity_summary(
    user_id: str,
    days: int = 30,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取用户活动摘要。

    Args:
        user_id: 用户ID
        days: 统计最近几天
        credentials: HTTP授权凭证

    Returns:
        用户活动摘要

    Raises:
        HTTPException: 查询失败或无权限
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

        # 检查权限(只能查看自己的或管理员可以查看所有)
        allowed_roles = ["admin", "super_admin", "security_analyst"]
        if user.id != user_id and user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限查看该用户的活动摘要"
            )

        # 获取活动摘要
        summary = await audit_service.get_user_activity_summary(user_id, days)

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户活动摘要异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户活动摘要失败"
        )
