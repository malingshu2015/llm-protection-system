"""
客户端专用 API
提供策略管理、健康检查等功能
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.auth.services.auth_service import get_current_user
from src.auth.models.user import User

router = APIRouter(prefix="/api/v1/client", tags=["客户端API"])


class PolicyResponse(BaseModel):
    """策略响应"""
    version: int
    patterns: dict
    keywords: list[str]
    customRules: Optional[list[dict]] = None
    inputRules: Optional[list[dict]] = None
    outputRules: Optional[list[dict]] = None
    modelConfig: Optional[dict] = None
    updatedAt: datetime


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    last_sync: datetime
    policy_version: int


@router.get("/policies/latest", response_model=PolicyResponse)
async def get_latest_policies(
    client_version: str = "1.0.0",
    current_policy_version: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """获取最新策略

    Args:
        client_version: 客户端版本
        current_policy_version: 当前策略版本
        current_user: 当前用户

    Returns:
        最新的安全策略
    """

    # TODO: 从数据库获取用户的策略配置
    # 这里先返回模拟数据

    policy = PolicyResponse(
        version=1,
        patterns={
            "email": r"[\w.-]+@[\w.-]+\.\w+",
            "phone": r"\d{3}-\d{3,4}-\d{4}",
            "ssn": r"\d{3}-\d{2}-\d{4}",
            "creditCard": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
        },
        keywords=["密码", "账号", "敏感信息"],
        customRules=[
            {
                "name": "示例规则",
                "code": "return { blocked: false };",
                "enabled": True
            }
        ],
        inputRules=[
            {
                "id": "rule_1",
                "name": "禁止输入个人信息",
                "keywords": ["身份证", "手机号"],
                "severity": "high",
                "action": "block",
                "enabled": True
            }
        ],
        outputRules=[
            {
                "id": "rule_2",
                "name": "脱敏个人信息",
                "keywords": ["电话", "邮箱"],
                "severity": "medium",
                "action": "warn",
                "enabled": True
            }
        ],
        modelConfig={
            "maxTokens": 2000,
            "temperature": 0.7,
            "allowedModels": ["gpt-4", "gpt-3.5-turbo"],
        },
        updatedAt=datetime.utcnow()
    )

    return policy


@router.get("/health", response_model=HealthResponse)
async def check_client_health(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """检查客户端健康状态

    Args:
        client_id: 客户端ID
        current_user: 当前用户

    Returns:
        健康检查结果
    """

    return HealthResponse(
        status="online",
        version="1.0.0",
        last_sync=datetime.utcnow(),
        policy_version=1
    )


@router.post("/report-issue")
async def report_issue(
    issue: dict,
    current_user: User = Depends(get_current_user)
):
    """报告客户端问题

    Args:
        issue: 问题详情
        current_user: 当前用户

    Returns:
        报告结果
    """

    # TODO: 保存问题报告到数据库

    return {
        "success": True,
        "issue_id": f"issue_{datetime.utcnow().timestamp()}",
        "message": "问题已记录，感谢您的反馈"
    }
