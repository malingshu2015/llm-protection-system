"""Tests for the protocol adapter module."""

import pytest

from src.proxy.protocol_adapter import (
    LLMProtocol,
    Message,
    StandardRequest,
    StandardResponse,
    AdaptedRequest,
    AdaptedResponse,
    ProtocolAdapter,
)


def test_message_model():
    """Test the Message model."""
    # Create a message
    message = Message(role="user", content="Hello, world!", name="John")
    
    # Check fields
    assert message.role == "user"
    assert message.content == "Hello, world!"
    assert message.name == "John"
    
    # Create a message without name
    message = Message(role="assistant", content="How can I help you?")
    
    # Check fields
    assert message.role == "assistant"
    assert message.content == "How can I help you?"
    assert message.name is None


def test_standard_request_model():
    """Test the StandardRequest model."""
    # Create a standard request
    request = StandardRequest(
        model="gpt-3.5-turbo",
        messages=[
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello, world!"),
        ],
        temperature=0.7,
        max_tokens=100,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\n"],
        stream=False,
        user="user123",
        metadata={"source": "test"},
    )
    
    # Check fields
    assert request.model == "gpt-3.5-turbo"
    assert len(request.messages) == 2
    assert request.messages[0].role == "system"
    assert request.messages[1].content == "Hello, world!"
    assert request.temperature == 0.7
    assert request.max_tokens == 100
    assert request.top_p == 0.9
    assert request.frequency_penalty == 0.0
    assert request.presence_penalty == 0.0
    assert request.stop == ["\n"]
    assert request.stream == False
    assert request.user == "user123"
    assert request.metadata == {"source": "test"}


def test_standard_response_model():
    """Test the StandardResponse model."""
    # Create a standard response
    response = StandardResponse(
        id="chatcmpl-123",
        model="gpt-3.5-turbo",
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello! How can I help you?"},
                "finish_reason": "stop",
            }
        ],
        usage={"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
        created=1677858242,
        metadata={"source": "test"},
    )
    
    # Check fields
    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-3.5-turbo"
    assert len(response.choices) == 1
    assert response.choices[0]["message"]["content"] == "Hello! How can I help you?"
    assert response.usage["prompt_tokens"] == 13
    assert response.created == 1677858242
    assert response.metadata == {"source": "test"}


def test_protocol_adapter_detect_protocol():
    """Test the protocol detection in the ProtocolAdapter."""
    adapter = ProtocolAdapter()
    
    # Test OpenAI URL
    protocol = adapter.detect_protocol(
        headers={"Content-Type": "application/json"},
        url="https://api.openai.com/v1/chat/completions",
    )
    assert protocol == LLMProtocol.OPENAI
    
    # Test Anthropic URL
    protocol = adapter.detect_protocol(
        headers={"Content-Type": "application/json"},
        url="https://api.anthropic.com/v1/complete",
    )
    assert protocol == LLMProtocol.ANTHROPIC
    
    # Test HuggingFace URL
    protocol = adapter.detect_protocol(
        headers={"Content-Type": "application/json"},
        url="https://api-inference.huggingface.co/models/gpt2",
    )
    assert protocol == LLMProtocol.HUGGINGFACE
    
    # Test Cohere URL
    protocol = adapter.detect_protocol(
        headers={"Content-Type": "application/json"},
        url="https://api.cohere.ai/v1/generate",
    )
    assert protocol == LLMProtocol.COHERE
    
    # Test unknown URL
    protocol = adapter.detect_protocol(
        headers={"Content-Type": "application/json"},
        url="https://api.example.com/v1/generate",
    )
    assert protocol == LLMProtocol.CUSTOM


def test_protocol_adapter_standardize_openai_request():
    """Test standardizing an OpenAI request."""
    adapter = ProtocolAdapter()
    
    # Create an OpenAI request payload
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ],
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stop": ["\n"],
        "stream": False,
        "user": "user123",
    }
    
    # Standardize the request
    standard_request = adapter.standardize_request(LLMProtocol.OPENAI, payload)
    
    # Check fields
    assert standard_request.model == "gpt-3.5-turbo"
    assert len(standard_request.messages) == 2
    assert standard_request.messages[0].role == "system"
    assert standard_request.messages[1].content == "Hello, world!"
    assert standard_request.temperature == 0.7
    assert standard_request.max_tokens == 100
    assert standard_request.top_p == 0.9
    assert standard_request.frequency_penalty == 0.0
    assert standard_request.presence_penalty == 0.0
    assert standard_request.stop == ["\n"]
    assert standard_request.stream == False
    assert standard_request.user == "user123"
    assert standard_request.metadata["original_protocol"] == "openai"


def test_protocol_adapter_adapt_request():
    """Test adapting a standard request to a specific protocol."""
    adapter = ProtocolAdapter()
    
    # Create a standard request
    standard_request = StandardRequest(
        model="gpt-3.5-turbo",
        messages=[
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello, world!"),
        ],
        temperature=0.7,
        max_tokens=100,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\n"],
        stream=False,
        user="user123",
        metadata={"source": "test"},
    )
    
    # Adapt to OpenAI protocol
    adapted_request = adapter.adapt_request(standard_request, LLMProtocol.OPENAI)
    
    # Check fields
    assert adapted_request.protocol == LLMProtocol.OPENAI
    assert adapted_request.payload["model"] == "gpt-3.5-turbo"
    assert len(adapted_request.payload["messages"]) == 2
    assert adapted_request.payload["temperature"] == 0.7
    assert adapted_request.headers["Content-Type"] == "application/json"
    
    # Adapt to Anthropic protocol
    adapted_request = adapter.adapt_request(standard_request, LLMProtocol.ANTHROPIC)
    
    # Check fields
    assert adapted_request.protocol == LLMProtocol.ANTHROPIC
    assert adapted_request.payload["model"] == "gpt-3.5-turbo"
    assert "system" in adapted_request.payload
    assert "prompt" in adapted_request.payload
    assert adapted_request.headers["Content-Type"] == "application/json"
    assert adapted_request.headers["anthropic-version"] == "2023-06-01"


def test_protocol_adapter_standardize_openai_response():
    """Test standardizing an OpenAI response."""
    adapter = ProtocolAdapter()
    
    # Create an OpenAI response payload
    payload = {
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
    
    # Standardize the response
    standard_response = adapter.standardize_response(LLMProtocol.OPENAI, payload)
    
    # Check fields
    assert standard_response.id == "chatcmpl-123"
    assert standard_response.model == "gpt-3.5-turbo-0613"
    assert len(standard_response.choices) == 1
    assert standard_response.choices[0]["message"]["content"] == "Hello! How can I help you today?"
    assert standard_response.usage["prompt_tokens"] == 13
    assert standard_response.created == 1677858242
    assert standard_response.metadata["original_protocol"] == "openai"


def test_protocol_adapter_adapt_response():
    """Test adapting a standard response to a specific protocol."""
    adapter = ProtocolAdapter()
    
    # Create a standard response
    standard_response = StandardResponse(
        id="chatcmpl-123",
        model="gpt-3.5-turbo",
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello! How can I help you?"},
                "finish_reason": "stop",
            }
        ],
        usage={"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20},
        created=1677858242,
        metadata={"source": "test"},
    )
    
    # Adapt to OpenAI protocol
    adapted_response = adapter.adapt_response(standard_response, LLMProtocol.OPENAI)
    
    # Check fields
    assert adapted_response.protocol == LLMProtocol.OPENAI
    assert adapted_response.payload["id"] == "chatcmpl-123"
    assert adapted_response.payload["model"] == "gpt-3.5-turbo"
    assert len(adapted_response.payload["choices"]) == 1
    assert adapted_response.headers["Content-Type"] == "application/json"
    
    # Adapt to Anthropic protocol
    adapted_response = adapter.adapt_response(standard_response, LLMProtocol.ANTHROPIC)
    
    # Check fields
    assert adapted_response.protocol == LLMProtocol.ANTHROPIC
    assert adapted_response.payload["id"] == "chatcmpl-123"
    assert adapted_response.payload["model"] == "gpt-3.5-turbo"
    assert "completion" in adapted_response.payload
    assert adapted_response.headers["Content-Type"] == "application/json"
