"""Ollama API代理路由，用于拦截和处理发送到Ollama原生API的请求。"""

import json
import time
import subprocess
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
import aiohttp

from src.logger import logger
from src.models_interceptor import InterceptedRequest, InterceptedResponse


router = APIRouter()
interceptor = None
security_detector = None


async def startup():
    """Start the components on startup."""
    global interceptor, security_detector

    # Initialize components
    from src.proxy.interceptor import HTTPInterceptor
    from src.security.detector import SecurityDetector

    security_detector = SecurityDetector()
    interceptor = HTTPInterceptor()


async def shutdown():
    """Stop the components on shutdown."""
    global interceptor

    # Close the interceptor if it exists
    if interceptor is not None:
        await interceptor.close()


# 在路由器启动时初始化组件
@router.on_event("startup")
async def startup_event():
    await startup()

# 在路由器关闭时清理组件
@router.on_event("shutdown")
async def shutdown_event():
    await shutdown()


@router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def ollama_proxy(request: Request, path: str):
    """代理Ollama原生API请求。

    Args:
        request: 请求对象。
        path: 请求路径。

    Returns:
        来自Ollama API的响应。
    """
    try:
        logger.info(f"收到Ollama原生API请求: {request.method} {request.url.path}")

        # 检查是否是聊天完成请求
        if "chat/completions" in path:
            logger.info("检测到聊天完成请求，使用直接转发模式")

            # 获取请求体
            body_bytes = await request.body()
            body = {}
            if body_bytes:
                try:
                    import json
                    body = json.loads(body_bytes)
                except Exception as e:
                    body = {"raw_content": body_bytes.decode("utf-8", errors="replace")}
            else:
                body = {}

            # 执行安全检测
            # 创建拦截请求用于安全检测
            intercepted_request = await _create_intercepted_request(request, path)

            # 检查API密钥
            from src.security.api_auth import api_key_manager, extract_api_key_from_request
            api_key = extract_api_key_from_request(request)

            if not api_key or not api_key_manager.validate_api_key(api_key):
                logger.warning(f"API密钥验证失败: 缺少API密钥或API密钥无效")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": {
                            "message": "请求被安全防火墙拦截: 缺少API密钥",
                            "type": "security_violation",
                            "code": 403,
                            "details": {"reason": "missing_api_key"}
                        }
                    },
                )

            if security_detector is not None:
                security_result = await security_detector.check_request(intercepted_request)
                if not security_result.is_allowed:
                    logger.warning(f"安全检测失败: {security_result.reason}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": {
                                "message": f"本地大模型防护系统阻止了请求: {security_result.reason}",
                                "type": "security_violation",
                                "code": 403,
                                "details": security_result.details if hasattr(security_result, 'details') else None
                            }
                        },
                    )

            # 获取对话ID
            from src.security.conversation_tracker import conversation_tracker
            conversation_id, _ = conversation_tracker.process_request(intercepted_request)
            logger.info(f"Ollama代理: 处理对话 {conversation_id}")

            # 使用aiohttp直接与Ollama通信

            # 构建请求数据
            ollama_request = {
                "model": body.get("model", "tinyllama:latest"),
                "messages": body.get("messages", []),
                "stream": False  # 强制使用非流式响应，避免流式响应处理问题
            }

            # 添加其他可选参数
            if "temperature" in body:
                ollama_request["temperature"] = body["temperature"]
            if "max_tokens" in body:
                ollama_request["max_tokens"] = body["max_tokens"]

            try:
                # 使用aiohttp发送请求
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:11434/api/chat",
                        json=ollama_request,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        # 获取响应
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Ollama API返回错误: {response.status} - {error_text}")
                            return JSONResponse(
                                content={"error": f"Ollama API返回错误: {response.status} - {error_text}"},
                                status_code=response.status
                            )

                        # 由于我们已经强制使用非流式响应，这里直接处理非流式响应
                        # 获取响应内容
                        ollama_response = await response.json()

                        # 构建OpenAI格式的响应
                        openai_format_response = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": body.get('model', 'unknown'),
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {
                                        "role": "assistant",
                                        "content": ollama_response.get("message", {}).get("content", "")
                                    },
                                    "finish_reason": "stop"
                                }
                            ],
                            "usage": {
                                "prompt_tokens": ollama_response.get('prompt_eval_count', 0),
                                "completion_tokens": ollama_response.get('eval_count', 0),
                                "total_tokens": (ollama_response.get('prompt_eval_count', 0) + ollama_response.get('eval_count', 0))
                            }
                        }

                        # 返回OpenAI格式的响应
                        return JSONResponse(
                            content=openai_format_response,
                            status_code=200
                        )

            except Exception as e:
                logger.exception(f"与Ollama通信时出错: {str(e)}")
                return JSONResponse(
                    content={"error": f"与Ollama通信时出错: {str(e)}"},
                    status_code=500
                )
        elif path == "models":
            # 处理模型列表请求
            logger.info("检测到模型列表请求，使用直接转发模式")

            # 检查API密钥
            from src.security.api_auth import api_key_manager, extract_api_key_from_request
            api_key = extract_api_key_from_request(request)

            if not api_key or not api_key_manager.validate_api_key(api_key):
                logger.warning(f"API密钥验证失败: 缺少API密钥或API密钥无效")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": {
                            "message": "请求被安全防火墙拦截: 缺少API密钥",
                            "type": "security_violation",
                            "code": 403,
                            "details": {"reason": "missing_api_key"}
                        }
                    },
                )

            # 获取Ollama模型列表
            try:
                import subprocess
                import json

                # 使用curl命令获取Ollama模型列表
                curl_cmd = "curl -s http://localhost:11434/api/tags"
                result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error(f"获取Ollama模型列表失败: {result.stderr}")
                    return JSONResponse(
                        content={"error": f"获取Ollama模型列表失败: {result.stderr}"},
                        status_code=500
                    )

                # 解析Ollama模型列表
                ollama_models = json.loads(result.stdout)

                # 转换为OpenAI格式的模型列表
                openai_models = {
                    "object": "list",
                    "data": []
                }

                for model in ollama_models.get("models", []):
                    model_name = model.get("name")
                    openai_models["data"].append({
                        "id": model_name,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "ollama",
                        "permission": [],
                        "root": model_name,
                        "parent": None
                    })

                # 返回OpenAI格式的模型列表
                return JSONResponse(
                    content=openai_models,
                    status_code=200
                )

            except Exception as e:
                logger.exception(f"获取Ollama模型列表时出错: {str(e)}")
                return JSONResponse(
                    content={"error": f"获取Ollama模型列表时出错: {str(e)}"},
                    status_code=500
                )
        else:
            # 对于非聊天完成请求，使用原来的方式处理
            # 创建拦截请求
            intercepted_request = await _create_intercepted_request(request, path)

            # 检查API密钥
            from src.security.api_auth import api_key_manager, extract_api_key_from_request
            api_key = extract_api_key_from_request(request)

            if not api_key or not api_key_manager.validate_api_key(api_key):
                logger.warning(f"API密钥验证失败: 缺少API密钥或API密钥无效")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": {
                            "message": "请求被安全防火墙拦截: 缺少API密钥",
                            "type": "security_violation",
                            "code": 403,
                            "details": {"reason": "missing_api_key"}
                        }
                    },
                )

            # 执行安全检测
            if security_detector is not None:
                security_result = await security_detector.check_request(intercepted_request)
                if not security_result.is_allowed:
                    logger.warning(f"安全检测失败: {security_result.reason}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": {
                                "message": f"本地大模型防护系统阻止了请求: {security_result.reason}",
                                "type": "security_violation",
                                "code": 403,
                                "details": security_result.details if hasattr(security_result, 'details') else None
                            }
                        },
                    )

            # 获取对话ID
            from src.security.conversation_tracker import conversation_tracker
            conversation_id, _ = conversation_tracker.process_request(intercepted_request)
            logger.info(f"Ollama代理: 处理对话 {conversation_id}")

            # 转发请求到Ollama
            response = await _forward_to_ollama(intercepted_request)

            # 对于流式响应，跳过内容检查
            if response.is_streaming:
                logger.info("检测到流式响应，跳过内容检查")
            else:
                # 执行安全检测
                security_result = await security_detector.check_response(response, conversation_id)
                if not security_result.is_allowed:
                    logger.warning(f"响应安全检测失败: {security_result.reason}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": {
                                "message": f"本地大模型防护系统阻止了响应: {security_result.reason}",
                                "type": "security_violation",
                                "code": 403,
                                "details": security_result.details if hasattr(security_result, 'details') else None
                            }
                        },
                    )

            # 返回响应
            return _create_response(response)

    except Exception as e:
        logger.exception(f"处理Ollama原生API请求时出错: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": f"处理请求时出错: {str(e)}",
                    "type": "internal_error",
                    "code": 500
                }
            },
        )


async def _create_intercepted_request(request: Request, path: str) -> InterceptedRequest:
    """创建拦截请求对象。

    Args:
        request: 原始请求。
        path: 请求路径。

    Returns:
        拦截请求对象。
    """
    # 获取请求头
    headers = dict(request.headers)

    # 获取请求体
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body_bytes = await request.body()
        if body_bytes:
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                body = {"raw_content": body_bytes.decode("utf-8", errors="replace")}

    # 确定提供商
    provider = "ollama"

    # 创建拦截请求
    return InterceptedRequest(
        method=request.method,
        url=str(request.url),
        headers=headers,
        body=body,
        query_params=dict(request.query_params),
        timestamp=time.time(),
        client_ip=request.client.host if request.client else "",
        provider=provider,
        path=path,  # 使用path参数
    )


async def _forward_to_ollama(intercepted_request: InterceptedRequest) -> InterceptedResponse:
    """转发请求到Ollama。

    Args:
        intercepted_request: 拦截请求。

    Returns:
        拦截响应。
    """
    start_time = time.time()

    # 准备请求参数
    method = intercepted_request.method
    # 修改URL，确保正确转发到Ollama API
    original_url = str(intercepted_request.url)
    logger.info(f"原始URL: {original_url}")

    # 从URL中提取域名和端口部分
    from urllib.parse import urlparse
    parsed_url = urlparse(original_url)
    logger.info(f"解析后的URL: {parsed_url}, netloc: {parsed_url.netloc}, path: {parsed_url.path}")

    # 构建新的URL - 注意：Ollama的chat completions API是/api/chat，而不是/api/chat/completions
    if "chat/completions" in parsed_url.path:
        url = "http://localhost:11434/api/chat"
    else:
        # 处理其他API路径
        url = f"http://localhost:11434/api{parsed_url.path.replace('/v1', '')}"
    logger.info(f"转发到Ollama的URL: {url}")
    headers = intercepted_request.headers
    data = json.dumps(intercepted_request.body) if intercepted_request.body else None

    # 使用aiohttp转发请求
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method=method, url=url, headers=headers, data=data
            ) as response:
                # 检查是否是流式响应
                if response.headers.get("Transfer-Encoding") == "chunked" or response.headers.get("Content-Type") == "text/event-stream":
                    # 对于流式响应，我们返回一个特殊的响应对象
                    return InterceptedResponse(
                        status_code=response.status,
                        headers=dict(response.headers),
                        body={"streaming": True, "message": "Streaming response from Ollama"},
                        timestamp=time.time(),
                        latency=time.time() - start_time,
                        is_streaming=True,
                        raw_response=response  # 保存原始响应对象以便后续处理
                    )
                else:
                    # 对于非流式响应，按原来的方式处理
                    response_body = None
                    response_text = await response.text()
                    if response_text:
                        try:
                            response_body = json.loads(response_text)
                        except json.JSONDecodeError:
                            response_body = {"raw_content": response_text}

                    # 创建拦截响应
                    return InterceptedResponse(
                        status_code=response.status,
                        headers=dict(response.headers),
                        body=response_body,
                        timestamp=time.time(),
                        latency=time.time() - start_time,
                    )
    except Exception as e:
        logger.exception(f"转发请求到Ollama时出错: {e}")
        return InterceptedResponse(
            status_code=500,
            headers={"Content-Type": "application/json"},
            body={
                "error": {
                    "message": f"转发请求到Ollama时出错: {str(e)}",
                    "type": "internal_error",
                    "code": 500,
                }
            },
            timestamp=time.time(),
            latency=time.time() - start_time,
        )


def _create_response(intercepted_response: InterceptedResponse) -> Response:
    """创建FastAPI响应。

    Args:
        intercepted_response: 拦截响应。

    Returns:
        FastAPI响应。
    """
    # 检查是否是流式响应
    if intercepted_response.is_streaming and intercepted_response.raw_response:
        # 对于流式响应，我们需要直接返回原始响应的内容
        # 但是不能直接使用raw_response.content，因为这会导致错误

        # 创建一个生成器函数来读取原始响应的内容
        async def stream_generator():
            try:
                # 使用aiohttp的方式读取内容
                async for chunk in intercepted_response.raw_response.content:
                    yield chunk
            except Exception as e:
                logger.error(f"流式响应读取错误: {e}")
                # 如果出错，返回一个错误消息
                yield json.dumps({"error": "流式响应读取错误"}).encode()

        # 设置响应头
        headers = dict(intercepted_response.headers or {})
        # 移除Content-Length头，因为我们使用的是流式传输
        if "Content-Length" in headers:
            del headers["Content-Length"]

        # 设置正确的内容类型
        headers["Content-Type"] = "application/json"

        # 创建流式响应
        return StreamingResponse(
            stream_generator(),
            status_code=intercepted_response.status_code,
            headers=headers
        )
    else:
        # 对于非流式响应，按原来的方式处理
        content = (
            json.dumps(intercepted_response.body)
            if intercepted_response.body
            else ""
        )

        # 创建响应
        return Response(
            content=content,
            status_code=intercepted_response.status_code,
            headers=intercepted_response.headers,
        )
