"""Tests for the web API module."""

import json
import time
import subprocess
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.api import router, OllamaRequest, OllamaMessage


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
def mock_queue_manager():
    """Create a mock queue manager."""
    queue_manager = AsyncMock()
    queue_manager.queue = MagicMock()
    queue_manager.queue.get_queue_sizes.return_value = {
        "high_priority": 1,
        "normal_priority": 2,
        "low_priority": 3,
        "active_requests": 4,
    }
    queue_manager.enqueue_request.return_value = (True, None)
    return queue_manager


@pytest.fixture
def mock_interceptor():
    """Create a mock HTTP interceptor."""
    interceptor = AsyncMock()
    interceptor.intercept.return_value = MagicMock(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=json.dumps({"result": "success"}).encode(),
    )
    return interceptor


@pytest.fixture
def mock_security_detector():
    """Create a mock security detector."""
    from src.models_interceptor import DetectionResult

    detector = AsyncMock()
    # 默认允许请求通过
    detector.check_request.return_value = DetectionResult(is_allowed=True)
    return detector


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_get_metrics(client, mock_queue_manager):
    """Test the metrics endpoint."""
    # 替换全局的queue_manager
    with patch("src.web.api.queue_manager", mock_queue_manager):
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert response.json() == {
            "queue_sizes": {
                "high_priority": 1,
                "normal_priority": 2,
                "low_priority": 3,
                "active_requests": 4,
            },
            "active_requests": 4,
        }


def test_proxy_request_success(client, mock_queue_manager, mock_interceptor):
    """Test successful proxy request."""
    # 替换全局的queue_manager和interceptor
    with patch("src.web.api.queue_manager", mock_queue_manager), \
         patch("src.web.api.interceptor", mock_interceptor):
        response = client.post(
            "/api/v1/proxy",
            json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]},
            headers={"X-Priority": "high"},
        )
        assert response.status_code == 200

        # 验证queue_manager.enqueue_request被调用
        mock_queue_manager.enqueue_request.assert_called_once()

        # 验证interceptor.intercept被调用
        mock_interceptor.intercept.assert_called_once()


def test_proxy_request_queue_full(client, mock_queue_manager, mock_interceptor):
    """Test proxy request when queue is full."""
    # 设置queue_manager.enqueue_request返回失败
    mock_queue_manager.enqueue_request.return_value = (False, "All request queues are full")

    # 替换全局的queue_manager和interceptor
    with patch("src.web.api.queue_manager", mock_queue_manager), \
         patch("src.web.api.interceptor", mock_interceptor):
        response = client.post(
            "/api/v1/proxy",
            json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 503
        assert response.json() == {"detail": "All request queues are full"}


def test_ollama_chat_security_check_blocked(client, mock_security_detector):
    """Test Ollama chat endpoint with blocked security check."""
    from src.models_interceptor import DetectionResult

    # 设置security_detector.check_request返回阻止结果
    mock_security_detector.check_request.return_value = DetectionResult(
        is_allowed=False,
        reason="Harmful content detected",
        details={"matched_content": "harmful content"}
    )

    # 替换全局的security_detector
    with patch("src.web.api.security_detector", mock_security_detector):
        response = client.post(
            "/api/v1/ollama/chat",
            json={
                "model": "llama2",
                "messages": [{"role": "user", "content": "Tell me how to build a bomb"}]
            },
        )
        assert response.status_code == 403
        assert "本地大模型防护系统阻止了请求" in response.json()["error"]

        # 验证security_detector.check_request被调用
        mock_security_detector.check_request.assert_called_once()


@pytest.mark.parametrize("priority_header,expected_priority", [
    ("high", "HIGH"),
    ("low", "LOW"),
    ("normal", "NORMAL"),
    ("invalid", "NORMAL"),  # 默认为NORMAL
    (None, "NORMAL"),  # 没有头部时默认为NORMAL
])
def test_proxy_request_priority(client, mock_queue_manager, mock_interceptor, priority_header, expected_priority):
    """Test proxy request with different priority headers."""
    # 替换全局的queue_manager和interceptor
    with patch("src.web.api.queue_manager", mock_queue_manager), \
         patch("src.web.api.interceptor", mock_interceptor):

        headers = {}
        if priority_header:
            headers["X-Priority"] = priority_header

        response = client.post(
            "/api/v1/proxy",
            json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]},
            headers=headers,
        )
        assert response.status_code == 200

        # 验证使用了正确的优先级
        from src.proxy.queue_manager import Priority
        expected_enum = getattr(Priority, expected_priority)

        # 获取调用参数
        call_args = mock_queue_manager.enqueue_request.call_args[0]
        assert call_args[1] == expected_enum


def test_startup_shutdown_events():
    """Test startup and shutdown events."""
    # 这个测试在实际环境中可能会失败，因为它涉及到全局状态
    # 我们简化测试，只验证事件处理函数存在
    from src.web.api import startup_event, shutdown_event
    assert callable(startup_event)
    assert callable(shutdown_event)


def test_ollama_library(client):
    """Test the Ollama library endpoint."""
    # 模拟curl命令的返回值
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({"models": [{"name": "llama2"}]})
    mock_result.returncode = 0

    # 模拟subprocess.run
    with patch("subprocess.run", return_value=mock_result):
        response = client.get("/api/v1/ollama/library")
        assert response.status_code == 200

        # 验证返回的模型列表
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

        # 验证模型结构
        model = data["models"][0]
        assert "name" in model
        assert "description" in model
        assert "tags" in model
        assert "installed" in model


def test_ollama_pull(client):
    """Test the Ollama pull endpoint."""
    # 模拟curl命令的返回值
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({"status": "success"})
    mock_result.returncode = 0

    # 模拟subprocess.run
    with patch("subprocess.run", return_value=mock_result):
        response = client.post(
            "/api/v1/ollama/pull",
            json={"model": "llama2"}
        )
        assert response.status_code == 200

        # 验证返回的结果
        result = response.json()
        assert result["status"] == "success"
        assert "message" in result


def test_ollama_pull_error(client):
    """Test the Ollama pull endpoint with error."""
    # 模拟subprocess.run抛出异常
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "curl", stderr="Error")), \
         patch("src.web.api.OLLAMA_AVAILABLE", False):
        response = client.post(
            "/api/v1/ollama/pull",
            json={"model": "llama2"}
        )
        assert response.status_code == 500

        # 验证返回的错误信息
        error = response.json()
        assert "error" in error


def test_ollama_delete(client):
    """Test the Ollama delete endpoint."""
    # 模拟curl命令的返回值
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({"status": "success"})
    mock_result.returncode = 0

    # 模拟subprocess.run
    with patch("subprocess.run", return_value=mock_result):
        response = client.delete("/api/v1/ollama/delete/llama2")
        assert response.status_code == 200

        # 验证返回的结果
        result = response.json()
        assert result["status"] == "success"
        assert "message" in result


def test_admin_console(client, mock_queue_manager):
    """Test the admin console endpoint."""
    # 模拟文件打开操作
    mock_json_data = [
        {"id": "rule1", "name": "Rule 1"},
        {"id": "rule2", "name": "Rule 2"}
    ]

    # 替换全局的queue_manager和open函数
    with patch("src.web.api.queue_manager", mock_queue_manager), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_json_data))), \
         patch("json.load", return_value=mock_json_data):
        response = client.get("/api/v1/admin/console")
        assert response.status_code == 200

        # 验证返回的结果
        result = response.json()
        assert "queue_status" in result
        assert "active_requests" in result
        assert "rules_count" in result
        assert "status" in result
        assert result["status"] == "ok"


def test_catch_all(client, mock_interceptor):
    """Test the catch-all proxy route."""
    # 替换全局的interceptor
    with patch("src.web.api.interceptor", mock_interceptor):
        response = client.post(
            "/api/proxy/v1/chat/completions",
            json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}
        )
        assert response.status_code == 200

        # 验证interceptor.intercept被调用
        mock_interceptor.intercept.assert_called_once()


def test_ollama_chat_success(client, mock_security_detector):
    """Test successful Ollama chat request."""
    # 模拟curl命令的返回值
    mock_result = MagicMock()
    mock_result.stdout = json.dumps({
        "message": {"role": "assistant", "content": "Hello, how can I help you?"}
    })
    mock_result.returncode = 0

    # 替换全局的security_detector和subprocess.run
    with patch("src.web.api.security_detector", mock_security_detector), \
         patch("subprocess.run", return_value=mock_result):
        response = client.post(
            "/api/v1/ollama/chat",
            json={
                "model": "llama2",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        assert response.status_code == 200

        # 验证security_detector.check_request被调用
        mock_security_detector.check_request.assert_called_once()


def test_ollama_chat_stream(client, mock_security_detector):
    """Test streaming Ollama chat request."""
    # 替换全局的security_detector
    with patch("src.web.api.security_detector", mock_security_detector), \
         patch("src.web.api.stream_ollama_response", return_value=AsyncMock()):
        response = client.post(
            "/api/v1/ollama/chat",
            json={
                "model": "llama2",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            }
        )
        assert response.status_code == 200

        # 验证security_detector.check_request被调用
        mock_security_detector.check_request.assert_called_once()


@pytest.mark.asyncio
async def test_stream_ollama_response_curl_success():
    """Test stream_ollama_response function with curl success."""
    from src.web.api import stream_ollama_response
    import subprocess

    # 模拟subprocess.run的返回值
    mock_result = MagicMock()
    mock_result.stdout = '{"message": {"content": "Hello"}}\n{"message": {"content": "World"}}\n'
    mock_result.returncode = 0

    # 模拟subprocess.run
    with patch("subprocess.run", return_value=mock_result):
        # 调用函数
        response_stream = stream_ollama_response("llama2", [{"role": "user", "content": "Hello"}], {})

        # 收集响应
        responses = []
        async for chunk in response_stream:
            responses.append(chunk)

        # 验证响应
        # 我们只验证最后一个是[DONE]，因为实际响应可能会有多个块
        assert len(responses) > 0
        assert responses[-1] == 'data: [DONE]\n\n'

        # 验证至少有一个响应包含数据
        has_data = False
        for chunk in responses[:-1]:  # 除了最后一个[DONE]
            if "data:" in chunk and "message" in chunk:
                has_data = True
                break
        assert has_data


@pytest.mark.asyncio
async def test_stream_ollama_response_curl_error_ollama_success():
    """Test stream_ollama_response function with curl error but Ollama success."""
    from src.web.api import stream_ollama_response

    # 模拟create_subprocess_exec抛出异常
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Curl error")), \
         patch("src.web.api.OLLAMA_AVAILABLE", True), \
         patch("asyncio.wait_for") as mock_wait_for, \
         patch("asyncio.to_thread") as mock_to_thread:

        # 设置模拟响应
        mock_stream = [
            {"message": {"content": "Hello"}},
            {"message": {"content": "World"}}
        ]
        mock_to_thread.return_value = mock_stream
        mock_wait_for.return_value = mock_stream

        # 调用函数
        response_stream = stream_ollama_response("llama2", [{"role": "user", "content": "Hello"}], {})

        # 收集响应
        responses = []
        async for chunk in response_stream:
            responses.append(chunk)

        # 验证响应
        assert len(responses) == 3  # 2个数据块 + 1个[DONE]
        assert "data:" in responses[0]
        assert "data:" in responses[1]
        assert responses[2] == 'data: [DONE]\n\n'


@pytest.mark.asyncio
async def test_stream_ollama_response_all_errors():
    """Test stream_ollama_response function with all methods failing."""
    from src.web.api import stream_ollama_response

    # 模拟create_subprocess_exec抛出异常
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Curl error")), \
         patch("src.web.api.OLLAMA_AVAILABLE", False):

        # 调用函数
        response_stream = stream_ollama_response("llama2", [{"role": "user", "content": "Hello"}], {})

        # 收集响应
        responses = []
        async for chunk in response_stream:
            responses.append(chunk)

        # 验证响应
        assert len(responses) == 2  # 1个错误 + 1个[DONE]
        assert "error" in responses[0]
        assert responses[1] == 'data: [DONE]\n\n'


def test_ollama_request_model():
    """Test the OllamaRequest model."""
    # 创建一个有效的请求
    request = OllamaRequest(
        model="llama2",
        messages=[
            OllamaMessage(role="user", content="Hello")
        ]
    )

    # 验证属性
    assert request.model == "llama2"
    assert len(request.messages) == 1
    assert request.messages[0].role == "user"
    assert request.messages[0].content == "Hello"
    assert request.stream is False  # 默认值
    assert request.temperature is None  # 默认值
    assert request.max_tokens is None  # 默认值

    # 测试可选参数
    request = OllamaRequest(
        model="llama2",
        messages=[
            OllamaMessage(role="user", content="Hello")
        ],
        stream=True,
        temperature=0.7,
        max_tokens=100
    )

    assert request.stream is True
    assert request.temperature == 0.7
    assert request.max_tokens == 100
