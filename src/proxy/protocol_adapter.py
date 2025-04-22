"""Protocol adapter for converting between different LLM API protocols."""

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from src.logger import logger


class LLMProtocol(str, Enum):
    """Supported LLM API protocols."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class Message(BaseModel):
    """A message in a conversation."""

    role: str
    content: str
    name: Optional[str] = None


class StandardRequest(BaseModel):
    """Standardized request format for internal processing."""

    model: str
    messages: List[Message]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[List[str]] = None
    stream: Optional[bool] = False
    user: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StandardResponse(BaseModel):
    """Standardized response format for internal processing."""

    id: str
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    created: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdaptedRequest(BaseModel):
    """A request adapted to a specific LLM protocol."""

    protocol: LLMProtocol
    payload: Dict[str, Any]
    headers: Dict[str, str]


class AdaptedResponse(BaseModel):
    """A response adapted from a specific LLM protocol."""

    protocol: LLMProtocol
    payload: Dict[str, Any]
    headers: Dict[str, str]


class ProtocolAdapter:
    """Adapts requests and responses between different LLM API protocols."""

    def __init__(self):
        """Initialize the protocol adapter."""
        # Register protocol adapters
        self.request_adapters = {
            LLMProtocol.OPENAI: self._adapt_to_openai_request,
            LLMProtocol.ANTHROPIC: self._adapt_to_anthropic_request,
            LLMProtocol.HUGGINGFACE: self._adapt_to_huggingface_request,
            LLMProtocol.COHERE: self._adapt_to_cohere_request,
            LLMProtocol.OLLAMA: self._adapt_to_ollama_request,
        }

        self.response_adapters = {
            LLMProtocol.OPENAI: self._adapt_from_openai_response,
            LLMProtocol.ANTHROPIC: self._adapt_from_anthropic_response,
            LLMProtocol.HUGGINGFACE: self._adapt_from_huggingface_response,
            LLMProtocol.COHERE: self._adapt_from_cohere_response,
            LLMProtocol.OLLAMA: self._adapt_from_ollama_response,
        }

    def detect_protocol(self, headers: Dict[str, str], url: str) -> LLMProtocol:
        """Detect the LLM protocol from request headers and URL.

        Args:
            headers: The request headers.
            url: The request URL.

        Returns:
            The detected LLM protocol.
        """
        # Check URL patterns
        if "api.openai.com" in url:
            return LLMProtocol.OPENAI
        elif "api.anthropic.com" in url:
            return LLMProtocol.ANTHROPIC
        elif "api-inference.huggingface.co" in url:
            return LLMProtocol.HUGGINGFACE
        elif "api.cohere.ai" in url:
            return LLMProtocol.COHERE
        elif "localhost:11434/api" in url or "ollama" in url:
            return LLMProtocol.OLLAMA

        # Check headers
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer sk-"):
            if "anthropic" in auth_header:
                return LLMProtocol.ANTHROPIC
            else:
                return LLMProtocol.OPENAI

        # Default to custom protocol
        return LLMProtocol.CUSTOM

    def standardize_request(
        self, protocol: LLMProtocol, payload: Dict[str, Any]
    ) -> StandardRequest:
        """Convert a protocol-specific request to the standard format.

        Args:
            protocol: The LLM protocol.
            payload: The request payload.

        Returns:
            The standardized request.
        """
        if protocol == LLMProtocol.OPENAI:
            return self._standardize_openai_request(payload)
        elif protocol == LLMProtocol.ANTHROPIC:
            return self._standardize_anthropic_request(payload)
        elif protocol == LLMProtocol.HUGGINGFACE:
            return self._standardize_huggingface_request(payload)
        elif protocol == LLMProtocol.COHERE:
            return self._standardize_cohere_request(payload)
        elif protocol == LLMProtocol.OLLAMA:
            return self._standardize_ollama_request(payload)
        else:
            # For custom protocols, try to extract common fields
            return self._standardize_custom_request(payload)

    def adapt_request(
        self, standard_request: StandardRequest, target_protocol: LLMProtocol
    ) -> AdaptedRequest:
        """Adapt a standardized request to a specific LLM protocol.

        Args:
            standard_request: The standardized request.
            target_protocol: The target LLM protocol.

        Returns:
            The adapted request.
        """
        adapter = self.request_adapters.get(target_protocol)

        if adapter:
            return adapter(standard_request)
        else:
            logger.warning(f"No adapter found for protocol {target_protocol}")
            # Return a passthrough adapter
            return AdaptedRequest(
                protocol=target_protocol,
                payload=standard_request.model_dump(),
                headers={"Content-Type": "application/json"},
            )

    def standardize_response(
        self, protocol: LLMProtocol, payload: Dict[str, Any]
    ) -> StandardResponse:
        """Convert a protocol-specific response to the standard format.

        Args:
            protocol: The LLM protocol.
            payload: The response payload.

        Returns:
            The standardized response.
        """
        if protocol == LLMProtocol.OPENAI:
            return self._standardize_openai_response(payload)
        elif protocol == LLMProtocol.ANTHROPIC:
            return self._standardize_anthropic_response(payload)
        elif protocol == LLMProtocol.HUGGINGFACE:
            return self._standardize_huggingface_response(payload)
        elif protocol == LLMProtocol.COHERE:
            return self._standardize_cohere_response(payload)
        elif protocol == LLMProtocol.OLLAMA:
            return self._standardize_ollama_response(payload)
        else:
            # For custom protocols, try to extract common fields
            return self._standardize_custom_response(payload)

    def adapt_response(
        self, standard_response: StandardResponse, target_protocol: LLMProtocol
    ) -> AdaptedResponse:
        """Adapt a standardized response to a specific LLM protocol.

        Args:
            standard_response: The standardized response.
            target_protocol: The target LLM protocol.

        Returns:
            The adapted response.
        """
        adapter = self.response_adapters.get(target_protocol)

        if adapter:
            return adapter(standard_response)
        else:
            logger.warning(f"No adapter found for protocol {target_protocol}")
            # Return a passthrough adapter
            return AdaptedResponse(
                protocol=target_protocol,
                payload=standard_response.model_dump(),
                headers={"Content-Type": "application/json"},
            )

    # Standardization methods

    def _standardize_openai_request(self, payload: Dict[str, Any]) -> StandardRequest:
        """Standardize an OpenAI request.

        Args:
            payload: The OpenAI request payload.

        Returns:
            The standardized request.
        """
        # Extract messages
        messages = [
            Message(role=msg["role"], content=msg["content"], name=msg.get("name"))
            for msg in payload.get("messages", [])
        ]

        # Create standard request
        return StandardRequest(
            model=payload.get("model", ""),
            messages=messages,
            temperature=payload.get("temperature", 1.0),
            max_tokens=payload.get("max_tokens"),
            top_p=payload.get("top_p", 1.0),
            frequency_penalty=payload.get("frequency_penalty", 0.0),
            presence_penalty=payload.get("presence_penalty", 0.0),
            stop=payload.get("stop"),
            stream=payload.get("stream", False),
            user=payload.get("user"),
            metadata={"original_protocol": "openai"},
        )

    def _standardize_anthropic_request(self, payload: Dict[str, Any]) -> StandardRequest:
        """Standardize an Anthropic request.

        Args:
            payload: The Anthropic request payload.

        Returns:
            The standardized request.
        """
        # Extract system prompt and messages
        system = payload.get("system", "")
        prompt = payload.get("prompt", "")

        messages = []

        # Add system message if present
        if system:
            messages.append(Message(role="system", content=system))

        # Parse the prompt into messages (simplified)
        if prompt:
            # Simple parsing for Human/Assistant format
            parts = prompt.split("\n\n")
            for i, part in enumerate(parts):
                if part.startswith("Human:"):
                    content = part[6:].strip()
                    messages.append(Message(role="user", content=content))
                elif part.startswith("Assistant:"):
                    content = part[10:].strip()
                    messages.append(Message(role="assistant", content=content))

        # Create standard request
        return StandardRequest(
            model=payload.get("model", ""),
            messages=messages,
            temperature=payload.get("temperature", 1.0),
            max_tokens=payload.get("max_tokens_to_sample"),
            top_p=payload.get("top_p", 1.0),
            stop=payload.get("stop_sequences"),
            stream=payload.get("stream", False),
            metadata={"original_protocol": "anthropic"},
        )

    def _standardize_huggingface_request(self, payload: Dict[str, Any]) -> StandardRequest:
        """Standardize a Hugging Face request.

        Args:
            payload: The Hugging Face request payload.

        Returns:
            The standardized request.
        """
        # Extract inputs
        inputs = payload.get("inputs", "")

        # Create messages
        messages = [Message(role="user", content=inputs)]

        # Create standard request
        return StandardRequest(
            model=payload.get("model", ""),
            messages=messages,
            temperature=payload.get("temperature", 1.0),
            max_tokens=payload.get("max_new_tokens"),
            top_p=payload.get("top_p", 1.0),
            metadata={"original_protocol": "huggingface"},
        )

    def _standardize_cohere_request(self, payload: Dict[str, Any]) -> StandardRequest:
        """Standardize a Cohere request.

        Args:
            payload: The Cohere request payload.

        Returns:
            The standardized request.
        """
        # Extract messages
        message = payload.get("message", "")
        chat_history = payload.get("chat_history", [])

        messages = []

        # Add chat history
        for entry in chat_history:
            role = "user" if entry.get("role") == "USER" else "assistant"
            messages.append(Message(role=role, content=entry.get("message", "")))

        # Add current message
        if message:
            messages.append(Message(role="user", content=message))

        # Create standard request
        return StandardRequest(
            model=payload.get("model", ""),
            messages=messages,
            temperature=payload.get("temperature", 1.0),
            max_tokens=payload.get("max_tokens"),
            metadata={"original_protocol": "cohere"},
        )

    def _standardize_ollama_request(self, payload: Dict[str, Any]) -> StandardRequest:
        """Standardize an Ollama request.

        Args:
            payload: The Ollama request payload.

        Returns:
            The standardized request.
        """
        # Extract messages
        messages_data = payload.get("messages", [])

        messages = []

        # Convert Ollama messages to standard format
        for msg in messages_data:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append(Message(role=role, content=content))

        # Create standard request
        return StandardRequest(
            model=payload.get("model", ""),
            messages=messages,
            temperature=payload.get("temperature", 1.0),
            max_tokens=payload.get("max_tokens"),
            metadata={"original_protocol": "ollama"},
        )

    def _standardize_custom_request(self, payload: Dict[str, Any]) -> StandardRequest:
        """Standardize a custom request by extracting common fields.

        Args:
            payload: The custom request payload.

        Returns:
            The standardized request.
        """
        # Try to extract messages
        messages = []

        # Check for OpenAI-like messages
        if "messages" in payload:
            for msg in payload["messages"]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append(Message(role=role, content=content))
        # Check for prompt or input field
        elif "prompt" in payload:
            messages.append(Message(role="user", content=payload["prompt"]))
        elif "input" in payload:
            messages.append(Message(role="user", content=payload["input"]))
        elif "inputs" in payload:
            messages.append(Message(role="user", content=payload["inputs"]))

        # Create standard request with best-effort extraction
        return StandardRequest(
            model=payload.get("model", ""),
            messages=messages,
            temperature=payload.get("temperature", 1.0),
            max_tokens=payload.get("max_tokens") or payload.get("max_new_tokens"),
            top_p=payload.get("top_p", 1.0),
            metadata={"original_protocol": "custom", "original_payload": payload},
        )

    # Response standardization methods

    def _standardize_openai_response(self, payload: Dict[str, Any]) -> StandardResponse:
        """Standardize an OpenAI response.

        Args:
            payload: The OpenAI response payload.

        Returns:
            The standardized response.
        """
        return StandardResponse(
            id=payload.get("id", ""),
            model=payload.get("model", ""),
            choices=payload.get("choices", []),
            usage=payload.get("usage", {}),
            created=payload.get("created", 0),
            metadata={"original_protocol": "openai"},
        )

    def _standardize_anthropic_response(self, payload: Dict[str, Any]) -> StandardResponse:
        """Standardize an Anthropic response.

        Args:
            payload: The Anthropic response payload.

        Returns:
            The standardized response.
        """
        # Convert Anthropic format to standard format
        content = payload.get("completion", "")

        choices = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": payload.get("stop_reason", "stop"),
            }
        ]

        usage = {
            "prompt_tokens": payload.get("usage", {}).get("prompt_tokens", 0),
            "completion_tokens": payload.get("usage", {}).get("completion_tokens", 0),
            "total_tokens": payload.get("usage", {}).get("total_tokens", 0),
        }

        return StandardResponse(
            id=payload.get("id", ""),
            model=payload.get("model", ""),
            choices=choices,
            usage=usage,
            created=payload.get("created", 0),
            metadata={"original_protocol": "anthropic"},
        )

    def _standardize_huggingface_response(self, payload: Dict[str, Any]) -> StandardResponse:
        """Standardize a Hugging Face response.

        Args:
            payload: The Hugging Face response payload.

        Returns:
            The standardized response.
        """
        # Extract generated text
        generated_text = ""

        if isinstance(payload, list) and len(payload) > 0:
            generated_text = payload[0].get("generated_text", "")
        elif isinstance(payload, dict):
            generated_text = payload.get("generated_text", "")

        choices = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": generated_text},
                "finish_reason": "stop",
            }
        ]

        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        return StandardResponse(
            id="hf_" + str(hash(generated_text))[:8],
            model="huggingface",
            choices=choices,
            usage=usage,
            created=int(import_time()),
            metadata={"original_protocol": "huggingface"},
        )

    def _standardize_cohere_response(self, payload: Dict[str, Any]) -> StandardResponse:
        """Standardize a Cohere response.

        Args:
            payload: The Cohere response payload.

        Returns:
            The standardized response.
        """
        # Extract text
        text = ""

        if "text" in payload:
            text = payload["text"]
        elif "generations" in payload and len(payload["generations"]) > 0:
            text = payload["generations"][0].get("text", "")

        choices = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ]

        usage = {
            "prompt_tokens": payload.get("meta", {}).get("prompt_tokens", 0),
            "completion_tokens": payload.get("meta", {}).get("completion_tokens", 0),
            "total_tokens": payload.get("meta", {}).get("total_tokens", 0),
        }

        return StandardResponse(
            id=payload.get("id", ""),
            model=payload.get("model", ""),
            choices=choices,
            usage=usage,
            created=int(import_time()),
            metadata={"original_protocol": "cohere"},
        )

    def _standardize_ollama_response(self, payload: Dict[str, Any]) -> StandardResponse:
        """Standardize an Ollama response.

        Args:
            payload: The Ollama response payload.

        Returns:
            The standardized response.
        """
        # Extract content from Ollama response
        message = payload.get("message", {})
        content = message.get("content", "")

        choices = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ]

        # Ollama doesn't provide detailed token usage, try to extract from response
        prompt_tokens = payload.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = payload.get("usage", {}).get("completion_tokens", 0)
        total_tokens = payload.get("usage", {}).get("total_tokens", 0)

        # If token information is not available, estimate based on total_duration
        if total_tokens == 0 and "total_duration" in payload:
            # Very rough estimate based on processing time
            total_tokens = int(payload.get("total_duration", 0) / 1000000)  # Convert ns to tokens (very approximate)
            prompt_tokens = total_tokens // 2
            completion_tokens = total_tokens - prompt_tokens

        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

        return StandardResponse(
            id=payload.get("id", "ollama_" + str(hash(content))[:8]),
            model=payload.get("model", ""),
            choices=choices,
            usage=usage,
            created=int(import_time()),
            metadata={"original_protocol": "ollama"},
        )

    def _standardize_custom_response(self, payload: Dict[str, Any]) -> StandardResponse:
        """Standardize a custom response by extracting common fields.

        Args:
            payload: The custom response payload.

        Returns:
            The standardized response.
        """
        # Try to extract content
        content = ""

        if "choices" in payload and len(payload["choices"]) > 0:
            choice = payload["choices"][0]
            if "message" in choice:
                content = choice["message"].get("content", "")
            elif "text" in choice:
                content = choice["text"]
        elif "completion" in payload:
            content = payload["completion"]
        elif "text" in payload:
            content = payload["text"]
        elif "content" in payload:
            content = payload["content"]

        choices = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ]

        usage = payload.get("usage", {})

        return StandardResponse(
            id=payload.get("id", "custom_" + str(hash(content))[:8]),
            model=payload.get("model", "custom"),
            choices=choices,
            usage=usage,
            created=int(import_time()),
            metadata={"original_protocol": "custom", "original_payload": payload},
        )

    # Adaptation methods

    def _adapt_to_openai_request(self, standard_request: StandardRequest) -> AdaptedRequest:
        """Adapt a standardized request to OpenAI format.

        Args:
            standard_request: The standardized request.

        Returns:
            The adapted request.
        """
        payload = {
            "model": standard_request.model,
            "messages": [msg.model_dump() for msg in standard_request.messages],
            "temperature": standard_request.temperature,
        }

        if standard_request.max_tokens is not None:
            payload["max_tokens"] = standard_request.max_tokens

        if standard_request.top_p != 1.0:
            payload["top_p"] = standard_request.top_p

        if standard_request.frequency_penalty != 0.0:
            payload["frequency_penalty"] = standard_request.frequency_penalty

        if standard_request.presence_penalty != 0.0:
            payload["presence_penalty"] = standard_request.presence_penalty

        if standard_request.stop:
            payload["stop"] = standard_request.stop

        if standard_request.stream:
            payload["stream"] = standard_request.stream

        if standard_request.user:
            payload["user"] = standard_request.user

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedRequest(
            protocol=LLMProtocol.OPENAI,
            payload=payload,
            headers=headers,
        )

    def _adapt_to_anthropic_request(self, standard_request: StandardRequest) -> AdaptedRequest:
        """Adapt a standardized request to Anthropic format.

        Args:
            standard_request: The standardized request.

        Returns:
            The adapted request.
        """
        # Extract system message if present
        system = ""
        messages = []

        for msg in standard_request.messages:
            if msg.role == "system":
                system = msg.content
            else:
                messages.append(msg)

        # Build prompt in Anthropic format
        prompt = ""
        for i, msg in enumerate(messages):
            if msg.role == "user":
                prompt += f"\n\nHuman: {msg.content}"
            elif msg.role == "assistant":
                prompt += f"\n\nAssistant: {msg.content}"

        # Add final assistant prompt
        prompt += "\n\nAssistant:"

        payload = {
            "model": standard_request.model,
            "prompt": prompt,
            "temperature": standard_request.temperature,
        }

        if system:
            payload["system"] = system

        if standard_request.max_tokens is not None:
            payload["max_tokens_to_sample"] = standard_request.max_tokens

        if standard_request.top_p != 1.0:
            payload["top_p"] = standard_request.top_p

        if standard_request.stop:
            payload["stop_sequences"] = standard_request.stop

        if standard_request.stream:
            payload["stream"] = standard_request.stream

        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        return AdaptedRequest(
            protocol=LLMProtocol.ANTHROPIC,
            payload=payload,
            headers=headers,
        )

    def _adapt_to_huggingface_request(self, standard_request: StandardRequest) -> AdaptedRequest:
        """Adapt a standardized request to Hugging Face format.

        Args:
            standard_request: The standardized request.

        Returns:
            The adapted request.
        """
        # Extract user message
        inputs = ""
        for msg in standard_request.messages:
            if msg.role == "user":
                inputs += msg.content + "\n"

        payload = {
            "inputs": inputs.strip(),
        }

        if standard_request.temperature != 1.0:
            payload["parameters"] = {"temperature": standard_request.temperature}

        if standard_request.max_tokens is not None:
            if "parameters" not in payload:
                payload["parameters"] = {}
            payload["parameters"]["max_new_tokens"] = standard_request.max_tokens

        if standard_request.top_p != 1.0:
            if "parameters" not in payload:
                payload["parameters"] = {}
            payload["parameters"]["top_p"] = standard_request.top_p

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedRequest(
            protocol=LLMProtocol.HUGGINGFACE,
            payload=payload,
            headers=headers,
        )

    def _adapt_to_cohere_request(self, standard_request: StandardRequest) -> AdaptedRequest:
        """Adapt a standardized request to Cohere format.

        Args:
            standard_request: The standardized request.

        Returns:
            The adapted request.
        """
        # Extract chat history and current message
        chat_history = []
        current_message = ""

        for i, msg in enumerate(standard_request.messages[:-1]):
            role = "USER" if msg.role == "user" else "CHATBOT"
            chat_history.append({"role": role, "message": msg.content})

        if standard_request.messages:
            current_message = standard_request.messages[-1].content

        payload = {
            "model": standard_request.model,
            "message": current_message,
            "chat_history": chat_history,
            "temperature": standard_request.temperature,
        }

        if standard_request.max_tokens is not None:
            payload["max_tokens"] = standard_request.max_tokens

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedRequest(
            protocol=LLMProtocol.COHERE,
            payload=payload,
            headers=headers,
        )

    # Response adaptation methods

    def _adapt_from_openai_response(
        self, standard_response: StandardResponse
    ) -> AdaptedResponse:
        """Adapt a standardized response to OpenAI format.

        Args:
            standard_response: The standardized response.

        Returns:
            The adapted response.
        """
        # OpenAI format is already close to our standard format
        payload = {
            "id": standard_response.id,
            "object": "chat.completion",
            "created": standard_response.created,
            "model": standard_response.model,
            "choices": standard_response.choices,
            "usage": standard_response.usage,
        }

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedResponse(
            protocol=LLMProtocol.OPENAI,
            payload=payload,
            headers=headers,
        )

    def _adapt_from_anthropic_response(
        self, standard_response: StandardResponse
    ) -> AdaptedResponse:
        """Adapt a standardized response to Anthropic format.

        Args:
            standard_response: The standardized response.

        Returns:
            The adapted response.
        """
        # Extract content from choices
        content = ""
        stop_reason = "stop"

        if standard_response.choices and len(standard_response.choices) > 0:
            choice = standard_response.choices[0]
            if "message" in choice:
                content = choice["message"].get("content", "")
            stop_reason = choice.get("finish_reason", "stop")

        payload = {
            "id": standard_response.id,
            "type": "completion",
            "completion": content,
            "model": standard_response.model,
            "stop_reason": stop_reason,
            "usage": standard_response.usage,
        }

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedResponse(
            protocol=LLMProtocol.ANTHROPIC,
            payload=payload,
            headers=headers,
        )

    def _adapt_from_huggingface_response(
        self, standard_response: StandardResponse
    ) -> AdaptedResponse:
        """Adapt a standardized response to Hugging Face format.

        Args:
            standard_response: The standardized response.

        Returns:
            The adapted response.
        """
        # Extract content from choices
        content = ""

        if standard_response.choices and len(standard_response.choices) > 0:
            choice = standard_response.choices[0]
            if "message" in choice:
                content = choice["message"].get("content", "")

        payload = [{"generated_text": content}]

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedResponse(
            protocol=LLMProtocol.HUGGINGFACE,
            payload=payload,
            headers=headers,
        )

    def _adapt_from_cohere_response(
        self, standard_response: StandardResponse
    ) -> AdaptedResponse:
        """Adapt a standardized response to Cohere format.

        Args:
            standard_response: The standardized response.

        Returns:
            The adapted response.
        """
        # Extract content from choices
        content = ""

        if standard_response.choices and len(standard_response.choices) > 0:
            choice = standard_response.choices[0]
            if "message" in choice:
                content = choice["message"].get("content", "")

        payload = {
            "id": standard_response.id,
            "text": content,
            "model": standard_response.model,
            "generations": [{"text": content}],
            "meta": {
                "prompt_tokens": standard_response.usage.get("prompt_tokens", 0),
                "completion_tokens": standard_response.usage.get("completion_tokens", 0),
                "total_tokens": standard_response.usage.get("total_tokens", 0),
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedResponse(
            protocol=LLMProtocol.COHERE,
            payload=payload,
            headers=headers,
        )

    def _adapt_to_ollama_request(self, standard_request: StandardRequest) -> AdaptedRequest:
        """Adapt a standard request to the Ollama API format.

        Args:
            standard_request: The standardized request.

        Returns:
            The adapted request for the Ollama API.
        """
        try:
            # Extract messages
            messages = standard_request.messages

            # Build the Ollama request payload
            payload = {
                "model": standard_request.model,
                "messages": [{
                    "role": msg.role,
                    "content": msg.content
                } for msg in messages],
                "stream": False,
            }

            # Add optional parameters if they exist
            if standard_request.temperature is not None:
                payload["temperature"] = standard_request.temperature

            if standard_request.max_tokens is not None:
                payload["max_tokens"] = standard_request.max_tokens

            return AdaptedRequest(
                protocol=LLMProtocol.OLLAMA,
                payload=payload,
                headers={"Content-Type": "application/json"},
                endpoint="/chat",  # Ollama chat endpoint
            )
        except Exception as e:
            logger.error(f"Error adapting to Ollama request: {e}")
            # Return a minimal valid request
            return AdaptedRequest(
                protocol=LLMProtocol.OLLAMA,
                payload={"model": standard_request.model, "messages": [{"role": "user", "content": "Hello"}]},
                headers={"Content-Type": "application/json"},
                endpoint="/chat",
            )

    def _adapt_from_ollama_response(
        self, standard_response: StandardResponse
    ) -> AdaptedResponse:
        """Adapt a standardized response to Ollama format.

        Args:
            standard_response: The standardized response.

        Returns:
            The adapted response.
        """
        # Extract content from choices
        content = ""

        if standard_response.choices and len(standard_response.choices) > 0:
            choice = standard_response.choices[0]
            if "message" in choice:
                content = choice["message"].get("content", "")

        payload = {
            "model": standard_response.model,
            "message": {
                "role": "assistant",
                "content": content
            },
            "total_duration": 0,  # Placeholder
        }

        headers = {
            "Content-Type": "application/json",
        }

        return AdaptedResponse(
            protocol=LLMProtocol.OLLAMA,
            payload=payload,
            headers=headers,
        )


def import_time() -> float:
    """Import time module and return current time.

    This function is used to avoid circular imports.

    Returns:
        The current time in seconds since the epoch.
    """
    import time
    return time.time()
