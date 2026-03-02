from pydantic import ConfigDict
"""用户活动审计日志模型。"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditActionType(str, Enum):
    """审计日志动作类型。"""

    # 认证相关
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"

    # 用户管理
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ROLE_CHANGE = "user_role_change"
    USER_STATUS_CHANGE = "user_status_change"

    # 规则管理
    RULE_CREATE = "rule_create"
    RULE_UPDATE = "rule_update"
    RULE_DELETE = "rule_delete"
    RULE_ENABLE = "rule_enable"
    RULE_DISABLE = "rule_disable"

    # 模型管理
    MODEL_ADD = "model_add"
    MODEL_REMOVE = "model_remove"
    MODEL_CONFIG_UPDATE = "model_config_update"

    # API密钥管理
    API_KEY_CREATE = "api_key_create"
    API_KEY_UPDATE = "api_key_update"
    API_KEY_DELETE = "api_key_delete"
    API_KEY_ROTATE = "api_key_rotate"

    # 安全事件
    SECURITY_EVENT_DETECTED = "security_event_detected"
    SECURITY_EVENT_BLOCKED = "security_event_blocked"

    # 系统操作
    SYSTEM_CONFIG_UPDATE = "system_config_update"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditLogLevel(str, Enum):
    """审计日志级别。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLog(BaseModel):
    """审计日志模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    username: Optional[str] = None
    action_type: AuditActionType
    action_description: str
    resource_type: Optional[str] = None  # 操作的资源类型(如 "user", "rule", "model")
    resource_id: Optional[str] = None    # 操作的资源ID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    level: AuditLogLevel = AuditLogLevel.INFO
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 额外的上下文信息

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "user_id": "user-123",
                "username": "admin",
                "action_type": "user_login",
                "action_description": "用户登录成功",
                "ip_address": "192.168.1.100",
                "level": "info",
                "success": True
            }
        })


class AuditLogQuery(BaseModel):
    """审计日志查询参数。"""

    user_id: Optional[str] = None
    username: Optional[str] = None
    action_type: Optional[AuditActionType] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    level: Optional[AuditLogLevel] = None
    success: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditLogResponse(BaseModel):
    """审计日志查询响应。"""

    total: int
    logs: list[AuditLog]
    limit: int
    offset: int
