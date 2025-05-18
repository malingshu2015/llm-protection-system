"""拦截器相关数据模型。"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DetectionType(str, Enum):
    """安全检测类型。"""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    ROLE_PLAY = "role_play"
    SENSITIVE_INFO = "sensitive_info"
    HARMFUL_CONTENT = "harmful_content"
    COMPLIANCE_VIOLATION = "compliance_violation"
    CUSTOM = "custom"


class Severity(str, Enum):
    """安全检测严重程度。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InterceptedRequest(BaseModel):
    """拦截的请求模型。"""

    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    query_params: Dict[str, str] = {}
    timestamp: float = 0.0
    client_ip: str = ""
    provider: str = ""


class InterceptedResponse(BaseModel):
    """拦截的响应模型。"""

    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0
    latency: float = 0.0
    is_streaming: bool = False
    raw_response: Any = None


class DetectionResult(BaseModel):
    """安全检测结果。"""

    is_allowed: bool = True
    detection_type: Optional[DetectionType] = None
    severity: Optional[Severity] = None
    reason: str = ""
    details: Dict[str, Any] = {}
    status_code: int = 403


class SecurityRule(BaseModel):
    """安全规则。"""

    id: str
    name: str
    description: str
    detection_type: DetectionType
    severity: Severity
    patterns: List[str] = []
    keywords: List[str] = []
    enabled: bool = True
    block: bool = True
    priority: int = 100  # 优先级，数字越小优先级越高
    categories: List[str] = []  # 规则分类
    custom_code: Optional[str] = None

    # 这些字段不会被序列化/反序列化
    compiled_patterns: List[Any] = Field(default_factory=list, exclude=True)
    keyword_patterns: List[Any] = Field(default_factory=list, exclude=True)
