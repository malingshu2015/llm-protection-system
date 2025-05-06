"""安全中间件模块。"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import settings
from src.logger import logger
from src.security.api_auth import extract_api_key_from_request, api_key_manager
from src.security.rate_limiter import rate_limiter
from src.security.content_masker import content_masker


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件，用于API密钥认证和速率限制。"""

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

        # 处理请求
        response = await call_next(request)

        # 内容脱敏
        if settings.security.enable_content_masking and isinstance(response, Response):
            # 只处理JSON响应
            if response.headers.get("content-type", "").startswith("application/json"):
                try:
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
