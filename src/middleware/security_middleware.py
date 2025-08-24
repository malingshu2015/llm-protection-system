"""安全中间件模块。"""

import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import settings
from src.logger import logger
from src.security.api_auth import extract_api_key_from_request, api_key_manager
from src.security.rate_limiter import rate_limiter
from src.security.content_masker import content_masker


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件，用于API密钥认证、速率限制和实时监控。"""

    async def dispatch(self, request: Request, call_next):
        """处理请求。

        Args:
            request: 请求对象。
            call_next: 下一个中间件或路由处理函数。

        Returns:
            响应对象。
        """
        # 跳过OPTIONS请求
        if request.method == "OPTIONS":
            return await call_next(request)

        # 跳过不需要认证的路径
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # 收集实时监控数据
        start_time = time.time()
        client_info = self._extract_client_info(request)
        input_content = None

        # API密钥认证
        if settings.security.enable_api_auth:
            api_key = extract_api_key_from_request(request)
            if not api_key:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "缺少API密钥",
                        "type": "authentication_error",
                        "code": 403,
                    },
                )

            if not api_key_manager.validate_api_key(api_key):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "无效的API密钥",
                        "type": "authentication_error",
                        "code": 403,
                    },
                )

            # 检查模型访问权限
            if "/api/v1/ollama/chat" in request.url.path:
                try:
                    # 尝试从请求体中获取模型名称
                    body = await request.json()
                    model = body.get("model", "")
                    if model and not api_key_manager.check_model_access(api_key, model):
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": f"没有权限访问模型: {model}",
                                "type": "authorization_error",
                                "code": 403,
                            },
                        )
                except Exception as e:
                    logger.error(f"检查模型访问权限失败: {e}")

        # 速率限制
        if settings.security.enable_rate_limiting:
            is_allowed, rate_limit_info = await rate_limiter.check_rate_limit(request)
            if not is_allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "请求频率超过限制",
                        "type": "rate_limit_error",
                        "code": 429,
                        "rate_limit": rate_limit_info,
                    },
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                        "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                        "X-RateLimit-Reset": str(rate_limit_info["reset"]),
                        "X-RateLimit-Used": str(rate_limit_info["used"]),
                        "Retry-After": str(rate_limit_info["reset"] - int(time.time())),
                    },
                )

        # 尝试提取输入内容用于实时监控
        if request.url.path.startswith("/v1/chat/completions") or "chat/completions" in request.url.path:
            try:
                # 尝试从request中获取已缓存的body
                if hasattr(request, '_body'):
                    body_bytes = request._body
                    if body_bytes:
                        import json as json_module
                        body_data = json_module.loads(body_bytes.decode('utf-8'))
                        messages = body_data.get('messages', [])
                        # 获取最后一条用户消息作为输入内容
                        for msg in reversed(messages):
                            if msg.get('role') == 'user':
                                input_content = msg.get('content', '')[:500]  # 限制长度
                                break
            except Exception as e:
                logger.debug(f"提取输入内容失败: {e}")

        # 处理请求
        response = await call_next(request)
        
        # 计算响应时间
        response_time = (time.time() - start_time) * 1000

        # 内容脱敏
        if settings.security.enable_content_masking and isinstance(response, Response):
            # 跳过StreamingResponse，因为它没有body属性
            from fastapi.responses import StreamingResponse
            if isinstance(response, StreamingResponse):
                logger.debug("跳过StreamingResponse的内容脱敏处理")
                return response
                
            # 只处理JSON响应
            if response.headers.get("content-type", "").startswith("application/json"):
                try:
                    # 检查response是否有body属性
                    if not hasattr(response, 'body'):
                        logger.debug("响应对象没有body属性，跳过内容脱敏")
                        return response
                        
                    # 将响应转换为InterceptedResponse
                    from src.models_interceptor import InterceptedResponse
                    import json

                    response_body = json.loads(response.body.decode("utf-8"))
                    intercepted_response = InterceptedResponse(
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        body=response_body,
                        timestamp=time.time(),
                        latency=0.0,
                    )

                    # 处理响应
                    processed_response = content_masker.process_response(intercepted_response)

                    # 如果响应被处理，更新响应内容
                    if "X-Content-Masked" in processed_response.headers:
                        response_body = json.dumps(processed_response.body).encode("utf-8")
                        response = Response(
                            content=response_body,
                            status_code=processed_response.status_code,
                            headers=processed_response.headers,
                            media_type="application/json",
                        )
                except Exception as e:
                    logger.error(f"处理响应内容失败: {e}")

        # 广播实时监控事件
        if input_content and not request.url.path.startswith("/api/v1/realtime"):
            try:
                from src.web.realtime_monitor_api import broadcast_realtime_event
                import asyncio
                
                # 异步广播事件，不阻塞响应
                asyncio.create_task(broadcast_realtime_event(
                    content=input_content,
                    client_type=client_info['type'],
                    client_id=client_info['id'],
                    detection_result=None,  # 在这里无法获取检测结果
                    response_time_ms=response_time
                ))
            except Exception as e:
                logger.debug(f"广播实时监控事件失败: {e}")

        return response

    def _is_public_path(self, path: str) -> bool:
        """检查路径是否是公开路径。

        Args:
            path: 请求路径。

        Returns:
            是否是公开路径。
        """
        public_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/version",
            "/api/v1/login",
            "/api/v1/register",
            "/static/",
            "/favicon.ico",
        ]

        for public_path in public_paths:
            if path.startswith(public_path):
                return True

        return False

    def _extract_client_info(self, request: Request) -> dict:
        """提取客户端信息用于实时监控。
        
        Args:
            request: 请求对象
            
        Returns:
            包含客户端类型和ID的字典
        """
        # 获取User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        client_ip = request.client.host if request.client else "unknown"
        
        # 根据User-Agent和其他头信息判断客户端类型
        if "cherry studio" in user_agent or "cherry-studio" in user_agent:
            client_type = "Cherry Studio"
        elif "chatbox" in user_agent:
            client_type = "ChatBox"
        elif "open-webui" in user_agent or "openwebui" in user_agent:
            client_type = "Open WebUI"
        elif "postman" in user_agent:
            client_type = "Postman"
        elif "curl" in user_agent:
            client_type = "cURL"
        elif "python" in user_agent:
            client_type = "Python Client"
        elif "javascript" in user_agent or "axios" in user_agent or "fetch" in user_agent:
            client_type = "Web Client"
        elif "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
            client_type = "Mobile App"
        elif "mozilla" in user_agent or "chrome" in user_agent or "safari" in user_agent:
            client_type = "Web Browser"
        else:
            client_type = "API Client"
            
        # 生成客户端ID (IP地址 + 时间戳的简化版本)
        client_id = f"{client_ip}_{int(time.time()) % 10000}"
        
        return {
            "type": client_type,
            "id": client_id,
            "ip": client_ip,
            "user_agent": request.headers.get("user-agent", "")
        }
