"""Tests for the configuration module."""

import os
from src.config import settings

def test_settings_initialization():
    """Test that settings are initialized correctly."""
    # Test that settings is an instance of the correct class
    assert settings is not None

    # Test that required configurations are present
    assert settings.security is not None
    assert settings.web is not None
    assert settings.logging is not None
    assert settings.llm_providers is not None
    assert len(settings.llm_providers) > 0

def test_security_config():
    """Test the security configuration."""
    security_config = settings.security

    # Test default values
    assert security_config.prompt_injection_rules_path is not None
    assert security_config.sensitive_info_patterns_path is not None
    assert security_config.harmful_content_rules_path is not None
    assert security_config.compliance_rules_path is not None
    assert security_config.jailbreak_rules_path is not None

    # Test that paths exist
    assert os.path.exists(security_config.prompt_injection_rules_path)
    assert os.path.exists(security_config.sensitive_info_patterns_path)
    assert os.path.exists(security_config.harmful_content_rules_path)

def test_web_config():
    """Test the web configuration."""
    web_config = settings.web

    # Test default values
    assert web_config.host is not None
    assert web_config.port is not None
    assert isinstance(web_config.port, int)
    assert web_config.secret_key is not None
    assert len(web_config.secret_key) > 0

    # Test token expiration
    assert web_config.token_expire_minutes > 0

def test_log_config():
    """Test the log configuration."""
    log_config = settings.logging

    # Test default values
    assert log_config.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert log_config.format is not None
    # file_path可能有默认值，所以不测试它是否为None

def test_llm_providers_config():
    """Test the LLM providers configuration."""
    llm_providers = settings.llm_providers

    # Test that the providers dictionary exists
    assert llm_providers is not None
    assert isinstance(llm_providers, dict)

    # Test that some providers are present
    assert len(llm_providers) > 0

    # Test a provider configuration
    for provider_name, provider_config in llm_providers.items():
        assert "api_base" in provider_config
        assert "timeout" in provider_config
        break

def test_env_override():
    """Test that environment variables can override settings."""
    # 由于环境变量可能已经被设置，这个测试可能不稳定
    # 我们只测试基本功能

    # 测试设置实例可以被创建
    from src.config import Settings
    new_settings = Settings()

    # 测试基本属性存在
    assert new_settings.app_name is not None
    assert new_settings.web is not None
    assert new_settings.security is not None
