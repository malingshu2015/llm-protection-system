"""Tests for the models module."""

import pytest
from src.models import (
    DetectionType,
    Severity,
    DetectionResult,
    SecurityRule,
    InterceptedRequest,
    InterceptedResponse
)

def test_detection_type_enum():
    """Test the DetectionType enum."""
    # Test that all expected values are present
    assert DetectionType.PROMPT_INJECTION.value == "prompt_injection"
    assert DetectionType.SENSITIVE_INFO.value == "sensitive_info"
    assert DetectionType.HARMFUL_CONTENT.value == "harmful_content"
    assert DetectionType.JAILBREAK.value == "jailbreak"
    assert DetectionType.COMPLIANCE_VIOLATION.value == "compliance_violation"
    assert DetectionType.CUSTOM.value == "custom"

def test_severity_enum():
    """Test the Severity enum."""
    # Test that all expected values are present
    assert Severity.LOW.value == "low"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.HIGH.value == "high"
    assert Severity.CRITICAL.value == "critical"

    # 枚举值不能直接比较大小，所以我们不测试比较操作

def test_detection_result():
    """Test the DetectionResult class."""
    # Create a detection result
    result = DetectionResult(
        is_allowed=False,
        detection_type=DetectionType.PROMPT_INJECTION,
        severity=Severity.HIGH,
        reason="Contains prompt injection attempt",
        details={"rule_id": "test-rule-1", "matched_content": "malicious content"}
    )

    # Test that the attributes are set correctly
    assert result.is_allowed is False
    assert result.detection_type == DetectionType.PROMPT_INJECTION
    assert result.severity == Severity.HIGH
    assert result.reason == "Contains prompt injection attempt"
    assert "rule_id" in result.details
    assert result.details["rule_id"] == "test-rule-1"
    assert "matched_content" in result.details
    assert result.details["matched_content"] == "malicious content"

    # Test model_dump method (替代to_dict)
    result_dict = result.model_dump()
    assert result_dict["is_allowed"] is False
    assert result_dict["detection_type"] == "prompt_injection"
    assert result_dict["severity"] == "high"
    assert result_dict["reason"] == "Contains prompt injection attempt"
    assert "rule_id" in result_dict["details"]

def test_security_rule():
    """Test the SecurityRule class."""
    # Create a security rule
    rule = SecurityRule(
        id="test-rule-2",
        name="Test Rule",
        description="A test security rule",
        detection_type=DetectionType.HARMFUL_CONTENT,
        severity=Severity.MEDIUM,
        patterns=[r"harmful\s+content"],
        enabled=True
    )

    # Test that the attributes are set correctly
    assert rule.id == "test-rule-2"
    assert rule.name == "Test Rule"
    assert rule.description == "A test security rule"
    assert rule.detection_type == DetectionType.HARMFUL_CONTENT
    assert rule.severity == Severity.MEDIUM
    assert len(rule.patterns) == 1
    assert rule.patterns[0] == r"harmful\s+content"
    assert rule.enabled is True

    # Test model_dump method (替代to_dict)
    rule_dict = rule.model_dump()
    assert rule_dict["id"] == "test-rule-2"
    assert rule_dict["name"] == "Test Rule"
    assert rule_dict["description"] == "A test security rule"
    assert rule_dict["detection_type"] == "harmful_content"
    assert rule_dict["severity"] == "medium"
    assert rule_dict["patterns"] == [r"harmful\s+content"]
    assert rule_dict["enabled"] is True

def test_intercepted_request():
    """Test the InterceptedRequest class."""
    # Create an intercepted request
    request = InterceptedRequest(
        method="POST",
        url="https://api.example.com/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        body={
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, world!"}
            ]
        }
    )

    # Test that the attributes are set correctly
    assert request.method == "POST"
    assert request.url == "https://api.example.com/v1/chat/completions"
    assert request.headers == {"Content-Type": "application/json"}
    assert request.body["model"] == "gpt-3.5-turbo"
    assert len(request.body["messages"]) == 1
    assert request.body["messages"][0]["role"] == "user"
    assert request.body["messages"][0]["content"] == "Hello, world!"

    # Test model_dump method (替代to_dict)
    request_dict = request.model_dump()
    assert request_dict["method"] == "POST"
    assert request_dict["url"] == "https://api.example.com/v1/chat/completions"
    assert request_dict["headers"] == {"Content-Type": "application/json"}
    assert request_dict["body"]["model"] == "gpt-3.5-turbo"

def test_intercepted_response():
    """Test the InterceptedResponse class."""
    # Create an intercepted response
    response = InterceptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677858242,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?",
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": 13,
                "completion_tokens": 12,
                "total_tokens": 25,
            },
        }
    )

    # Test that the attributes are set correctly
    assert response.status_code == 200
    assert response.headers == {"Content-Type": "application/json"}
    assert response.body["id"] == "chatcmpl-123"
    assert response.body["model"] == "gpt-3.5-turbo-0613"
    assert len(response.body["choices"]) == 1
    assert response.body["choices"][0]["message"]["role"] == "assistant"
    assert response.body["choices"][0]["message"]["content"] == "Hello! How can I help you today?"

    # Test model_dump method (替代to_dict)
    response_dict = response.model_dump()
    assert response_dict["status_code"] == 200
    assert response_dict["headers"] == {"Content-Type": "application/json"}
    assert response_dict["body"]["id"] == "chatcmpl-123"
