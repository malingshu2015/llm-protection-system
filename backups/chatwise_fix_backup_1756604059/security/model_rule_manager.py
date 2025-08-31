"""模型安全规则配置管理器。"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionType, SecurityRule
from src.models_rules import (
    ModelRuleAssociation,
    ModelRuleConfig,
    ModelRuleSummary,
    RuleConflict,
    RuleSetTemplate,
)


class ModelRuleManager:
    """模型安全规则配置管理器。"""

    def __init__(self):
        """初始化模型规则管理器。"""
        self.model_rules_path = os.path.join(settings.rules.rules_path, "model_rules.json")
        self.templates_path = os.path.join(settings.rules.rules_path, "rule_templates.json")
        self.model_rules: Dict[str, ModelRuleConfig] = {}
        self.templates: Dict[str, RuleSetTemplate] = {}
        self._load_model_rules()
        self._load_templates()

    def _load_model_rules(self) -> None:
        """加载模型规则配置。"""
        try:
            if os.path.exists(self.model_rules_path):
                with open(self.model_rules_path, "r") as f:
                    data = json.load(f)
                    for item in data:
                        # 处理日期时间字段
                        if "created_at" in item and isinstance(item["created_at"], str):
                            try:
                                item["created_at"] = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                            except ValueError:
                                item["created_at"] = datetime.now()

                        if "updated_at" in item and isinstance(item["updated_at"], str):
                            try:
                                item["updated_at"] = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                            except ValueError:
                                item["updated_at"] = datetime.now()

                        # 处理规则列表中的日期时间字段
                        if "rules" in item and isinstance(item["rules"], list):
                            for rule in item["rules"]:
                                if "created_at" in rule and isinstance(rule["created_at"], str):
                                    try:
                                        rule["created_at"] = datetime.fromisoformat(rule["created_at"].replace("Z", "+00:00"))
                                    except ValueError:
                                        rule["created_at"] = datetime.now()

                                if "updated_at" in rule and isinstance(rule["updated_at"], str):
                                    try:
                                        rule["updated_at"] = datetime.fromisoformat(rule["updated_at"].replace("Z", "+00:00"))
                                    except ValueError:
                                        rule["updated_at"] = datetime.now()

                        try:
                            config = ModelRuleConfig(**item)
                            self.model_rules[config.model_id] = config
                        except Exception as e:
                            logger.warning(f"解析模型规则配置项失败: {e}, 跳过该项: {item}")
            else:
                # 创建目录（如果不存在）
                os.makedirs(os.path.dirname(self.model_rules_path), exist_ok=True)
                # 创建空文件
                with open(self.model_rules_path, "w") as f:
                    json.dump([], f)
        except Exception as e:
            logger.error(f"加载模型规则配置失败: {e}")
            # 不要完全重置模型规则，保留已成功加载的规则
            if not self.model_rules:
                self.model_rules = {}

    def _load_templates(self) -> None:
        """加载规则集模板。"""
        try:
            if os.path.exists(self.templates_path):
                with open(self.templates_path, "r") as f:
                    data = json.load(f)
                    for item in data:
                        # 处理日期时间字段
                        if "created_at" in item and isinstance(item["created_at"], str):
                            try:
                                item["created_at"] = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                            except ValueError:
                                item["created_at"] = datetime.now()

                        if "updated_at" in item and isinstance(item["updated_at"], str):
                            try:
                                item["updated_at"] = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                            except ValueError:
                                item["updated_at"] = datetime.now()

                        try:
                            template = RuleSetTemplate(**item)
                            self.templates[template.id] = template
                        except Exception as e:
                            logger.warning(f"解析规则集模板项失败: {e}, 跳过该项: {item}")
            else:
                # 创建目录（如果不存在）
                os.makedirs(os.path.dirname(self.templates_path), exist_ok=True)
                # 创建默认模板
                default_templates = self._create_default_templates()
                with open(self.templates_path, "w") as f:
                    json.dump([t.model_dump() for t in default_templates], f, indent=2)

                for template in default_templates:
                    self.templates[template.id] = template
        except Exception as e:
            logger.error(f"加载规则集模板失败: {e}")
            # 不要完全重置模板，保留已成功加载的模板
            if not self.templates:
                self.templates = {}

    def _create_default_templates(self) -> List[RuleSetTemplate]:
        """创建默认规则集模板。"""
        # 严格安全模板
        strict_template = RuleSetTemplate(
            id="high_security",
            name="高安全级别",
            description="适用于高安全要求场景的规则集，启用所有安全规则",
            rules=[
                # 提示注入检测规则
                {"rule_id": "pi-001", "enabled": True, "priority": 10},
                {"rule_id": "pi-002", "enabled": True, "priority": 11},
                {"rule_id": "pi-003", "enabled": True, "priority": 5},
                {"rule_id": "pi-004", "enabled": True, "priority": 12},
                {"rule_id": "pi-005", "enabled": True, "priority": 13},
                {"rule_id": "pi-006", "enabled": True, "priority": 8},
                {"rule_id": "pi-007", "enabled": True, "priority": 7},
                {"rule_id": "pi-008", "enabled": True, "priority": 6},

                # 越狱检测规则
                {"rule_id": "jb-001", "enabled": True, "priority": 5},
                {"rule_id": "jb-002", "enabled": True, "priority": 5},
                {"rule_id": "jb-003", "enabled": True, "priority": 6},
                {"rule_id": "jb-004", "enabled": True, "priority": 7},
                {"rule_id": "jb-005", "enabled": True, "priority": 8},
                {"rule_id": "jb-006", "enabled": True, "priority": 9},
                {"rule_id": "jb-007", "enabled": True, "priority": 7},
                {"rule_id": "jb-008", "enabled": True, "priority": 6},

                # 敏感信息检测规则
                {"rule_id": "si-001", "enabled": True, "priority": 20},
                {"rule_id": "si-002", "enabled": True, "priority": 21},
                {"rule_id": "si-003", "enabled": True, "priority": 22},

                # 有害内容检测规则
                {"rule_id": "hc-001", "enabled": True, "priority": 15},
                {"rule_id": "hc-002", "enabled": True, "priority": 16},
                {"rule_id": "hc-003", "enabled": True, "priority": 17},
                {"rule_id": "hc-004", "enabled": True, "priority": 18},
                {"rule_id": "hc-005", "enabled": True, "priority": 19},
                {"rule_id": "hc-006", "enabled": True, "priority": 16},
                {"rule_id": "hc-007", "enabled": True, "priority": 14},
                {"rule_id": "hc-008", "enabled": True, "priority": 15},
                {"rule_id": "hc-009", "enabled": True, "priority": 13},
                {"rule_id": "hc-010", "enabled": True, "priority": 14},

                # 合规性检测规则
                {"rule_id": "comp-001", "enabled": True, "priority": 30},
                {"rule_id": "comp-002", "enabled": True, "priority": 31},
            ],
            category="security",
        )

        # 标准安全模板
        standard_template = RuleSetTemplate(
            id="medium_security",
            name="中安全级别",
            description="适用于一般安全要求的场景，平衡安全性和灵活性",
            rules=[
                # 提示注入检测规则
                {"rule_id": "pi-001", "enabled": True, "priority": 10},
                {"rule_id": "pi-003", "enabled": True, "priority": 5},
                {"rule_id": "pi-006", "enabled": True, "priority": 8},

                # 越狱检测规则
                {"rule_id": "jb-001", "enabled": True, "priority": 5},
                {"rule_id": "jb-002", "enabled": True, "priority": 5},

                # 敏感信息检测规则
                {"rule_id": "si-001", "enabled": True, "priority": 20},

                # 有害内容检测规则
                {"rule_id": "hc-004", "enabled": True, "priority": 18},
                {"rule_id": "hc-005", "enabled": True, "priority": 19},
                {"rule_id": "hc-007", "enabled": True, "priority": 14},

                # 合规性检测规则
                {"rule_id": "comp-001", "enabled": True, "priority": 30},
            ],
            category="security",
        )

        # 最小安全模板
        minimal_template = RuleSetTemplate(
            id="low_security",
            name="低安全级别",
            description="适用于低安全要求的场景，只启用关键安全规则",
            rules=[
                # 越狱检测规则
                {"rule_id": "jb-001", "enabled": True, "priority": 5},

                # 敏感信息检测规则
                {"rule_id": "si-001", "enabled": True, "priority": 20},

                # 有害内容检测规则
                {"rule_id": "hc-004", "enabled": True, "priority": 18},
                {"rule_id": "hc-005", "enabled": True, "priority": 19},
            ],
            category="security",
        )

        # 研究模板
        research_template = RuleSetTemplate(
            id="research",
            name="研究模式",
            description="适用于研究和测试场景，最小化安全限制",
            rules=[
                # 敏感信息检测规则
                {"rule_id": "si-001", "enabled": True, "priority": 20},

                # 有害内容检测规则
                {"rule_id": "hc-005", "enabled": True, "priority": 19},
            ],
            category="research",
        )

        # 自定义模板
        custom_template = RuleSetTemplate(
            id="custom",
            name="自定义模式",
            description="用户自定义规则模板，可根据需要自由配置",
            rules=[],
            category="custom",
        )

        return [strict_template, standard_template, minimal_template, research_template, custom_template]

    def _save_model_rules(self) -> None:
        """保存模型规则配置。"""
        try:
            # 使用model_dump方法并指定序列化日期时间字段
            with open(self.model_rules_path, "w") as f:
                json.dump([config.model_dump(mode='json') for config in self.model_rules.values()], f, indent=2)
        except Exception as e:
            logger.error(f"保存模型规则配置失败: {e}")

    def _save_templates(self) -> None:
        """保存规则集模板。"""
        try:
            # 使用model_dump方法并指定序列化日期时间字段
            with open(self.templates_path, "w") as f:
                json.dump([template.model_dump(mode='json') for template in self.templates.values()], f, indent=2)
        except Exception as e:
            logger.error(f"保存规则集模板失败: {e}")

    def get_model_rule_config(self, model_id: str) -> Optional[ModelRuleConfig]:
        """获取模型规则配置。

        Args:
            model_id: 模型ID

        Returns:
            模型规则配置，如果不存在则返回None
        """
        return self.model_rules.get(model_id)

    def get_all_model_rule_configs(self) -> List[ModelRuleConfig]:
        """获取所有模型规则配置。

        Returns:
            所有模型规则配置列表
        """
        return list(self.model_rules.values())

    def create_model_rule_config(self, config: ModelRuleConfig) -> ModelRuleConfig:
        """创建模型规则配置。

        Args:
            config: 模型规则配置

        Returns:
            创建的模型规则配置
        """
        self.model_rules[config.model_id] = config
        self._save_model_rules()
        return config

    def update_model_rule_config(self, config: ModelRuleConfig) -> ModelRuleConfig:
        """更新模型规则配置。

        Args:
            config: 模型规则配置

        Returns:
            更新后的模型规则配置
        """
        config.updated_at = datetime.now()
        self.model_rules[config.model_id] = config
        self._save_model_rules()
        return config

    def delete_model_rule_config(self, model_id: str) -> bool:
        """删除模型规则配置。

        Args:
            model_id: 模型ID

        Returns:
            是否删除成功
        """
        if model_id in self.model_rules:
            del self.model_rules[model_id]
            self._save_model_rules()
            return True
        return False

    def get_template(self, template_id: str) -> Optional[RuleSetTemplate]:
        """获取规则集模板。

        Args:
            template_id: 模板ID

        Returns:
            规则集模板，如果不存在则返回None
        """
        return self.templates.get(template_id)

    def get_all_templates(self) -> List[RuleSetTemplate]:
        """获取所有规则集模板。

        Returns:
            所有规则集模板列表
        """
        return list(self.templates.values())

    def create_template(self, template: RuleSetTemplate) -> RuleSetTemplate:
        """创建规则集模板。

        Args:
            template: 规则集模板

        Returns:
            创建的规则集模板
        """
        self.templates[template.id] = template
        self._save_templates()
        return template

    def update_template(self, template: RuleSetTemplate) -> RuleSetTemplate:
        """更新规则集模板。

        Args:
            template: 规则集模板

        Returns:
            更新后的规则集模板
        """
        template.updated_at = datetime.now()
        self.templates[template.id] = template
        self._save_templates()
        return template

    def delete_template(self, template_id: str) -> bool:
        """删除规则集模板。

        Args:
            template_id: 模板ID

        Returns:
            是否删除成功
        """
        if template_id in self.templates:
            del self.templates[template_id]
            self._save_templates()
            return True
        return False

    def apply_template_to_model(self, model_id: str, template_id: str) -> ModelRuleConfig:
        """将规则集模板应用到模型。

        Args:
            model_id: 模型ID
            template_id: 模板ID

        Returns:
            更新后的模型规则配置
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")

        # 创建或获取模型规则配置
        config = self.get_model_rule_config(model_id)
        if not config:
            config = ModelRuleConfig(model_id=model_id, template_id=template_id)
        else:
            config.template_id = template_id

        # 清除现有规则
        config.rules = []

        # 应用模板中的规则
        for rule_info in template.rules:
            rule_id = rule_info["rule_id"]
            enabled = rule_info.get("enabled", True)
            priority = rule_info.get("priority", 100)

            association = ModelRuleAssociation(
                id=f"{model_id}_{rule_id}",
                model_id=model_id,
                rule_id=rule_id,
                enabled=enabled,
                priority=priority,
                override_params=rule_info.get("override_params", {})
            )
            config.rules.append(association)

        # 保存配置
        self.update_model_rule_config(config)
        return config

    def detect_rule_conflicts(self, model_id: str) -> List[RuleConflict]:
        """检测模型规则冲突。

        Args:
            model_id: 模型ID

        Returns:
            规则冲突列表
        """
        conflicts = []
        config = self.get_model_rule_config(model_id)
        if not config:
            return conflicts

        # 获取所有启用的规则
        enabled_rules = [rule for rule in config.rules if rule.enabled]

        # 检查优先级冲突
        priority_map = {}
        for rule in enabled_rules:
            if rule.priority in priority_map:
                conflicts.append(RuleConflict(
                    rule1_id=priority_map[rule.priority],
                    rule2_id=rule.rule_id,
                    conflict_type="priority_conflict",
                    description=f"规则 {priority_map[rule.priority]} 和 {rule.rule_id} 具有相同的优先级 {rule.priority}",
                    suggestion="调整其中一个规则的优先级"
                ))
            else:
                priority_map[rule.priority] = rule.rule_id

        # TODO: 实现更复杂的冲突检测，如模式重叠、动作冲突等

        return conflicts

    def get_model_rule_summary(self, model_id: str, model_name: str, all_rules: List[SecurityRule]) -> ModelRuleSummary:
        """获取模型规则摘要。

        Args:
            model_id: 模型ID
            model_name: 模型名称
            all_rules: 所有安全规则

        Returns:
            模型规则摘要
        """
        config = self.get_model_rule_config(model_id)
        if not config:
            return ModelRuleSummary(
                model_id=model_id,
                model_name=model_name,
                template_id=None,
                template_name=None,
                rules_count=0,
                enabled_rules_count=0,
                security_score=0,
                last_updated=datetime.now()
            )

        # 获取模板名称
        template_name = None
        if config.template_id and config.template_id in self.templates:
            template_name = self.templates[config.template_id].name

        # 计算规则数量
        rules_count = len(config.rules)
        enabled_rules_count = sum(1 for rule in config.rules if rule.enabled)

        # 计算安全评分
        security_score = self._calculate_security_score(config, all_rules)

        return ModelRuleSummary(
            model_id=model_id,
            model_name=model_name,
            template_id=config.template_id,
            template_name=template_name,
            rules_count=rules_count,
            enabled_rules_count=enabled_rules_count,
            security_score=security_score,
            last_updated=config.updated_at
        )

    def _calculate_security_score(self, config: ModelRuleConfig, all_rules: List[SecurityRule]) -> int:
        """计算安全评分。

        Args:
            config: 模型规则配置
            all_rules: 所有安全规则

        Returns:
            安全评分（0-100）
        """
        if not config.rules:
            return 0

        # 创建规则ID到规则的映射
        rule_map = {}
        for rule in all_rules:
            if hasattr(rule, 'id'):
                rule_map[rule.id] = rule
            elif isinstance(rule, dict) and 'id' in rule:
                # 处理字典类型的规则
                rule_id = rule['id']
                rule_map[rule_id] = rule

        # 获取已启用的规则
        enabled_rules = [rule for rule in config.rules if rule.enabled]
        if not enabled_rules:
            return 0

        # 计算关键规则的覆盖率
        critical_rule_types = {
            DetectionType.PROMPT_INJECTION.value,
            DetectionType.JAILBREAK.value,
            DetectionType.HARMFUL_CONTENT.value,
            DetectionType.SENSITIVE_INFO.value,
        }

        covered_types = set()
        for rule in enabled_rules:
            if rule.rule_id in rule_map:
                # 获取规则类型
                if hasattr(rule_map[rule.rule_id], 'detection_type'):
                    if hasattr(rule_map[rule.rule_id].detection_type, 'value'):
                        rule_type = rule_map[rule.rule_id].detection_type.value
                    else:
                        rule_type = str(rule_map[rule.rule_id].detection_type)
                elif isinstance(rule_map[rule.rule_id], dict) and 'detection_type' in rule_map[rule.rule_id]:
                    rule_type = rule_map[rule.rule_id]['detection_type']
                else:
                    # 如果无法确定规则类型，跳过该规则
                    continue
                if rule_type in critical_rule_types:
                    covered_types.add(rule_type)

        type_coverage = len(covered_types) / len(critical_rule_types) * 50

        # 计算规则数量得分
        rule_count_score = min(len(enabled_rules) / 20 * 50, 50)  # 最多20个规则得满分

        # 综合得分
        return int(type_coverage + rule_count_score)

    def batch_apply_template(self, model_ids: List[str], template_id: str) -> int:
        """批量应用模板到多个模型。

        Args:
            model_ids: 模型ID列表
            template_id: 模板ID

        Returns:
            成功应用的模型数量
        """
        success_count = 0
        for model_id in model_ids:
            try:
                self.apply_template_to_model(model_id, template_id)
                success_count += 1
            except Exception as e:
                logger.error(f"将模板 {template_id} 应用到模型 {model_id} 失败: {e}")
        return success_count

    def batch_toggle_rules(self, model_ids: List[str], rule_ids: List[str], enabled: bool) -> int:
        """批量启用/禁用规则。

        Args:
            model_ids: 模型ID列表
            rule_ids: 规则ID列表
            enabled: 是否启用

        Returns:
            成功更新的模型数量
        """
        success_count = 0
        for model_id in model_ids:
            try:
                config = self.get_model_rule_config(model_id)
                if not config:
                    continue

                updated = False
                for rule in config.rules:
                    if rule.rule_id in rule_ids:
                        rule.enabled = enabled
                        updated = True

                if updated:
                    self.update_model_rule_config(config)
                    success_count += 1
            except Exception as e:
                logger.error(f"为模型 {model_id} 批量{('启用' if enabled else '禁用')}规则失败: {e}")
        return success_count

    def create_template_from_model(self, model_id: str, template_id: str, template_name: str,
                                  description: str, category: str) -> RuleSetTemplate:
        """从模型配置创建模板。

        Args:
            model_id: 模型ID
            template_id: 新模板ID
            template_name: 新模板名称
            description: 新模板描述
            category: 新模板分类

        Returns:
            创建的模板
        """
        config = self.get_model_rule_config(model_id)
        if not config:
            raise ValueError(f"模型 {model_id} 的规则配置不存在")

        # 创建模板规则列表
        template_rules = []
        for rule in config.rules:
            template_rules.append({
                "rule_id": rule.rule_id,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "override_params": rule.override_params
            })

        # 创建新模板
        template = RuleSetTemplate(
            id=template_id,
            name=template_name,
            description=description,
            rules=template_rules,
            category=category
        )

        # 保存模板
        self.create_template(template)
        return template
