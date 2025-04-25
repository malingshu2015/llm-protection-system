"""Tests for the model rules API module."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.models_rules import ModelRuleConfig, ModelRuleAssociation, RuleSetTemplate, ModelRuleSummary
from src.web.model_rules_api import router


@pytest.fixture
def app():
    """Create a FastAPI app with the API router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_model_rule_manager():
    """Create a mock model rule manager."""
    manager = MagicMock()

    # 设置get_all_model_rule_configs的返回值
    manager.get_all_model_rule_configs.return_value = [
        ModelRuleConfig(
            model_id="model1",
            template_id="template1",
            rules=[
                ModelRuleAssociation(
                    id="model1_rule1",
                    model_id="model1",
                    rule_id="rule1",
                    enabled=True,
                    priority=10
                )
            ]
        )
    ]

    # 设置get_model_rule_config的返回值
    manager.get_model_rule_config.return_value = ModelRuleConfig(
        model_id="model1",
        template_id="template1",
        rules=[
            ModelRuleAssociation(
                id="model1_rule1",
                model_id="model1",
                rule_id="rule1",
                enabled=True,
                priority=10
            )
        ]
    )

    # 设置get_all_templates的返回值
    manager.get_all_templates.return_value = [
        RuleSetTemplate(
            id="template1",
            name="Template 1",
            description="Test template",
            rules=[{"rule_id": "rule1", "enabled": True, "priority": 10}],
            category="test"
        )
    ]

    # 设置get_template的返回值
    manager.get_template.return_value = RuleSetTemplate(
        id="template1",
        name="Template 1",
        description="Test template",
        rules=[{"rule_id": "rule1", "enabled": True, "priority": 10}],
        category="test"
    )

    # 设置get_model_rule_summary的返回值
    manager.get_model_rule_summary.return_value = ModelRuleSummary(
        model_id="model1",
        model_name="Model 1",
        template_name="Template 1",
        rules_count=1,
        enabled_rules_count=1,
        security_score=80,
        last_updated=datetime.now()
    )

    # 设置detect_rule_conflicts的返回值
    manager.detect_rule_conflicts.return_value = []

    # 设置create_model_rule_config的返回值
    manager.create_model_rule_config.return_value = ModelRuleConfig(
        model_id="model1",
        template_id="template1",
        rules=[
            ModelRuleAssociation(
                id="model1_rule1",
                model_id="model1",
                rule_id="rule1",
                enabled=True,
                priority=10
            )
        ]
    )

    # 设置update_model_rule_config的返回值
    manager.update_model_rule_config.return_value = ModelRuleConfig(
        model_id="model1",
        template_id="template1",
        rules=[
            ModelRuleAssociation(
                id="model1_rule1",
                model_id="model1",
                rule_id="rule1",
                enabled=True,
                priority=10
            )
        ]
    )

    # 设置delete_model_rule_config的返回值
    manager.delete_model_rule_config.return_value = True

    # 设置create_template的返回值
    manager.create_template.return_value = RuleSetTemplate(
        id="template1",
        name="Template 1",
        description="Test template",
        rules=[{"rule_id": "rule1", "enabled": True, "priority": 10}],
        category="test"
    )

    # 设置update_template的返回值
    manager.update_template.return_value = RuleSetTemplate(
        id="template1",
        name="Template 1",
        description="Test template",
        rules=[{"rule_id": "rule1", "enabled": True, "priority": 10}],
        category="test"
    )

    # 设置delete_template的返回值
    manager.delete_template.return_value = True

    # 设置apply_template_to_model的返回值
    manager.apply_template_to_model.return_value = ModelRuleConfig(
        model_id="model1",
        template_id="template1",
        rules=[
            ModelRuleAssociation(
                id="model1_rule1",
                model_id="model1",
                rule_id="rule1",
                enabled=True,
                priority=10
            )
        ]
    )

    return manager


@pytest.fixture
def mock_get_rules():
    """Create a mock get_rules function."""
    async def mock_get_rules_func():
        return [
            {
                "id": "rule1",
                "name": "Rule 1",
                "description": "Test rule",
                "detection_type": "prompt_injection",
                "severity": "high",
                "patterns": ["pattern1"],
                "enabled": True
            }
        ]

    return mock_get_rules_func


def test_get_model_rule_summaries(client, mock_model_rule_manager, mock_get_rules):
    """Test getting model rule summaries."""
    # 模拟请求并返回模拟数据
    # 替换全局的model_rule_manager和get_rules
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager), \
         patch("src.web.model_rules_api.get_rules", mock_get_rules), \
         patch("requests.get") as mock_requests_get:

        # 模拟请求响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "model1", "model": "model1"},
                {"name": "model2", "model": "model2"}
            ]
        }
        mock_requests_get.return_value = mock_response

        response = client.get("/api/v1/model-rules")
        assert response.status_code == 200

        # 验证返回的摘要列表
        summaries = response.json()
        assert len(summaries) >= 1

        # 验证model_rule_manager.get_all_model_rule_configs被调用
        mock_model_rule_manager.get_all_model_rule_configs.assert_called_once()


def test_get_model_rule_config(client, mock_model_rule_manager):
    """Test getting a model rule configuration."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.get("/api/v1/model-rules/model1")
        assert response.status_code == 200

        # 验证返回的配置
        config = response.json()
        assert config["model_id"] == "model1"
        assert config["template_id"] == "template1"
        assert len(config["rules"]) == 1

        # 验证model_rule_manager.get_model_rule_config被调用
        mock_model_rule_manager.get_model_rule_config.assert_called_once_with("model1")


def test_get_model_rule_config_not_found(client, mock_model_rule_manager):
    """Test getting a non-existent model rule configuration."""
    # 设置get_model_rule_config返回None
    mock_model_rule_manager.get_model_rule_config.return_value = None

    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.get("/api/v1/model-rules/nonexistent")
        assert response.status_code == 404

        # 验证错误消息
        error = response.json()
        assert "不存在" in error["detail"]


def test_create_model_rule_config(client, mock_model_rule_manager):
    """Test creating a model rule configuration."""
    # 设置get_model_rule_config返回None（表示不存在）
    mock_model_rule_manager.get_model_rule_config.return_value = None

    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.post(
            "/api/v1/model-rules/model1",
            json={
                "template_id": "template1",
                "rules": [
                    {
                        "rule_id": "rule1",
                        "enabled": True,
                        "priority": 10
                    }
                ]
            }
        )
        assert response.status_code == 200

        # 验证返回的配置
        config = response.json()
        assert config["model_id"] == "model1"
        assert config["template_id"] == "template1"

        # 验证model_rule_manager.create_model_rule_config被调用
        mock_model_rule_manager.create_model_rule_config.assert_called_once()


def test_update_model_rule_config(client, mock_model_rule_manager):
    """Test updating a model rule configuration."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.post(
            "/api/v1/model-rules/model1",
            json={
                "template_id": "template1",
                "rules": [
                    {
                        "rule_id": "rule1",
                        "enabled": True,
                        "priority": 10
                    }
                ]
            }
        )
        assert response.status_code == 200

        # 验证返回的配置
        config = response.json()
        assert config["model_id"] == "model1"
        assert config["template_id"] == "template1"

        # 验证model_rule_manager.update_model_rule_config被调用
        mock_model_rule_manager.update_model_rule_config.assert_called_once()


def test_delete_model_rule_config(client, mock_model_rule_manager):
    """Test deleting a model rule configuration."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.delete("/api/v1/model-rules/model1")
        assert response.status_code == 200

        # 验证返回的结果
        result = response.json()
        assert result["success"] is True

        # 验证model_rule_manager.delete_model_rule_config被调用
        mock_model_rule_manager.delete_model_rule_config.assert_called_once_with("model1")


def test_delete_model_rule_config_not_found(client, mock_model_rule_manager):
    """Test deleting a non-existent model rule configuration."""
    # 设置delete_model_rule_config返回False
    mock_model_rule_manager.delete_model_rule_config.return_value = False

    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.delete("/api/v1/model-rules/nonexistent")
        assert response.status_code == 404

        # 验证错误消息
        error = response.json()
        assert "不存在" in error["detail"]


def test_get_model_rule_conflicts(client, mock_model_rule_manager):
    """Test getting model rule conflicts."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.get("/api/v1/model-rules/model1/conflicts")
        assert response.status_code == 200

        # 验证返回的冲突列表
        conflicts = response.json()
        assert isinstance(conflicts, list)

        # 验证model_rule_manager.detect_rule_conflicts被调用
        mock_model_rule_manager.detect_rule_conflicts.assert_called_once_with("model1")


def test_get_rule_templates(client, mock_model_rule_manager):
    """Test getting rule templates."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.get("/api/v1/rule-templates")
        assert response.status_code == 200

        # 验证返回的模板列表
        templates = response.json()
        assert len(templates) == 1
        assert templates[0]["id"] == "template1"

        # 验证model_rule_manager.get_all_templates被调用
        mock_model_rule_manager.get_all_templates.assert_called_once()


def test_get_rule_template(client, mock_model_rule_manager):
    """Test getting a rule template."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.get("/api/v1/rule-templates/template1")
        assert response.status_code == 200

        # 验证返回的模板
        template = response.json()
        assert template["id"] == "template1"
        assert template["name"] == "Template 1"

        # 验证model_rule_manager.get_template被调用
        mock_model_rule_manager.get_template.assert_called_once_with("template1")


def test_get_rule_template_not_found(client, mock_model_rule_manager):
    """Test getting a non-existent rule template."""
    # 设置get_template返回None
    mock_model_rule_manager.get_template.return_value = None

    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.get("/api/v1/rule-templates/nonexistent")
        assert response.status_code == 404

        # 验证错误消息
        error = response.json()
        assert "不存在" in error["detail"]


def test_create_rule_template(client, mock_model_rule_manager):
    """Test creating a rule template."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.post(
            "/api/v1/rule-templates",
            json={
                "name": "Template 1",
                "description": "Test template",
                "rules": [{"rule_id": "rule1", "enabled": True, "priority": 10}],
                "category": "test"
            }
        )
        assert response.status_code == 200

        # 验证返回的模板
        template = response.json()
        assert template["name"] == "Template 1"
        assert template["description"] == "Test template"

        # 验证model_rule_manager.create_template被调用
        mock_model_rule_manager.create_template.assert_called_once()


def test_update_rule_template(client, mock_model_rule_manager):
    """Test updating a rule template."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.put(
            "/api/v1/rule-templates/template1",
            json={
                "name": "Updated Template",
                "description": "Updated description",
                "rules": [{"rule_id": "rule1", "enabled": True, "priority": 10}],
                "category": "test"
            }
        )
        assert response.status_code == 200

        # 验证返回的模板
        template = response.json()
        assert template["id"] == "template1"

        # 验证model_rule_manager.update_template被调用
        mock_model_rule_manager.update_template.assert_called_once()


def test_update_rule_template_not_found(client, mock_model_rule_manager):
    """Test updating a non-existent rule template."""
    # 设置get_template返回None
    mock_model_rule_manager.get_template.return_value = None

    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.put(
            "/api/v1/rule-templates/nonexistent",
            json={
                "name": "Updated Template",
                "description": "Updated description",
                "rules": [{"rule_id": "rule1", "enabled": True, "priority": 10}],
                "category": "test"
            }
        )
        assert response.status_code == 404

        # 验证错误消息
        error = response.json()
        assert "不存在" in error["detail"]


def test_delete_rule_template(client, mock_model_rule_manager):
    """Test deleting a rule template."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.delete("/api/v1/rule-templates/template1")
        assert response.status_code == 200

        # 验证返回的结果
        result = response.json()
        assert result["success"] is True

        # 验证model_rule_manager.delete_template被调用
        mock_model_rule_manager.delete_template.assert_called_once_with("template1")


def test_delete_rule_template_not_found(client, mock_model_rule_manager):
    """Test deleting a non-existent rule template."""
    # 设置delete_template返回False
    mock_model_rule_manager.delete_template.return_value = False

    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.delete("/api/v1/rule-templates/nonexistent")
        assert response.status_code == 404

        # 验证错误消息
        error = response.json()
        assert "不存在" in error["detail"]


def test_apply_template_to_model(client, mock_model_rule_manager):
    """Test applying a template to a model."""
    # 替换全局的model_rule_manager
    with patch("src.web.model_rules_api.model_rule_manager", mock_model_rule_manager):
        response = client.post("/api/v1/models/model1/apply-template/template1")
        assert response.status_code == 200

        # 验证返回的配置
        config = response.json()
        assert config["model_id"] == "model1"
        assert config["template_id"] == "template1"

        # 验证model_rule_manager.apply_template_to_model被调用
        mock_model_rule_manager.apply_template_to_model.assert_called_once_with("model1", "template1")
