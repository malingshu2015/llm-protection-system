"""HTTP interceptor for the proxy service."""

import asyncio
import json
import time
from typing import Any, Dict, Optional, Tuple, Union

import aiohttp
from fastapi import Request, Response
from pydantic import ValidationError

# 尝试导入ollama，如果不可用则设置为None
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    ollama = None
    OLLAMA_AVAILABLE = False

from src.config import settings
from src.logger import logger
from src.models_interceptor import InterceptedRequest, InterceptedResponse, DetectionResult


class HTTPInterceptor:
    """Intercepts HTTP requests and responses for security checks."""

    def __init__(self):
        """Initialize the HTTP interceptor."""
        # Import here to avoid circular imports
        from src.security.detector import SecurityDetector
        self.security_detector = SecurityDetector()

        # 创建具有更长超时时间的客户端会话
        timeout = aiohttp.ClientTimeout(total=120)  # 设置为 120 秒
        self.client_session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        """Close the HTTP client session."""
        await self.client_session.close()

    async def intercept(self, request: Request) -> Response:
        """Intercept an HTTP request, perform security checks, and forward it.

        Args:
            request: The incoming FastAPI request.

        Returns:
            The response from the target LLM provider.
        """
        start_time = time.time()

        try:
            # Parse and validate the request
            intercepted_request = await self._parse_request(request)

            # Perform security checks on the request
            security_result = await self.security_detector.check_request(intercepted_request)

            if not security_result.is_allowed:
                # Return blocked response if request is not allowed
                return await self._create_blocked_response(
                    security_result.reason, security_result.status_code
                )

            # 检查是否是测试环境，如果是，则不转发请求
            logger.info(f"Environment: {settings.environment}, Debug: {settings.debug}")
            # 强制设置为生产环境
            settings.environment = "production"
            settings.debug = False
            logger.info(f"New Environment: {settings.environment}, Debug: {settings.debug}")
            if False:
                # 创建一个模拟响应
                mock_response = InterceptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body={
                        "id": "mock-response-id",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": intercepted_request.body.get("model", "gpt-3.5-turbo"),
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "这是一个模拟响应，因为系统处于开发模式。",
                                },
                                "finish_reason": "stop",
                                "index": 0,
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 10,
                            "total_tokens": 20,
                        },
                    },
                    timestamp=time.time(),
                    latency=0.1,
                )
                return await self._create_response(mock_response)

            # Forward the request to the target LLM provider
            response = await self._forward_request(intercepted_request)

            # Perform security checks on the response
            security_result = await self.security_detector.check_response(response)

            if not security_result.is_allowed:
                # Return blocked response if response is not allowed
                return await self._create_blocked_response(
                    security_result.reason, security_result.status_code
                )

            # Return the response
            return await self._create_response(response)

        except Exception as e:
            logger.exception(f"Error intercepting request: {e}")
            return await self._create_error_response(str(e))
        finally:
            # Log request latency
            latency = time.time() - start_time
            logger.info(f"Request processed in {latency:.3f} seconds")

    def _get_provider_from_model(self, model_name: str) -> Optional[str]:
        """Determine the LLM provider from the model name.

        Args:
            model_name: The name of the model.

        Returns:
            The provider name, or None if the provider cannot be determined.
        """
        if not model_name:
            return None

        # OpenAI models
        if model_name.startswith("gpt-") or model_name.startswith("text-davinci-"):
            return "openai"

        # Anthropic models
        if model_name.startswith("claude-"):
            return "anthropic"

        # Ollama models
        if model_name.startswith("llama") or \
           model_name.startswith("mistral") or \
           model_name.startswith("gemma") or \
           model_name.startswith("phi") or \
           model_name.startswith("qwen") or \
           model_name.startswith("codellama") or \
           model_name.startswith("vicuna") or \
           model_name.startswith("orca"):
            return "ollama"

        return None

    async def _parse_request(self, request: Request) -> InterceptedRequest:
        """Parse and validate the incoming request.

        Args:
            request: The incoming FastAPI request.

        Returns:
            The parsed and validated request.
        """
        # Get request headers
        headers = dict(request.headers)

        # Get request body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body = json.loads(body_bytes)
                except json.JSONDecodeError:
                    body = {"raw_content": body_bytes.decode("utf-8", errors="replace")}

        # Determine LLM provider from the URL
        provider = "unknown"
        url = str(request.url)

        # 检查是否是内部路由
        if "localhost:8080" in url or "127.0.0.1:8080" in url:
            # 如果是内部路由，则不转发
            if "/api/v1/ollama/" in url:
                provider = "ollama"
            else:
                provider = "internal"
        else:
            # 首先尝试从 URL 确定提供商
            for provider_name, provider_config in settings.llm_providers.items():
                if provider_config["api_base"] in url:
                    provider = provider_name
                    break

        # 如果无法从 URL 确定提供商，尝试从模型名称确定
        if provider == "unknown" and body and "model" in body:
            model_provider = self._get_provider_from_model(body["model"])
            if model_provider:
                provider = model_provider

        # Create intercepted request
        return InterceptedRequest(
            method=request.method,
            url=str(request.url),
            headers=headers,
            body=body,
            query_params=dict(request.query_params),
            timestamp=time.time(),
            client_ip=request.client.host if request.client else "",
            provider=provider,
        )

    async def _forward_request(
        self, intercepted_request: InterceptedRequest
    ) -> InterceptedResponse:
        """Forward the request to the target LLM provider.

        Args:
            intercepted_request: The intercepted request.

        Returns:
            The response from the target LLM provider.
        """
        start_time = time.time()

        # Prepare request parameters
        method = intercepted_request.method
        url = intercepted_request.url
        headers = intercepted_request.headers
        data = json.dumps(intercepted_request.body) if intercepted_request.body else None

        # 如果是 Ollama 请求，使用 Ollama Python 客户端直接调用
        if intercepted_request.provider == "ollama":
            logger.info(f"Processing Ollama request for model: {intercepted_request.body.get('model', 'unknown')}")

            # 从请求中提取模型名称和消息
            model = intercepted_request.body.get("model", "llama2")
            messages = intercepted_request.body.get("messages", [])

            logger.info(f"Calling Ollama with model: {model} and {len(messages)} messages")

            # 检查Ollama模块是否可用
            if OLLAMA_AVAILABLE:
                try:
                    # 使用 Ollama Python 客户端发送请求
                    response_data = ollama.chat(model=model, messages=messages)
                    logger.info(f"Ollama response: {response_data}")

                    # 创建模拟的拦截响应
                    response = InterceptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body={
                            "id": f"ollama-{int(time.time())}",
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [
                                {
                                    "message": {
                                        "role": "assistant",
                                        "content": response_data.get("message", {}).get("content", ""),
                                    },
                                    "finish_reason": "stop",
                                    "index": 0,
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 0,  # Ollama 不提供这些信息
                                "completion_tokens": 0,
                                "total_tokens": 0,
                            },
                        },
                        timestamp=time.time(),
                        latency=0.1,
                    )

                    # 返回响应，但需要先转换为 FastAPI 响应
                    return await self._create_response(response)
                except Exception as e:
                    logger.exception(f"Error calling Ollama: {e}")
                    # 创建错误响应
                    error_response = InterceptedResponse(
                        status_code=500,
                        headers={"Content-Type": "application/json"},
                        body={
                            "error": {
                                "message": f"Error calling Ollama: {str(e)}",
                                "type": "ollama_error",
                                "code": 500,
                            }
                        },
                        timestamp=time.time(),
                        latency=0.1,
                    )
                    return await self._create_response(error_response)
            else:
                # Ollama模块不可用，返回错误响应
                logger.error("Ollama module is not available")
                error_response = InterceptedResponse(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body={
                        "error": {
                            "message": "Ollama module is not available. Please install the Ollama Python client.",
                            "type": "ollama_error",
                            "code": 500,
                        }
                    },
                    timestamp=time.time(),
                    latency=0.1,
                )
                return await self._create_response(error_response)

        # 如果是内部请求或 URL 为空，说明请求已经在前面的代码中处理过了，或者不应该转发
        if not url or intercepted_request.provider == "internal":
            return InterceptedResponse(
                status_code=500,
                headers={"Content-Type": "application/json"},
                body={
                    "error": {
                        "message": "Internal request not forwarded",
                        "type": "internal_request",
                        "code": 500,
                    }
                },
                timestamp=time.time(),
                latency=time.time() - start_time,
            )

        # 获取提供商超时时间，默认为 60 秒
        provider_timeout = int(
            settings.llm_providers.get(
                intercepted_request.provider, {"timeout": "60"}
            ).get("timeout", "60")
        )

        # 使用更长的超时时间
        timeout = aiohttp.ClientTimeout(total=provider_timeout)

        try:
            # Forward the request
            async with self.client_session.request(
                method=method, url=url, headers=headers, data=data, timeout=timeout
            ) as response:
                # Get response body
                response_body = None
                response_text = await response.text()
                if response_text:
                    try:
                        response_body = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_body = {"raw_content": response_text}

                # Create intercepted response
                return InterceptedResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    body=response_body,
                    timestamp=time.time(),
                    latency=time.time() - start_time,
                )
        except asyncio.TimeoutError:
            logger.error(f"Request timed out after {provider_timeout} seconds: {url}")
            return InterceptedResponse(
                status_code=504,  # Gateway Timeout
                headers={"Content-Type": "application/json"},
                body={
                    "error": {
                        "message": f"Request timed out after {provider_timeout} seconds",
                        "type": "timeout_error",
                        "code": 504,
                    }
                },
                timestamp=time.time(),
                latency=time.time() - start_time,
            )
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return InterceptedResponse(
                status_code=502,  # Bad Gateway
                headers={"Content-Type": "application/json"},
                body={
                    "error": {
                        "message": f"HTTP client error: {str(e)}",
                        "type": "http_client_error",
                        "code": 502,
                    }
                },
                timestamp=time.time(),
                latency=time.time() - start_time,
            )
        except Exception as e:
            logger.exception(f"Unexpected error forwarding request: {e}")
            return InterceptedResponse(
                status_code=500,
                headers={"Content-Type": "application/json"},
                body={
                    "error": {
                        "message": f"Unexpected error: {str(e)}",
                        "type": "internal_error",
                        "code": 500,
                    }
                },
                timestamp=time.time(),
                latency=time.time() - start_time,
            )

    async def _create_response(self, intercepted_response: InterceptedResponse) -> Response:
        """Create a FastAPI response from an intercepted response.

        Args:
            intercepted_response: The intercepted response.

        Returns:
            The FastAPI response.
        """
        # Prepare response content
        content = (
            json.dumps(intercepted_response.body)
            if intercepted_response.body
            else ""
        )

        # Create response
        return Response(
            content=content,
            status_code=intercepted_response.status_code,
            headers=intercepted_response.headers,
        )

    async def _create_blocked_response(
        self, reason: str, status_code: int = 403
    ) -> Response:
        """Create a response for blocked requests.

        Args:
            reason: The reason for blocking the request.
            status_code: The HTTP status code to return.

        Returns:
            The blocked response.
        """
        # 根据不同的拦截原因提供更友好的提示信息
        friendly_message = self._get_friendly_message(reason)
        suggestion = self._get_suggestion(reason)

        content = json.dumps(
            {
                "error": {
                    "message": f"请求被本地大模型防护系统拦截: {reason}",
                    "friendly_message": friendly_message,
                    "suggestion": suggestion,
                    "type": "security_violation",
                    "code": status_code,
                    "request_id": f"req-{int(time.time())}",
                    "feedback_url": "/api/v1/feedback/false-positive"
                }
            }
        )

        return Response(
            content=content,
            status_code=status_code,
            headers={"Content-Type": "application/json"},
        )

    def _get_friendly_message(self, reason: str) -> str:
        """根据拦截原因获取友好的提示信息。

        Args:
            reason: 拦截原因。

        Returns:
            友好的提示信息。
        """
        if "Prompt Injection" in reason:
            return "您的请求可能包含试图操纵模型的内容，这可能会导致安全风险。"
        elif "Jailbreak" in reason:
            return "您的请求可能包含试图绕过模型安全限制的内容，这违反了使用规范。"
        elif "Harmful Content" in reason:
            return "您的请求可能包含有害内容，我们无法处理此类请求。"
        elif "Sensitive Information" in reason:
            return "您的请求可能包含敏感信息，为保护您的隐私，我们已拦截此请求。"
        elif "Violence Content" in reason:
            return "您的请求可能包含暴力内容，我们无法处理此类请求。"
        elif "Self-Harm Content" in reason:
            return "您的请求可能涉及自残内容，如果您需要帮助，请联系专业心理咨询机构。"
        elif "Child Exploitation" in reason:
            return "您的请求可能涉及儿童不当内容，这违反了法律法规和使用规范。"
        else:
            return "您的请求违反了安全规则，已被系统拦截。"

    def _get_suggestion(self, reason: str) -> str:
        """根据拦截原因获取建议。

        Args:
            reason: 拦截原因。

        Returns:
            建议内容。
        """
        if "Prompt Injection" in reason:
            return "请避免使用试图操控模型的指令，如'忽略之前的指示'等。"
        elif "Jailbreak" in reason:
            return "请避免使用DAN等越狱提示，模型只能在安全限制内回答问题。"
        elif "Harmful Content" in reason:
            return "请避免询问有关制作危险物品、实施暴力行为等有害内容的问题。"
        elif "Sensitive Information" in reason:
            return "请不要在对话中分享密码、信用卡号等敏感个人信息，以保护您的隐私安全。"
        elif "Violence Content" in reason:
            return "请避免询问有关暴力行为的问题，尝试以更积极的方式表达您的需求。"
        elif "Self-Harm Content" in reason:
            return "如果您正在经历困难，请寻求专业帮助，全国心理援助热线：400-161-9995。"
        elif "Child Exploitation" in reason:
            return "此类内容严重违反法律法规，请立即停止相关查询。"
        else:
            return "请修改您的请求，避免包含可能违反安全规则的内容。如果您认为这是误判，可以通过反馈功能告诉我们。"

    async def _create_error_response(self, error_message: str) -> Response:
        """Create a response for internal errors.

        Args:
            error_message: The error message.

        Returns:
            The error response.
        """
        content = json.dumps(
            {
                "error": {
                    "message": f"LLM Security Firewall error: {error_message}",
                    "type": "internal_error",
                    "code": 500,
                }
            }
        )

        return Response(
            content=content,
            status_code=500,
            headers={"Content-Type": "application/json"},
        )
