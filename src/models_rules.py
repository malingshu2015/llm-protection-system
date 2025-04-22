"""模型安全规则配置相关数据模型。"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models_interceptor import SecurityRule


class ModelRuleAssociation(BaseModel):
    """模型-规则关联模型。"""

    id: str
    model_id: str
    rule_id: str
    enabled: bool = True
    priority: int = 100  # 在该模型中的优先级，数字越小优先级越高
    override_params: Dict[str, Any] = Field(default_factory=dict)  # 覆盖默认规则参数
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ModelRuleConfig(BaseModel):
    """模型规则配置模型。"""

    model_id: str
    template_id: Optional[str] = None
    rules: List[ModelRuleAssociation] = []
    enabled: bool = True
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RuleSetTemplate(BaseModel):
    """规则集模板模型。"""

    id: str
    name: str
    description: str
    rules: List[Dict[str, Any]] = []  # 包含rule_id, enabled, priority等信息
    category: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ModelRuleSummary(BaseModel):
    """模型规则摘要，用于前端展示。"""

    model_id: str
    model_name: str
    template_name: Optional[str] = None
    rules_count: int = 0
    enabled_rules_count: int = 0
    security_score: int = 0  # 0-100的安全评分
    last_updated: datetime = Field(default_factory=datetime.now)


class RuleConflict(BaseModel):
    """规则冲突模型。"""

    rule1_id: str
    rule2_id: str
    conflict_type: str  # "pattern_overlap", "priority_conflict", "action_conflict"
    description: str
    suggestion: str
