"""Ollama API代理路由，用于拦截和处理发送到Ollama原生API的请求。"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
from json import JSONEncoder

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Body
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.config import settings
from src.logger import logger
from src.proxy.interceptor import HTTPInterceptor
from src.security.detector import SecurityDetector
from src.models_interceptor import DetectionResult, InterceptedRequest, InterceptedResponse


router = APIRouter()
interceptor = None
security_detector = None


@router.on_event("startup")
async def startup_event():
    """Start the components on startup."""
    global interceptor, security_detector

    # Initialize components
    from src.proxy.interceptor import HTTPInterceptor
    from src.security.detector import SecurityDetector

    security_detector = SecurityDetector()
    interceptor = HTTPInterceptor()


@router.on_event("shutdown")
async def shutdown_event():
    """Stop the components on shutdown."""
    global interceptor

    # Close the interceptor if it exists
    if interceptor is not None:
        await interceptor.close()


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
            if body_bytes:
                try:
                    body = json.loads(body_bytes)
                except json.JSONDecodeError:
                    body = {"raw_content": body_bytes.decode("utf-8", errors="replace")}
            else:
                body = {}

            # 执行安全检测
            # 创建拦截请求用于安全检测
            intercepted_request = await _create_intercepted_request(request, path)

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

            # 使用httpx直接转发请求并返回流式响应
            import httpx

            # 构建Ollama API URL
            url = "http://localhost:11434/api/chat"

            # 使用子进程调用curl命令直接与Ollama通信
            import subprocess
            import shlex

            # 构建curl命令
            curl_cmd = f"curl -s -X POST http://localhost:11434/api/chat -H 'Content-Type: application/json' -d '{json.dumps(body)}'"

            # 执行curl命令
            try:
                # 使用subprocess执行curl命令
                process = subprocess.Popen(
                    shlex.split(curl_cmd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                # 获取输出
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    error_msg = f"Curl命令执行失败: {stderr.decode('utf-8')}"
                    logger.error(error_msg)
                    return JSONResponse(
                        content={"error": error_msg},
                        status_code=500
                    )

                # 返回curl命令的输出
                return Response(
                    content=stdout,
                    media_type="application/json"
                )

            except Exception as e:
                error_msg = f"执行curl命令失败: {str(e)}"
                logger.error(error_msg)
                return JSONResponse(
                    content={"error": error_msg},
                    status_code=500
                )
        else:
            # 对于非聊天完成请求，使用原来的方式处理
            # 创建拦截请求
            intercepted_request = await _create_intercepted_request(request, path)

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
        # 对于流式响应，我们暂时返回一个简单的JSON响应
        # 这是一个临时解决方案，直到我们能够正确处理流式响应
        return JSONResponse(
            content={
                "message": "流式响应暂不支持，请使用非流式模式",
                "status": "streaming_not_supported"
            },
            status_code=200
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
