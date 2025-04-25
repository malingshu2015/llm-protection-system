"""Tests for the HTTP interceptor module."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import Request, Response

from src.models_interceptor import InterceptedRequest, InterceptedResponse, DetectionResult
from src.security.detector import SecurityDetector
from src.proxy.interceptor import HTTPInterceptor


@pytest.fixture
def mock_security_detector():
    """Create a mock security detector."""
    detector = AsyncMock()

    # 设置默认返回值
    allowed_result = DetectionResult(is_allowed=True)
    detector.check_request.return_value = allowed_result
    detector.check_response.return_value = allowed_result

    return detector


@pytest_asyncio.fixture
async def interceptor(mock_security_detector):
    """Create an HTTP interceptor with a mock security detector."""
    # 在拦截器中，SecurityDetector是从src.security.detector导入的
    with patch.object(SecurityDetector, "__new__", return_value=mock_security_detector):
        # 模拟客户端会话
        with patch("aiohttp.ClientSession", new=MagicMock()):
            interceptor = HTTPInterceptor()
            yield interceptor


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url = "https://api.openai.com/v1/chat/completions"
    request.headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-test",
    }
    request.query_params = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    # 模拟请求体
    request_body = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, world!"}
        ]
    }
    request.body = AsyncMock(return_value=json.dumps(request_body).encode())

    return request


@pytest.mark.asyncio
async def test_parse_request(interceptor, mock_request):
    """Test parsing a request."""
    # 解析请求
    result = await interceptor._parse_request(mock_request)

    # 验证结果
    assert isinstance(result, InterceptedRequest)
    assert result.method == "POST"
    assert result.url == "https://api.openai.com/v1/chat/completions"
    assert result.headers["Content-Type"] == "application/json"
    assert result.body["model"] == "gpt-3.5-turbo"
    assert result.provider == "openai"


@pytest.mark.asyncio
async def test_get_provider_from_model(interceptor):
    """Test determining the provider from a model name."""
    # OpenAI models
    assert interceptor._get_provider_from_model("gpt-3.5-turbo") == "openai"
    assert interceptor._get_provider_from_model("gpt-4") == "openai"

    # Anthropic models
    assert interceptor._get_provider_from_model("claude-2") == "anthropic"

    # Ollama models
    assert interceptor._get_provider_from_model("llama2") == "ollama"
    assert interceptor._get_provider_from_model("mistral") == "ollama"

    # Unknown model
    assert interceptor._get_provider_from_model("unknown-model") is None
    assert interceptor._get_provider_from_model("") is None
    assert interceptor._get_provider_from_model(None) is None


@pytest.mark.asyncio
async def test_create_response(interceptor):
    """Test creating a response from an intercepted response."""
    # 创建一个拦截响应
    intercepted_response = InterceptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?",
                    }
                }
            ]
        }
    )

    # 创建响应
    response = await interceptor._create_response(intercepted_response)

    # 验证结果
    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

    # 验证响应体
    response_body = json.loads(response.body.decode())
    assert response_body["id"] == "chatcmpl-123"
    assert response_body["choices"][0]["message"]["content"] == "Hello! How can I help you today?"


@pytest.mark.asyncio
async def test_create_blocked_response(interceptor):
    """Test creating a blocked response."""
    # 创建被阻止的响应
    response = await interceptor._create_blocked_response("Harmful content detected", 403)

    # 验证结果
    assert isinstance(response, Response)
    assert response.status_code == 403
    assert response.headers["Content-Type"] == "application/json"

    # 验证响应体
    response_body = json.loads(response.body.decode())
    assert "error" in response_body
    assert "Harmful content detected" in response_body["error"]["message"]
    assert response_body["error"]["type"] == "security_violation"


@pytest.mark.asyncio
async def test_create_error_response(interceptor):
    """Test creating an error response."""
    # 创建错误响应
    response = await interceptor._create_error_response("Internal server error")

    # 验证结果
    assert isinstance(response, Response)
    assert response.status_code == 500
    assert response.headers["Content-Type"] == "application/json"

    # 验证响应体
    response_body = json.loads(response.body.decode())
    assert "error" in response_body
    assert "Internal server error" in response_body["error"]["message"]
    assert response_body["error"]["type"] == "internal_error"


@pytest.mark.asyncio
async def test_intercept_allowed_request(interceptor, mock_request, mock_security_detector):
    """Test intercepting an allowed request."""
    # 模拟转发请求的结果
    mock_response = InterceptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "Hello!"}}]
        }
    )

    # 模拟 _forward_request 方法
    with patch.object(interceptor, "_forward_request", return_value=mock_response):
        # 拦截请求
        response = await interceptor.intercept(mock_request)

        # 验证结果
        assert isinstance(response, Response)
        assert response.status_code == 200

        # 验证安全检查被调用
        mock_security_detector.check_request.assert_called_once()
        mock_security_detector.check_response.assert_called_once()


@pytest.mark.asyncio
async def test_intercept_blocked_request(interceptor, mock_request, mock_security_detector):
    """Test intercepting a blocked request."""
    # 设置安全检查结果为阻止
    blocked_result = DetectionResult(
        is_allowed=False,
        reason="Harmful content detected",
        status_code=403
    )
    mock_security_detector.check_request.return_value = blocked_result

    # 拦截请求
    response = await interceptor.intercept(mock_request)

    # 验证结果
    assert isinstance(response, Response)
    assert response.status_code == 403

    # 验证安全检查被调用
    mock_security_detector.check_request.assert_called_once()
    # 验证请求未被转发
    assert not mock_security_detector.check_response.called


@pytest.mark.asyncio
async def test_intercept_blocked_response(interceptor, mock_request, mock_security_detector):
    """Test intercepting a request with a blocked response."""
    # 设置响应安全检查结果为阻止
    blocked_result = DetectionResult(
        is_allowed=False,
        reason="Harmful content in response",
        status_code=403
    )
    mock_security_detector.check_response.return_value = blocked_result

    # 模拟转发请求的结果
    mock_response = InterceptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "Harmful content"}}]
        }
    )

    # 模拟 _forward_request 方法
    with patch.object(interceptor, "_forward_request", return_value=mock_response):
        # 拦截请求
        response = await interceptor.intercept(mock_request)

        # 验证结果
        assert isinstance(response, Response)
        assert response.status_code == 403

        # 验证安全检查被调用
        mock_security_detector.check_request.assert_called_once()
        mock_security_detector.check_response.assert_called_once()


@pytest.mark.asyncio
async def test_intercept_error_handling(interceptor, mock_request):
    """Test error handling during interception."""
    # 模拟 _parse_request 方法抛出异常
    with patch.object(interceptor, "_parse_request", side_effect=Exception("Test error")):
        # 拦截请求
        response = await interceptor.intercept(mock_request)

        # 验证结果
        assert isinstance(response, Response)
        assert response.status_code == 500

        # 验证响应体
        response_body = json.loads(response.body.decode())
        assert "error" in response_body
        assert "Test error" in response_body["error"]["message"]
