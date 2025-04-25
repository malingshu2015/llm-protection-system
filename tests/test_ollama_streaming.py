"""Test Ollama streaming functionality."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.web.api import app, stream_ollama_response


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_ollama_chat_stream(client):
    """Test streaming Ollama chat request."""
    # 模拟流式响应
    async def mock_stream_response(*args, **kwargs):
        """Mock streaming response."""
        yield "data: {\"message\": {\"role\": \"assistant\", \"content\": \"Hello\"}}\n\n"
        yield "data: {\"message\": {\"role\": \"assistant\", \"content\": \", world!\"}}\n\n"
        yield "data: [DONE]\n\n"

    # 替换stream_ollama_response函数
    with patch("src.web.api.stream_ollama_response", return_value=mock_stream_response()):
        response = client.post(
            "/api/v1/ollama/chat",
            json={
                "model": "llama2",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            },
            stream=True
        )
        
        assert response.status_code == 200
        
        # 收集流式响应
        content = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: ") and not line_str.endswith("[DONE]"):
                    data = json.loads(line_str[6:])  # 去掉 "data: " 前缀
                    if "message" in data and "content" in data["message"]:
                        content += data["message"]["content"]
        
        assert content == "Hello, world!"


@pytest.mark.asyncio
async def test_stream_ollama_response():
    """Test stream_ollama_response function."""
    # 模拟subprocess.create_subprocess_exec
    mock_process = AsyncMock()
    mock_process.stdout.readline = AsyncMock()
    
    # 设置readline的返回值序列
    mock_process.stdout.readline.side_effect = [
        b'{"message": {"role": "assistant", "content": "Hello"}}\n',
        b'{"message": {"role": "assistant", "content": ", world!"}}\n',
        b'{"done": true}\n',
        b''  # 空行表示结束
    ]
    
    mock_process.wait = AsyncMock()
    
    # 模拟create_subprocess_exec
    mock_create_subprocess = AsyncMock(return_value=mock_process)
    
    # 使用patch装饰器替换create_subprocess_exec
    with patch("asyncio.create_subprocess_exec", mock_create_subprocess):
        # 调用函数
        responses = []
        async for response in stream_ollama_response("llama2", [{"role": "user", "content": "Hello"}], {}):
            responses.append(response)
        
        # 验证结果
        assert len(responses) >= 3  # 至少有3个响应（2个内容块 + 1个DONE）
        assert all(r.startswith("data: ") for r in responses)  # 所有响应都以"data: "开头
        assert responses[-1] == "data: [DONE]\n\n"  # 最后一个响应是DONE


@pytest.mark.asyncio
async def test_stream_ollama_response_with_invalid_json():
    """Test stream_ollama_response function with invalid JSON."""
    # 模拟subprocess.create_subprocess_exec
    mock_process = AsyncMock()
    mock_process.stdout.readline = AsyncMock()
    
    # 设置readline的返回值序列，包含一个无效的JSON
    mock_process.stdout.readline.side_effect = [
        b'{"message": {"role": "assistant", "content": "Hello"}}\n',
        b'Invalid JSON\n',  # 无效的JSON
        b'{"message": {"role": "assistant", "content": ", world!"}}\n',
        b'{"done": true}\n',
        b''  # 空行表示结束
    ]
    
    mock_process.wait = AsyncMock()
    
    # 模拟create_subprocess_exec
    mock_create_subprocess = AsyncMock(return_value=mock_process)
    
    # 使用patch装饰器替换create_subprocess_exec
    with patch("asyncio.create_subprocess_exec", mock_create_subprocess):
        # 调用函数
        responses = []
        async for response in stream_ollama_response("llama2", [{"role": "user", "content": "Hello"}], {}):
            responses.append(response)
        
        # 验证结果
        assert len(responses) >= 2  # 至少有2个有效响应（1个内容块 + 1个DONE）
        assert all(r.startswith("data: ") for r in responses)  # 所有响应都以"data: "开头
        assert responses[-1] == "data: [DONE]\n\n"  # 最后一个响应是DONE


def test_ollama_chat_non_stream(client):
    """Test non-streaming Ollama chat request."""
    # 模拟curl命令的返回值，包含多行JSON
    mock_result = MagicMock()
    mock_result.stdout = (
        '{"message": {"role": "assistant", "content": "Hello"}}\n'
        '{"message": {"role": "assistant", "content": ", world!"}}\n'
        '{"done": true}\n'
    )
    mock_result.returncode = 0
    
    # 替换subprocess.run
    with patch("subprocess.run", return_value=mock_result):
        response = client.post(
            "/api/v1/ollama/chat",
            json={
                "model": "llama2",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        
        assert response.status_code == 200
        assert response.json()["message"]["content"] == "Hello, world!"
