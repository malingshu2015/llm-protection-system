"""增强的模型管理API，支持新的UI设计需求。"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from src.logger import logger
from src.models_interceptor import (
    ModelMetadata, SecurityTemplate, ModelTag, 
    SecurityLevel, ModelCategory
)

router = APIRouter(prefix="/api/v1/enhanced-models", tags=["enhanced-models"])


class BatchConfigRequest(BaseModel):
    """批量配置请求。"""
    model_names: List[str]
    template_id: Optional[str] = None
    security_level: Optional[SecurityLevel] = None
    category: Optional[ModelCategory] = None
    tags: Optional[List[str]] = None


class SecurityScoreResponse(BaseModel):
    """安全评分响应。"""
    model_name: str
    risk_score: float
    security_level: SecurityLevel
    enabled_rules_count: int
    total_rules_count: int
    recommendations: List[str]


class ModelSummary(BaseModel):
    """模型概览信息。"""
    total_models: int
    risk_distribution: Dict[str, int]  # high, medium, low, unknown
    category_distribution: Dict[str, int]
    avg_security_score: float


# 数据存储路径
MODELS_METADATA_PATH = "data/models_metadata.json"
SECURITY_TEMPLATES_PATH = "data/security_templates.json"
MODEL_TAGS_PATH = "data/model_tags.json"


def _ensure_data_directories():
    """确保数据目录存在。"""
    os.makedirs("data", exist_ok=True)


def _load_models_metadata() -> Dict[str, ModelMetadata]:
    """加载模型元数据。"""
    _ensure_data_directories()
    try:
        if os.path.exists(MODELS_METADATA_PATH):
            with open(MODELS_METADATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: ModelMetadata(**v) for k, v in data.items()}
    except Exception as e:
        logger.error(f"加载模型元数据失败: {e}")
    return {}


def _save_models_metadata(metadata: Dict[str, ModelMetadata]):
    """保存模型元数据。"""
    _ensure_data_directories()
    try:
        data = {k: v.dict() for k, v in metadata.items()}
        with open(MODELS_METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"保存模型元数据失败: {e}")


def _load_security_templates() -> List[SecurityTemplate]:
    """加载安全模板。"""
    _ensure_data_directories()
    try:
        if os.path.exists(SECURITY_TEMPLATES_PATH):
            with open(SECURITY_TEMPLATES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [SecurityTemplate(**item) for item in data]
    except Exception as e:
        logger.error(f"加载安全模板失败: {e}")
    
    # 返回默认模板
    return _get_default_templates()


def _get_default_templates() -> List[SecurityTemplate]:
    """获取默认安全模板。"""
    return [
        SecurityTemplate(
            id="strict-production",
            name="严格生产模式",
            description="适用于生产环境的高安全级别配置",
            security_level=SecurityLevel.STRICT,
            enabled_rules=["hc-001", "hc-002", "hc-003", "hc-004", "hc-005", "hc-011", "pi-001", "ji-001"],
            is_default=True
        ),
        SecurityTemplate(
            id="balanced-general",
            name="平衡通用模式", 
            description="推荐用于一般用途的平衡配置",
            security_level=SecurityLevel.BALANCED,
            enabled_rules=["hc-001", "hc-003", "hc-004", "hc-011", "pi-001"],
            is_default=True
        ),
        SecurityTemplate(
            id="relaxed-development",
            name="宽松开发模式",
            description="适用于开发测试的宽松配置",
            security_level=SecurityLevel.RELAXED,
            enabled_rules=["hc-004", "hc-011"],
            is_default=True
        )
    ]


def _calculate_security_score(model_name: str, metadata: ModelMetadata) -> float:
    """计算模型安全评分。"""
    # 基础评分
    base_score = 50.0
    
    # 根据安全等级调整
    level_scores = {
        SecurityLevel.STRICT: 90.0,
        SecurityLevel.BALANCED: 70.0,
        SecurityLevel.RELAXED: 40.0
    }
    base_score = level_scores.get(metadata.security_level, 50.0)
    
    # 根据启用的规则数量调整
    if metadata.template_id:
        templates = _load_security_templates()
        template = next((t for t in templates if t.id == metadata.template_id), None)
        if template:
            rule_bonus = min(len(template.enabled_rules) * 5, 30)
            base_score += rule_bonus
    
    # 根据模型分类调整
    category_adjustments = {
        ModelCategory.PRODUCTION: 10,
        ModelCategory.TESTING: 5,
        ModelCategory.DEVELOPMENT: -5,
        ModelCategory.RESEARCH: -10,
        ModelCategory.EDUCATION: 0
    }
    base_score += category_adjustments.get(metadata.category, 0)
    
    return min(max(base_score, 0), 100)


@router.get("/summary", response_model=ModelSummary)
async def get_models_summary():
    """获取模型概览信息。"""
    try:
        metadata = _load_models_metadata()
        
        total = len(metadata)
        risk_dist = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        category_dist = {}
        total_score = 0
        
        for model_meta in metadata.values():
            score = _calculate_security_score(model_meta.model_name, model_meta)
            total_score += score
            
            # 风险分布
            if score >= 80:
                risk_dist["low"] += 1
            elif score >= 60:
                risk_dist["medium"] += 1
            elif score >= 40:
                risk_dist["high"] += 1
            else:
                risk_dist["unknown"] += 1
            
            # 分类分布
            category = model_meta.category.value
            category_dist[category] = category_dist.get(category, 0) + 1
        
        avg_score = total_score / total if total > 0 else 0
        
        return ModelSummary(
            total_models=total,
            risk_distribution=risk_dist,
            category_distribution=category_dist,
            avg_security_score=round(avg_score, 1)
        )
    except Exception as e:
        logger.error(f"获取模型概览失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型概览失败")


@router.get("/security-score/{model_name}", response_model=SecurityScoreResponse)
async def get_security_score(model_name: str):
    """获取指定模型的安全评分。"""
    try:
        metadata = _load_models_metadata()
        model_meta = metadata.get(model_name)
        
        if not model_meta:
            # 为新模型创建默认元数据
            model_meta = ModelMetadata(model_name=model_name)
            metadata[model_name] = model_meta
            _save_models_metadata(metadata)
        
        score = _calculate_security_score(model_name, model_meta)
        
        # 获取启用的规则数量
        enabled_count = 0
        total_count = 12  # 假设总共有12个规则
        
        if model_meta.template_id:
            templates = _load_security_templates()
            template = next((t for t in templates if t.id == model_meta.template_id), None)
            if template:
                enabled_count = len(template.enabled_rules)
        
        # 生成建议
        recommendations = []
        if score < 60:
            recommendations.append("建议提升安全等级到平衡模式")
        if enabled_count < 5:
            recommendations.append("建议启用更多安全规则")
        if model_meta.category == ModelCategory.PRODUCTION and score < 80:
            recommendations.append("生产环境建议使用严格安全配置")
        
        return SecurityScoreResponse(
            model_name=model_name,
            risk_score=score,
            security_level=model_meta.security_level,
            enabled_rules_count=enabled_count,
            total_rules_count=total_count,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"获取安全评分失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全评分失败")


@router.post("/batch-config")
async def batch_configure_models(request: BatchConfigRequest):
    """批量配置模型。"""
    try:
        metadata = _load_models_metadata()
        updated_models = []
        
        for model_name in request.model_names:
            # 获取或创建模型元数据
            if model_name not in metadata:
                metadata[model_name] = ModelMetadata(model_name=model_name)
            
            model_meta = metadata[model_name]
            
            # 应用批量配置
            if request.template_id:
                model_meta.template_id = request.template_id
            if request.security_level:
                model_meta.security_level = request.security_level
            if request.category:
                model_meta.category = request.category
            if request.tags:
                model_meta.tags = request.tags
            
            model_meta.last_updated = datetime.now()
            updated_models.append(model_name)
        
        _save_models_metadata(metadata)
        
        return {
            "success": True,
            "message": f"成功配置 {len(updated_models)} 个模型",
            "updated_models": updated_models
        }
    except Exception as e:
        logger.error(f"批量配置失败: {e}")
        raise HTTPException(status_code=500, detail="批量配置失败")


@router.get("/templates", response_model=List[SecurityTemplate])
async def get_security_templates():
    """获取所有安全模板。"""
    try:
        return _load_security_templates()
    except Exception as e:
        logger.error(f"获取安全模板失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全模板失败")


@router.get("/metadata/{model_name}", response_model=ModelMetadata)
async def get_model_metadata(model_name: str):
    """获取模型元数据。"""
    try:
        metadata = _load_models_metadata()
        
        if model_name not in metadata:
            # 为新模型创建默认元数据
            metadata[model_name] = ModelMetadata(model_name=model_name)
            _save_models_metadata(metadata)
        
        return metadata[model_name]
    except Exception as e:
        logger.error(f"获取模型元数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型元数据失败")


@router.put("/metadata/{model_name}")
async def update_model_metadata(model_name: str, updated_metadata: ModelMetadata):
    """更新模型元数据。"""
    try:
        metadata = _load_models_metadata()
        updated_metadata.model_name = model_name
        updated_metadata.last_updated = datetime.now()
        metadata[model_name] = updated_metadata
        _save_models_metadata(metadata)
        
        return {"success": True, "message": "模型元数据更新成功"}
    except Exception as e:
        logger.error(f"更新模型元数据失败: {e}")
        raise HTTPException(status_code=500, detail="更新模型元数据失败")