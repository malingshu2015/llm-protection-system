"""模型安全规则配置API。"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path, status
from pydantic import BaseModel

from src.logger import logger
from src.models_rules import (
    ModelRuleAssociation,
    ModelRuleConfig,
    ModelRuleSummary,
    RuleSetTemplate,
)
from src.security.model_rule_manager import ModelRuleManager
from src.web.rules_api import get_rules


router = APIRouter()
model_rule_manager = ModelRuleManager()


class ModelRuleRequest(BaseModel):
    """模型规则请求。"""

    rule_id: str
    enabled: bool = True
    priority: int = 100
    override_params: Dict = {}


class ModelRuleConfigRequest(BaseModel):
    """模型规则配置请求。"""

    template_id: Optional[str] = None
    rules: List[ModelRuleRequest] = []


class TemplateRequest(BaseModel):
    """模板请求。"""

    name: str
    description: str
    rules: List[Dict] = []
    category: str


class BatchApplyTemplateRequest(BaseModel):
    """批量应用模板请求。"""

    model_ids: List[str]
    template_id: str


class BatchToggleRulesRequest(BaseModel):
    """批量启用/禁用规则请求。"""

    model_ids: List[str]
    rule_ids: List[str]
    enabled: bool


class CreateTemplateFromModelRequest(BaseModel):
    """从模型创建模板请求。"""

    model_id: str
    template_id: str
    name: str
    description: str
    category: str


class CreateModelRuleRequest(BaseModel):
    """创建模型规则关联请求。"""

    model_id: str
    template_id: str
    enabled: bool = True
    description: str = ""


@router.get("/api/v1/model-rules")
async def get_model_rule_summaries():
    """获取所有模型规则摘要。

    Returns:
        模型规则摘要列表
    """
    try:
        # 获取所有规则
        all_rules = await get_rules()

        # 获取所有模型规则配置
        configs = model_rule_manager.get_all_model_rule_configs()

        # 从Ollama API获取真实的本地模型数据
        try:
            import ollama
            client = ollama.Client(host='http://localhost:11434', timeout=30)
            models_response = client.list()
            models_data = {"models": models_response.get("models", [])}
            logger.info(f"成功从Ollama API获取模型列表，模型数量: {len(models_data['models'])}")
        except Exception as e:
            logger.warning(f"从Ollama API获取模型列表失败: {e}，将使用备用方法")
            # 如果无法从API获取模型列表，尝试使用requests库直接调用API
            import requests
            try:
                response = requests.get('http://localhost:11434/api/tags')
                if response.status_code == 200:
                    data = response.json()
                    models_data = {"models": data.get("models", [])}
                    logger.info(f"成功使用requests获取模型列表，模型数量: {len(models_data['models'])}")
                else:
                    logger.warning(f"使用requests获取模型列表失败，状态码: {response.status_code}")
                    models_data = {"models": []}
            except Exception as e2:
                logger.warning(f"使用requests获取模型列表失败: {e2}，将使用模拟数据")
                models_data = {"models": [{"name": "llama2", "model": "llama2"}, {"name": "mistral", "model": "mistral"}]}
        # 创建模型ID到名称的映射
        model_names = {}
        for model in models_data.get("models", []):
            # Ollama API 返回的模型对象使用 'model' 属性作为模型 ID
            # 如果 'model' 属性不存在，则尝试使用 'name' 属性
            # 如果都不存在，则使用字典中的第一个值作为 ID
            if isinstance(model, dict):
                model_id = model.get("model", model.get("name", next(iter(model.values()), "unknown")))
                model_names[model_id] = model_id
            else:
                # 如果模型不是字典，则尝试将其作为字符串使用
                try:
                    model_id = str(model)
                    model_names[model_id] = model_id
                except:
                    logger.warning(f"无法处理模型数据: {model}")
                    continue

        # 添加一些常见的模型，以防 Ollama API 没有返回这些模型
        common_models = ["llama2:latest", "llama3.2:latest", "gemma3:latest", "tinyllama:latest", "deepseek-r1:14b"]
        for model_id in common_models:
            if model_id not in model_names:
                model_names[model_id] = model_id

        # 为每个配置创建摘要
        summaries = []
        for config in configs:
            try:
                model_name = model_names.get(config.model_id, config.model_id)
                # 使用 try-except 块捕获 get_model_rule_summary 中的异常
                try:
                    summary = model_rule_manager.get_model_rule_summary(config.model_id, model_name, all_rules)
                    summaries.append(summary)
                except Exception as e:
                    logger.warning(f"为模型 {config.model_id} 创建摘要失败: {e}")
                    # 创建一个基本的摘要，避免前端显示错误
                    summary = ModelRuleSummary(
                        model_id=config.model_id,
                        model_name=model_name,
                        template_id=None,
                        template_name=None,
                        rules_count=0,
                        enabled_rules_count=0,
                        security_score=0,
                        last_updated=datetime.now()
                    )
                    summaries.append(summary)
            except Exception as e:
                logger.warning(f"处理模型 {config.model_id} 配置失败: {e}")

        # 为每个模型创建摘要（包括尚未配置的模型）
        for model_id, model_name in model_names.items():
            try:
                # 检查是否已经有这个模型的摘要
                if not any(summary.model_id == model_id for summary in summaries):
                    # 创建一个空的摘要
                    summary = ModelRuleSummary(
                        model_id=model_id,
                        model_name=model_name,
                        template_id=None,
                        template_name=None,
                        rules_count=0,
                        enabled_rules_count=0,
                        security_score=0,
                        last_updated=datetime.now()
                    )
                    summaries.append(summary)
            except Exception as e:
                logger.warning(f"为模型 {model_id} 创建默认摘要失败: {e}")

        return summaries
    except Exception as e:
        logger.error(f"获取模型规则摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型规则摘要失败: {str(e)}"
        )


@router.get("/api/v1/model-rules/{model_id}")
async def get_model_rule_config(model_id: str = Path(...)):
    """获取特定模型的规则配置。

    Args:
        model_id: 模型ID

    Returns:
        模型规则配置
    """
    try:
        config = model_rule_manager.get_model_rule_config(model_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型 {model_id} 的规则配置不存在"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型规则配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型规则配置失败: {str(e)}"
        )


@router.post("/api/v1/model-rules/{model_id}")
async def create_or_update_model_rule_config(
    model_id: str = Path(...),
    request: ModelRuleConfigRequest = Body(...)
):
    """创建或更新模型规则配置。

    Args:
        model_id: 模型ID
        request: 模型规则配置请求

    Returns:
        创建或更新的模型规则配置
    """
    try:
        # 检查是否存在现有配置
        existing_config = model_rule_manager.get_model_rule_config(model_id)

        if existing_config:
            # 更新现有配置
            config = existing_config
            config.template_id = request.template_id

            # 更新规则列表
            config.rules = []
            for rule_req in request.rules:
                association = ModelRuleAssociation(
                    id=f"{model_id}_{rule_req.rule_id}",
                    model_id=model_id,
                    rule_id=rule_req.rule_id,
                    enabled=rule_req.enabled,
                    priority=rule_req.priority,
                    override_params=rule_req.override_params
                )
                config.rules.append(association)

            # 更新配置
            config = model_rule_manager.update_model_rule_config(config)
        else:
            # 创建新配置
            rules = []
            for rule_req in request.rules:
                association = ModelRuleAssociation(
                    id=f"{model_id}_{rule_req.rule_id}",
                    model_id=model_id,
                    rule_id=rule_req.rule_id,
                    enabled=rule_req.enabled,
                    priority=rule_req.priority,
                    override_params=rule_req.override_params
                )
                rules.append(association)

            config = ModelRuleConfig(
                model_id=model_id,
                template_id=request.template_id,
                rules=rules
            )

            # 创建配置
            config = model_rule_manager.create_model_rule_config(config)

        return config
    except Exception as e:
        logger.error(f"创建或更新模型规则配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建或更新模型规则配置失败: {str(e)}"
        )


@router.delete("/api/v1/model-rules/{model_id}")
async def delete_model_rule_config(model_id: str = Path(...)):
    """删除模型规则配置。

    Args:
        model_id: 模型ID

    Returns:
        删除结果
    """
    try:
        success = model_rule_manager.delete_model_rule_config(model_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模型 {model_id} 的规则配置不存在"
            )
        return {"success": True, "message": f"模型 {model_id} 的规则配置已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型规则配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除模型规则配置失败: {str(e)}"
        )


@router.get("/api/v1/model-rules/{model_id}/conflicts")
async def get_model_rule_conflicts(model_id: str = Path(...)):
    """获取模型规则冲突。

    Args:
        model_id: 模型ID

    Returns:
        规则冲突列表
    """
    try:
        conflicts = model_rule_manager.detect_rule_conflicts(model_id)
        return conflicts
    except Exception as e:
        logger.error(f"获取模型规则冲突失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型规则冲突失败: {str(e)}"
        )


@router.get("/api/v1/rule-templates")
async def get_rule_templates():
    """获取所有规则集模板。

    Returns:
        规则集模板列表
    """
    try:
        templates = model_rule_manager.get_all_templates()
        return templates
    except Exception as e:
        logger.error(f"获取规则集模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取规则集模板失败: {str(e)}"
        )


@router.get("/api/v1/rule-templates/{template_id}")
async def get_rule_template(template_id: str = Path(...)):
    """获取特定规则集模板。

    Args:
        template_id: 模板ID

    Returns:
        规则集模板
    """
    try:
        template = model_rule_manager.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板 {template_id} 不存在"
            )
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取规则集模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取规则集模板失败: {str(e)}"
        )


@router.post("/api/v1/rule-templates")
async def create_rule_template(request: TemplateRequest = Body(...)):
    """创建规则集模板。

    Args:
        request: 模板请求

    Returns:
        创建的规则集模板
    """
    try:
        # 生成模板ID
        template_id = f"template-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        template = RuleSetTemplate(
            id=template_id,
            name=request.name,
            description=request.description,
            rules=request.rules,
            category=request.category
        )

        template = model_rule_manager.create_template(template)
        return template
    except Exception as e:
        logger.error(f"创建规则集模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建规则集模板失败: {str(e)}"
        )


@router.put("/api/v1/rule-templates/{template_id}")
async def update_rule_template(
    template_id: str = Path(...),
    request: TemplateRequest = Body(...)
):
    """更新规则集模板。

    Args:
        template_id: 模板ID
        request: 模板请求

    Returns:
        更新的规则集模板
    """
    try:
        template = model_rule_manager.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板 {template_id} 不存在"
            )

        template.name = request.name
        template.description = request.description
        template.rules = request.rules
        template.category = request.category

        template = model_rule_manager.update_template(template)
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新规则集模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新规则集模板失败: {str(e)}"
        )


@router.delete("/api/v1/rule-templates/{template_id}")
async def delete_rule_template(template_id: str = Path(...)):
    """删除规则集模板。

    Args:
        template_id: 模板ID

    Returns:
        删除结果
    """
    try:
        success = model_rule_manager.delete_template(template_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板 {template_id} 不存在"
            )
        return {"success": True, "message": f"模板 {template_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除规则集模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除规则集模板失败: {str(e)}"
        )


@router.post("/api/v1/models/{model_id}/apply-template/{template_id}")
async def apply_template_to_model(
    model_id: str = Path(...),
    template_id: str = Path(...)
):
    """将模板应用到模型。

    Args:
        model_id: 模型ID
        template_id: 模板ID

    Returns:
        更新后的模型规则配置
    """
    try:
        config = model_rule_manager.apply_template_to_model(model_id, template_id)
        return config
    except Exception as e:
        logger.error(f"将模板应用到模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"将模板应用到模型失败: {str(e)}"
        )


@router.post("/api/v1/models/batch/apply-template")
async def batch_apply_template(request: BatchApplyTemplateRequest = Body(...)):
    """批量应用模板到多个模型。

    Args:
        request: 批量应用模板请求

    Returns:
        批量应用结果
    """
    try:
        success_count = model_rule_manager.batch_apply_template(
            request.model_ids, request.template_id
        )
        return {
            "success": True,
            "message": f"成功将模板应用到 {success_count}/{len(request.model_ids)} 个模型"
        }
    except Exception as e:
        logger.error(f"批量应用模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量应用模板失败: {str(e)}"
        )


@router.post("/api/v1/models/batch/toggle-rules")
async def batch_toggle_rules(request: BatchToggleRulesRequest = Body(...)):
    """批量启用/禁用规则。

    Args:
        request: 批量启用/禁用规则请求

    Returns:
        批量操作结果
    """
    try:
        success_count = model_rule_manager.batch_toggle_rules(
            request.model_ids, request.rule_ids, request.enabled
        )
        action = "启用" if request.enabled else "禁用"
        return {
            "success": True,
            "message": f"成功为 {success_count}/{len(request.model_ids)} 个模型{action}规则"
        }
    except Exception as e:
        logger.error(f"批量{('启用' if request.enabled else '禁用')}规则失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量{('启用' if request.enabled else '禁用')}规则失败: {str(e)}"
        )


@router.post("/api/v1/model-rules")
async def create_model_rule(request: CreateModelRuleRequest = Body(...)):
    """创建模型规则关联。

    Args:
        request: 创建模型规则关联请求

    Returns:
        创建的模型规则关联
    """
    try:
        # 检查模板是否存在
        template = model_rule_manager.get_template(request.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板 {request.template_id} 不存在"
            )

        # 应用模板到模型
        config = model_rule_manager.apply_template_to_model(request.model_id, request.template_id)

        # 更新启用状态
        config.enabled = request.enabled
        config.description = request.description

        # 更新配置
        config = model_rule_manager.update_model_rule_config(config)

        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模型规则关联失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建模型规则关联失败: {str(e)}"
        )


@router.post("/api/v1/rule-templates/create-from-model")
async def create_template_from_model(request: CreateTemplateFromModelRequest = Body(...)):
    """从模型配置创建模板。

    Args:
        request: 从模型创建模板请求

    Returns:
        创建的模板
    """
    try:
        template = model_rule_manager.create_template_from_model(
            request.model_id,
            request.template_id,
            request.name,
            request.description,
            request.category
        )
        return template
    except Exception as e:
        logger.error(f"从模型创建模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从模型创建模板失败: {str(e)}"
        )
