"""Configuration module for the LLM Security Firewall."""

import os
from typing import Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="DEBUG")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_path: Optional[str] = Field(default=None)

    model_config = {
        "env_prefix": "LOG_",
        "extra": "ignore"
    }


class ProxyConfig(BaseSettings):
    """Proxy service configuration."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    timeout: int = Field(default=30)
    max_concurrent_requests: int = Field(default=100)
    request_queue_size: int = Field(default=1000)

    model_config = {
        "env_prefix": "PROXY_",
        "extra": "ignore"
    }


class SecurityConfig(BaseSettings):
    """Security detection configuration."""

    prompt_injection_rules_path: str = Field(
        default="rules/prompt_injection.json"
    )
    sensitive_info_patterns_path: str = Field(
        default="rules/sensitive_info.json"
    )
    harmful_content_rules_path: str = Field(
        default="rules/harmful_content.json"
    )
    compliance_rules_path: str = Field(
        default="rules/compliance.json"
    )
    jailbreak_rules_path: str = Field(
        default="rules/jailbreak.json"
    )
    max_prompt_length: int = Field(default=4096)
    max_response_length: int = Field(default=8192)

    model_config = {
        "env_prefix": "SECURITY_",
        "extra": "ignore"
    }


class RulesConfig(BaseSettings):
    """Rule engine configuration."""

    rules_path: str = Field(default="rules")
    rules_refresh_interval: int = Field(default=60)
    rules_cache_size: int = Field(default=1000)

    model_config = {
        "env_prefix": "RULES_",
        "extra": "ignore"
    }


class MonitorConfig(BaseSettings):
    """Resource monitoring configuration."""

    metrics_interval: int = Field(default=10)
    prometheus_port: int = Field(default=9090)
    alert_thresholds: Dict[str, float] = Field(
        default={
            "cpu_usage": 80.0,
            "memory_usage": 80.0,
            "request_latency": 1000.0,
        }
    )

    model_config = {
        "env_prefix": "MONITOR_",
        "extra": "ignore"
    }


class AuditConfig(BaseSettings):
    """Audit logging configuration."""

    audit_log_path: str = Field(default="logs/audit.log")
    audit_log_retention: int = Field(default=30)
    audit_log_format: str = Field(default="json")

    model_config = {
        "env_prefix": "AUDIT_",
        "extra": "ignore"
    }


class WebConfig(BaseSettings):
    """Web interface configuration."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)
    secret_key: str = Field(default_factory=lambda: os.urandom(24).hex())
    token_expire_minutes: int = Field(default=60)

    model_config = {
        "env_prefix": "WEB_",
        "extra": "ignore"
    }


class Settings(BaseSettings):
    """Global application settings."""

    app_name: str = Field(default="本地大模型防护系统")
    environment: str = Field(default="production")
    debug: bool = Field(default=False)
    data_dir: str = Field(default="data")

    # Module configurations
    logging: LoggingConfig = LoggingConfig()
    proxy: ProxyConfig = ProxyConfig()
    security: SecurityConfig = SecurityConfig()
    rules: RulesConfig = RulesConfig()
    monitor: MonitorConfig = MonitorConfig()
    audit: AuditConfig = AuditConfig()
    web: WebConfig = WebConfig()

    # LLM provider configurations
    llm_providers: Dict[str, Dict[str, str]] = Field(
        default={
            "openai": {
                "api_base": "https://api.openai.com/v1",
                "timeout": "30",
            },
            "anthropic": {
                "api_base": "https://api.anthropic.com",
                "timeout": "30",
            },
            "ollama": {
                "api_base": "http://localhost:11434/api",
                "timeout": "30",
            },
        }
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Create global settings instance
settings = Settings()
