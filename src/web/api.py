"""API router for the web interface."""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
from json import JSONEncoder

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Body
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# 尝试导入ollama，如果不可用则设置为None
print("=== 开始导入Ollama模块 ===")
import sys
print(f"Python路径: {sys.path}")

try:
    import ollama
    import os
    # 设置 Ollama 的连接地址
    os.environ['OLLAMA_HOST'] = 'http://localhost:11434'
    # 设置连接超时时间
    ollama.Client(host='http://localhost:11434', timeout=30)
    OLLAMA_AVAILABLE = True
    print("=== Ollama模块已成功导入 ===")
except ImportError as e:
    print(f"=== Ollama模块导入失败: {e} ===")
    ollama = None
    OLLAMA_AVAILABLE = False
except Exception as e:
    print(f"=== Ollama模块初始化失败: {e} ===")
    ollama = None
    OLLAMA_AVAILABLE = False

from src.config import settings
from src.logger import logger
from src.proxy.interceptor import HTTPInterceptor
from src.proxy.queue_manager import Priority, QueueManager
from src.security.detector import SecurityDetector
from src.models_interceptor import DetectionResult


router = APIRouter()
queue_manager = None
interceptor = None
security_detector = None

# 自定义 JSON 编码器
class OllamaJSONEncoder(JSONEncoder):
    def default(self, obj):
        # 如果是 Ollama 的 ChatResponse 对象
        if hasattr(obj, 'model_dump'):
            # 如果是 Pydantic 模型，使用 model_dump()
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            # 如果是普通对象，使用 __dict__
            return obj.__dict__
        # 如果是其他类型，使用默认处理
        return super().default(obj)


# 缓存字典，用于存储流式响应的结果
# 键是请求的哈希值，值是响应内容
_response_cache = {}

# 缓存过期时间（秒）
_CACHE_EXPIRY = 300  # 5分钟

# 缓存最大条目
_MAX_CACHE_ENTRIES = 100

# 批处理大小
_BATCH_SIZE = 10

# 模型下载进度信息
# 键是模型名称，值是包含下载进度信息的字典
# 格式: {
#   "status": "downloading" | "completed" | "failed",
#   "progress": 0.75,  # 0.0 到 1.0 之间的浮点数
#   "downloaded_size": 1024000,  # 已下载的字节数
#   "total_size": 2048000,  # 总字节数
#   "speed": 1024,  # 下载速度（字节/秒）
#   "eta": 60,  # 预计剩余时间（秒）
#   "error": "错误信息",  # 如果失败，包含错误信息
#   "start_time": 1619712345.67,  # 开始时间（时间戳）
#   "update_time": 1619712400.00  # 最后更新时间（时间戳）
# }
_model_download_progress = {}

async def get_latest_ollama_models():
    """从 Ollama 官方获取最新模型列表。

    Returns:
        最新的 Ollama 模型列表。
    """
    try:
        # 尝试导入所需的库
        try:
            import aiohttp
        except ImportError:
            logger.warning("无法导入 aiohttp 库，尝试使用 requests 库")
            import requests

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("无法导入 BeautifulSoup 库，将使用正则表达式解析")
            import re

        logger.info("开始从 Ollama 官方获取最新模型列表...")

        # 定义一些示例最新模型，以防无法获取实际数据
        fallback_models = [
            {
                "name": "llama3:latest",
                "description": "Meta的最新Llama 3模型",
                "tags": ["text", "chat", "general"],
                "is_latest": True
            },
            {
                "name": "phi3:latest",
                "description": "Microsoft的最新Phi-3模型",
                "tags": ["text", "chat", "general"],
                "is_latest": True
            },
            {
                "name": "mistral:latest",
                "description": "Mistral AI的最新开源模型",
                "tags": ["text", "chat", "general"],
                "is_latest": True
            }
        ]

        # 尝试使用 aiohttp 获取 Ollama 模型页面
        try:
            if 'aiohttp' in sys.modules:
                async with aiohttp.ClientSession() as session:
                    # 获取最新模型页面
                    async with session.get("https://ollama.com/search?o=newest") as response:
                        if response.status != 200:
                            logger.warning(f"获取 Ollama 最新模型页面失败，状态码: {response.status}")
                            return fallback_models

                        html = await response.text()
            elif 'requests' in sys.modules:
                # 如果没有 aiohttp，使用 requests
                response = requests.get("https://ollama.com/search?o=newest")
                if response.status_code != 200:
                    logger.warning(f"获取 Ollama 最新模型页面失败，状态码: {response.status_code}")
                    return fallback_models

                html = response.text
            else:
                logger.warning("无法获取 Ollama 最新模型页面，没有可用的 HTTP 客户端库")
                return fallback_models

            # 解析 HTML
            models = []

            if 'BeautifulSoup' in sys.modules:
                # 使用 BeautifulSoup 解析 HTML
                soup = BeautifulSoup(html, 'html.parser')

                # 查找模型列表
                model_elements = soup.select('.model-card')

                for element in model_elements:
                    try:
                        # 获取模型名称
                        name_element = element.select_one('.model-name')
                        if not name_element:
                            continue

                        model_name = name_element.text.strip()

                        # 获取模型描述
                        description_element = element.select_one('.model-description')
                        description = description_element.text.strip() if description_element else f"{model_name} 模型"

                        # 获取模型标签
                        tags = []
                        tag_elements = element.select('.model-tag')
                        for tag_element in tag_elements:
                            tag = tag_element.text.strip().lower()
                            if tag:
                                tags.append(tag)

                        # 如果没有标签，添加默认标签
                        if not tags:
                            tags = ["text", "general"]

                        # 添加到模型列表
                        models.append({
                            "name": model_name,
                            "description": description,
                            "tags": tags,
                            "is_latest": True  # 标记为最新模型
                        })
                    except Exception as e:
                        logger.warning(f"解析模型元素时出错: {e}")
            else:
                # 使用正则表达式解析 HTML
                # 这是一个简化的解析，可能不如 BeautifulSoup 准确
                model_matches = re.findall(r'<div[^>]*class="[^"]*model-card[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)

                for model_html in model_matches[:10]:  # 只处理前10个匹配项
                    try:
                        # 尝试提取模型名称
                        name_match = re.search(r'<div[^>]*class="[^"]*model-name[^"]*"[^>]*>(.*?)</div>', model_html, re.DOTALL)
                        if not name_match:
                            continue

                        model_name = name_match.group(1).strip()

                        # 尝试提取模型描述
                        description_match = re.search(r'<div[^>]*class="[^"]*model-description[^"]*"[^>]*>(.*?)</div>', model_html, re.DOTALL)
                        description = description_match.group(1).strip() if description_match else f"{model_name} 模型"

                        # 添加到模型列表
                        models.append({
                            "name": model_name,
                            "description": description,
                            "tags": ["text", "general"],  # 默认标签
                            "is_latest": True  # 标记为最新模型
                        })
                    except Exception as e:
                        logger.warning(f"使用正则表达式解析模型元素时出错: {e}")

            if models:
                logger.info(f"成功从 Ollama 官方获取 {len(models)} 个最新模型")
                return models
            else:
                logger.warning("未能从 Ollama 官方获取任何模型，使用备用模型列表")
                return fallback_models

        except Exception as e:
            logger.warning(f"获取 Ollama 最新模型页面时出错: {e}")
            return fallback_models

    except ImportError as e:
        logger.warning(f"导入依赖库失败，无法获取最新 Ollama 模型: {e}")
        return []
    except Exception as e:
        logger.warning(f"获取最新 Ollama 模型时出错: {e}")
        return []

async def stream_ollama_response(model: str, messages: List[Dict], options: Dict) -> AsyncIterator[str]:
    """流式返回 Ollama 响应。

    Args:
        model: 模型名称。
        messages: 消息列表。
        options: 选项。

    Yields:
        流式响应的每一部分。
    """
    global _response_cache

    # 清理过期缓存
    current_time = time.time()
    expired_keys = [k for k, v in _response_cache.items() if current_time - v['timestamp'] > _CACHE_EXPIRY]
    for k in expired_keys:
        del _response_cache[k]

    # 如果缓存过大，删除最早的条目
    if len(_response_cache) > _MAX_CACHE_ENTRIES:
        oldest_key = min(_response_cache.keys(), key=lambda k: _response_cache[k]['timestamp'])
        del _response_cache[oldest_key]

    # 生成请求的哈希值作为缓存键
    cache_key = hash(f"{model}_{str(messages)}_{str(options)}")

    # 检查缓存
    if cache_key in _response_cache:
        logger.info(f"使用缓存的流式响应: {model}")
        for chunk in _response_cache[cache_key]['chunks']:
            yield chunk
        return

    # 初始化缓存条目
    _response_cache[cache_key] = {
        'timestamp': time.time(),
        'chunks': []
    }

    try:
        logger.info(f"开始流式调用 Ollama 模型: {model}")

        # 尝试使用curl命令调用Ollama流式 API
        try:
            import subprocess
            import json
            import asyncio
            from asyncio import create_subprocess_exec
            from asyncio.subprocess import PIPE

            logger.info(f"尝试使用curl命令调用Ollama流式 API...")

            # 准备请求数据
            request_data = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": options
            }

            # 将请求数据转换为JSON字符串
            request_json = json.dumps(request_data)

            # 使用asyncio创建子进程
            proc = await create_subprocess_exec(
                'curl', '-s', '-N', '-X', 'POST', 'http://localhost:11434/api/chat',
                '-H', 'Content-Type: application/json',
                '-d', request_json,
                stdout=PIPE, stderr=PIPE
            )

            # 初始化缓冲区和计数器
            buffer = []
            count = 0

            # 读取流式输出
            async for line in proc.stdout:
                line = line.decode('utf-8').strip()
                if line:
                    try:
                        # 尝试解析JSON，确保是有效的JSON对象
                        json.loads(line)
                        # 将每一行格式化为SSE格式
                        formatted_line = f"data: {line}\n\n"
                        buffer.append(formatted_line)
                        count += 1

                        # 当缓冲区达到批处理大小或者是最后一个响应时，发送批量数据
                        if count >= _BATCH_SIZE or '"done":true' in line:
                            # 将批量数据添加到缓存
                            _response_cache[cache_key]['chunks'].extend(buffer)

                            # 发送批量数据
                            for chunk in buffer:
                                yield chunk

                            # 重置缓冲区和计数器
                            buffer = []
                            count = 0
                    except json.JSONDecodeError as e:
                        # 使用警告级别记录日志，避免使用settings.DEBUG
                        logger.warning(f"解析流式响应行失败: {e}, 行内容: {line[:100]}")
                        # 忽略无效的JSON行

            # 如果缓冲区中还有数据，发送剩余数据
            if buffer:
                # 将批量数据添加到缓存
                _response_cache[cache_key]['chunks'].extend(buffer)

                # 发送批量数据
                for chunk in buffer:
                    yield chunk

            # 等待进程结束
            await proc.wait()

            # 发送结束信号
            done_signal = "data: [DONE]\n\n"
            _response_cache[cache_key]['chunks'].append(done_signal)
            yield done_signal
            return

        except Exception as e:
            # 使用警告级别记录日志，避免使用settings.DEBUG
            logger.warning(f"使用curl调用Ollama流式 API时出错: {str(e)[:100]}")

            # 如果Ollama模块可用，尝试使用Python客户端
            if OLLAMA_AVAILABLE:
                try:
                    # 直接调用 Ollama 的流式 API
                    # 注意：根据 Ollama Python 客户端的文档，我们需要在同步上下文中调用 ollama.chat
                    def call_ollama():
                        # 创建一个新的客户端实例，设置更长的超时时间
                        client = ollama.Client(host='http://localhost:11434', timeout=60)
                        return client.chat(
                            model=model,
                            messages=messages,
                            stream=True,
                            options=options
                        )

                    # 在单独的线程中运行同步函数
                    stream = await asyncio.wait_for(
                        asyncio.to_thread(call_ollama),
                        timeout=120
                    )

                    # 初始化缓冲区和计数器
                    buffer = []
                    count = 0

                    # 处理流式响应
                    for chunk in stream:
                        try:
                            # 使用自定义 JSON 编码器将对象转换为 JSON 字符串
                            chunk_json = json.dumps(chunk, cls=OllamaJSONEncoder)
                            # 将每一行格式化为SSE格式
                            formatted_chunk = f"data: {chunk_json}\n\n"
                            buffer.append(formatted_chunk)
                            count += 1

                            # 当缓冲区达到批处理大小或者是最后一个响应时，发送批量数据
                            if count >= _BATCH_SIZE or chunk.get('done', False):
                                # 将批量数据添加到缓存
                                _response_cache[cache_key]['chunks'].extend(buffer)

                                # 发送批量数据
                                for chunk_data in buffer:
                                    yield chunk_data

                                # 重置缓冲区和计数器
                                buffer = []
                                count = 0
                        except Exception as chunk_error:
                            # 使用警告级别记录日志，避免使用settings.DEBUG
                            logger.warning(f"处理流式响应块失败: {chunk_error}, 块内容: {str(chunk)[:100]}")
                            # 忽略处理失败的块

                    # 如果缓冲区中还有数据，发送剩余数据
                    if buffer:
                        # 将批量数据添加到缓存
                        _response_cache[cache_key]['chunks'].extend(buffer)

                        # 发送批量数据
                        for chunk_data in buffer:
                            yield chunk_data

                    # 发送结束信号
                    done_signal = "data: [DONE]\n\n"
                    _response_cache[cache_key]['chunks'].append(done_signal)
                    yield done_signal
                    return

                except asyncio.TimeoutError:
                    logger.error(f"调用 Ollama 流式 API 超时")
                    error_json = json.dumps({"error": "调用 Ollama 流式 API 超时"})
                    yield f"data: {error_json}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                except Exception as e:
                    logger.exception(f"调用 Ollama Python客户端流式 API 时出错: {e}")

            # 所有方法均失败，返回错误
            error_json = json.dumps({"error": f"调用 Ollama 流式 API 时出错: {str(e)}"})
            yield f"data: {error_json}\n\n"
            yield "data: [DONE]\n\n"
            return


    except Exception as e:
        # 如果出错，发送错误信息
        logger.exception(f"流式响应处理失败: {e}")
        error_json = json.dumps({"error": f"流式响应处理失败: {str(e)}"})
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n"


@router.on_event("startup")
async def startup_event():
    """Start the queue manager on startup."""
    global queue_manager, interceptor, security_detector

    # Initialize components
    from src.proxy.queue_manager import QueueManager
    from src.proxy.interceptor import HTTPInterceptor
    from src.security.detector import SecurityDetector

    queue_manager = QueueManager()
    security_detector = SecurityDetector()
    interceptor = HTTPInterceptor()

    # Start the queue manager
    await queue_manager.start()


@router.on_event("shutdown")
async def shutdown_event():
    """Stop the queue manager on shutdown."""
    global queue_manager, interceptor

    # Stop the queue manager if it exists
    if queue_manager is not None:
        await queue_manager.stop()

    # Close the interceptor if it exists
    if interceptor is not None:
        await interceptor.close()


@router.get("/api/v1/health")
async def health_check():
    """Health check endpoint.

    Returns:
        A JSON response with the service status.
    """
    return {"status": "ok", "version": "0.1.0"}


@router.get("/api/v1/metrics")
async def get_metrics():
    """Get service metrics.

    Returns:
        A JSON response with service metrics.
    """
    queue_sizes = queue_manager.queue.get_queue_sizes()

    return {
        "queue_sizes": queue_sizes,
        "active_requests": queue_sizes["active_requests"],
    }


@router.post("/api/v1/proxy")
async def proxy_request(request: Request):
    """Proxy an LLM API request.

    Args:
        request: The incoming request.

    Returns:
        The response from the LLM API.
    """
    # Get priority from headers
    priority_header = request.headers.get("X-Priority", "normal").lower()

    if priority_header == "high":
        priority = Priority.HIGH
    elif priority_header == "low":
        priority = Priority.LOW
    else:
        priority = Priority.NORMAL

    # Enqueue the request
    success, error = await queue_manager.enqueue_request(request, priority)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error or "Service unavailable",
        )

    # Process the request directly for now (in the future, this will be handled by the queue)
    return await interceptor.intercept(request)


# 定义 Ollama 请求模型
class OllamaMessage(BaseModel):
    role: str
    content: str

class OllamaRequest(BaseModel):
    model: str
    messages: List[OllamaMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

# 添加 Ollama 专用路由
@router.post("/api/v1/ollama/chat")
async def ollama_chat(request: OllamaRequest = Body(...)):
    """直接使用 Ollama 进行聊天请求。

    Args:
        request: Ollama 聊天请求。

    Returns:
        Ollama 的响应。
    """
    print(f"=== 调用ollama_chat函数，OLLAMA_AVAILABLE={OLLAMA_AVAILABLE} ===")
    # 即使Ollama模块不可用，也尝试使用curl调用Ollama API

    try:
        logger.info(f"直接调用 Ollama 模型: {request.model}")

        # 将 Pydantic 模型转换为 Python 字典
        messages = [msg.model_dump() for msg in request.messages]

        # 执行安全检测
        if security_detector is not None:
            # 创建一个模拟的 InterceptedRequest 对象
            from src.models_interceptor import InterceptedRequest

            # 合并所有消息内容
            all_content = ""
            for msg in request.messages:
                all_content += msg.content + "\n"

            # 创建请求对象
            intercepted_request = InterceptedRequest(
                method="POST",
                url="/api/v1/ollama/chat",
                headers={},
                body={
                    "model": request.model,
                    "messages": [msg.model_dump() for msg in request.messages]
                },
                query_params={},
                timestamp=time.time(),
                client_ip="127.0.0.1",
                provider="ollama"
            )

            # 执行安全检测
            logger.info(f"执行安全检测，文本长度: {len(all_content)}")
            logger.info(f"请求内容: {all_content[:200]}...")  # 记录请求内容的前200个字符
            security_result = await security_detector.check_request(intercepted_request)

            if not security_result.is_allowed:
                logger.warning(f"安全检测失败: {security_result.reason}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": f"本地大模型防护系统阻止了请求: {security_result.reason}",
                        "type": "security_violation",
                        "code": 403,
                        "details": security_result.details if hasattr(security_result, 'details') else None
                    },
                )

        # 调用 Ollama API
        # 根据 Ollama 客户端的支持参数进行调用
        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens

        # 如果请求流式响应，则返回 StreamingResponse
        if request.stream:
            return StreamingResponse(
                content=stream_ollama_response(request.model, messages, options),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            # 尝试使用curl命令调用Ollama API
            try:
                import subprocess
                import json

                logger.info(f"尝试使用curl命令调用Ollama API...")

                # 准备请求数据
                request_data = {
                    "model": request.model,
                    "messages": [msg.model_dump() for msg in request.messages],
                    "options": options
                }

                # 将请求数据转换为JSON字符串
                request_json = json.dumps(request_data)

                # 执行curl命令，使用流式模式获取响应，然后手动处理
                result = subprocess.run(
                    ['curl', '-s', '-N', '-X', 'POST', 'http://localhost:11434/api/chat',
                     '-H', 'Content-Type: application/json',
                     '-d', request_json],
                    capture_output=True, text=True, check=True
                )

                # 生成请求的哈希值作为缓存键
                cache_key = hash(f"{request.model}_{str(messages)}_{str(options)}")

                # 检查缓存
                if cache_key in _response_cache and 'full_response' in _response_cache[cache_key]:
                    logger.info(f"使用缓存的非流式响应: {request.model}")
                    return _response_cache[cache_key]['full_response']

                # 处理流式响应
                if result.stdout:
                    # 将响应拆分为多行，每行是一个JSON对象
                    response_lines = result.stdout.strip().split('\n')

                    # 如果有多行，处理响应
                    if response_lines:
                        # 使用列表收集内容片段，然后使用join合并，提高性能
                        content_parts = []

                        # 使用单次遍历而不是多次遍历，提高性能
                        has_done = False
                        for line in response_lines:
                            try:
                                parsed = json.loads(line)
                                if parsed.get('done', False):
                                    has_done = True
                                if 'message' in parsed and 'content' in parsed['message']:
                                    content_parts.append(parsed['message']['content'])
                            except json.JSONDecodeError:
                                # 使用警告级别记录日志，避免使用settings.DEBUG
                                logger.warning(f"解析响应行失败: {line[:100]}")
                                continue

                        if has_done or content_parts:  # 如果有done标记或者有内容，则认为有效
                            # 使用join合并字符串，比+运算符更高效
                            full_content = ''.join(content_parts)

                            # 创建最终响应
                            response_data = {
                                "model": request.model,
                                "message": {
                                    "role": "assistant",
                                    "content": full_content
                                }
                            }

                            # 将响应存入缓存
                            if cache_key not in _response_cache:
                                _response_cache[cache_key] = {'timestamp': time.time()}
                            _response_cache[cache_key]['full_response'] = response_data

                            logger.info(f"Ollama 响应成功处理")
                            return response_data
                        else:
                            logger.warning("未找到有效的Ollama响应内容")
                            raise Exception("未找到有效的Ollama响应内容")
                    else:
                        logger.warning("Ollama响应为空")
                        raise Exception("Ollama响应为空")
                else:
                    logger.warning("Ollama响应为空")
                    raise Exception("Ollama响应为空")

            except subprocess.CalledProcessError as e:
                logger.warning(f"使用curl调用Ollama API失败: {e}, stderr: {e.stderr}")
                raise Exception(f"调用Ollama API失败: {e.stderr}")

            except json.JSONDecodeError as e:
                logger.warning(f"解析Ollama响应JSON失败: {e}, 原始响应: {result.stdout[:200] if 'result' in locals() else 'N/A'}")
                raise Exception(f"解析Ollama响应失败: {e}")

            except Exception as e:
                logger.warning(f"使用curl调用Ollama API时发生未知错误: {e}")

                # 生成请求的哈希值作为缓存键
                cache_key = hash(f"{request.model}_{str(messages)}_{str(options)}")

                # 检查缓存
                if cache_key in _response_cache and 'full_response' in _response_cache[cache_key]:
                    logger.info(f"使用缓存的非流式响应: {request.model}")
                    return _response_cache[cache_key]['full_response']

                # 如果Ollama模块可用，尝试使用Python客户端
                if OLLAMA_AVAILABLE:
                    logger.info("尝试使用Ollama Python客户端...")
                    try:
                        # 创建一个新的客户端实例，设置更长的超时时间
                        client = ollama.Client(host='http://localhost:11434', timeout=60)

                        # 使用流式模式获取响应，然后手动处理
                        stream_response = client.chat(
                            model=request.model,
                            messages=messages,
                            stream=True,  # 使用流式模式
                            options=options
                        )

                        # 使用字符串连接而不是多次字符串连接，提高性能
                        content_parts = []
                        for chunk in stream_response:
                            if 'message' in chunk and 'content' in chunk['message']:
                                content_parts.append(chunk['message']['content'])

                        # 使用join合并字符串，比+运算符更高效
                        full_content = ''.join(content_parts)

                        # 创建最终响应
                        response_data = {
                            "model": request.model,
                            "message": {
                                "role": "assistant",
                                "content": full_content
                            }
                        }

                        # 将响应存入缓存
                        if cache_key not in _response_cache:
                            _response_cache[cache_key] = {'timestamp': time.time()}
                        _response_cache[cache_key]['full_response'] = response_data

                        logger.info(f"Ollama Python客户端响应成功处理")
                        return response_data
                    except Exception as client_error:
                        # 使用警告级别记录日志，避免使用settings.DEBUG
                        logger.warning(f"Ollama Python客户端处理失败: {str(client_error)[:100]}")
                        raise Exception(f"Ollama Python客户端处理失败: {str(client_error)[:100]}")
                else:
                    raise Exception(f"无法连接到Ollama服务: {e}")
    except Exception as e:
        logger.exception(f"调用 Ollama 时出错: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"调用 Ollama 时出错: {str(e)}"},
        )

@router.get("/api/v1/ollama/models")
async def get_ollama_models():
    """获取已安装的 Ollama 模型列表。

    Returns:
        已安装的 Ollama 模型列表。
    """
    print(f"=== 调用get_ollama_models函数，OLLAMA_AVAILABLE={OLLAMA_AVAILABLE} ===")
    # 即使Ollama模块不可用，也尝试使用curl获取模型列表

    try:
        # 从Ollama API获取真实的模型列表
        logger.info("开始获取Ollama模型列表...")

        # 首先尝试使用curl命令直接获取模型列表
        import subprocess
        import json
        import time
        import random

        # 生成一个随机字符串，用于避免缓存
        cache_buster = f"{time.time()}_{random.randint(1000, 9999)}"

        # 强制刷新Ollama模型列表缓存
        try:
            logger.info("尝试强制刷新Ollama模型列表缓存...")
            # 执行一个简单的请求来刷新Ollama的内部缓存
            refresh_result = subprocess.run(['curl', '-s', '-X', 'GET', f'http://localhost:11434/api/show?_={cache_buster}'],
                                    capture_output=True, text=True)
            logger.info("已尝试刷新Ollama模型列表缓存")
        except Exception as e:
            logger.warning(f"刷新Ollama模型列表缓存时出错: {e}")

        # 尝试直接从Ollama服务获取模型列表
        try:
            logger.info("尝试直接从Ollama服务获取模型列表...")
            # 执行一个直接的系统调用来获取模型列表
            result = subprocess.run(['ls', '-la', '/Users/binxie/.ollama/models'],
                                    capture_output=True, text=True)
            logger.info(f"Ollama模型目录内容: {result.stdout}")
        except Exception as e:
            logger.warning(f"获取Ollama模型目录内容失败: {e}")

        # 尝试使用不同的API端点获取模型列表
        models = []

        # 1. 首先尝试使用 /api/tags 端点，添加随机参数避免缓存
        try:
            logger.info("尝试使用curl命令从/api/tags获取Ollama模型列表...")
            # 执行curl命令
            result = subprocess.run(['curl', '-s', f'http://localhost:11434/api/tags?_={cache_buster}'],
                                    capture_output=True, text=True, check=True)

            # 解析JSON响应
            if result.stdout:
                data = json.loads(result.stdout)
                models = data.get("models", [])

                if models:
                    logger.info(f"成功使用curl从/api/tags获取模型列表，模型数量: {len(models)}")
                    # 添加模型详细信息的日志
                    for i, model in enumerate(models):
                        logger.info(f"  模型 {i+1}: {model.get('model', 'unknown')}")
                else:
                    logger.warning("使用curl从/api/tags获取模型列表成功，但模型列表为空")
            else:
                logger.warning("使用curl从/api/tags获取模型列表成功，但响应为空")
        except Exception as e:
            logger.warning(f"使用curl从/api/tags获取模型列表失败: {e}")

        # 2. 如果第一个方法失败，尝试使用 /api/list 端点，添加随机参数避免缓存
        if not models:
            try:
                logger.info("尝试使用curl命令从/api/list获取Ollama模型列表...")
                # 执行curl命令
                result = subprocess.run(['curl', '-s', f'http://localhost:11434/api/list?_={cache_buster}'],
                                        capture_output=True, text=True, check=True)

                # 解析JSON响应
                if result.stdout:
                    data = json.loads(result.stdout)
                    models = data.get("models", [])

                    if models:
                        logger.info(f"成功使用curl从/api/list获取模型列表，模型数量: {len(models)}")
                        # 添加模型详细信息的日志
                        for i, model in enumerate(models):
                            logger.info(f"  模型 {i+1}: {model.get('model', 'unknown')}")
                    else:
                        logger.warning("使用curl从/api/list获取模型列表成功，但模型列表为空")
                else:
                    logger.warning("使用curl从/api/list获取模型列表成功，但响应为空")
            except Exception as e:
                logger.warning(f"使用curl从/api/list获取模型列表失败: {e}")

        # 3. 尝试使用系统命令直接获取模型列表
        if not models:
            try:
                logger.info("尝试使用ollama命令行工具获取模型列表...")
                # 执行ollama命令
                result = subprocess.run(['ollama', 'list'],
                                        capture_output=True, text=True)

                if result.stdout:
                    logger.info(f"ollama list命令输出: {result.stdout}")
                    # 解析输出，提取模型名称
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # 跳过标题行
                        for line in lines[1:]:
                            parts = line.split()
                            if parts:
                                model_name = parts[0]
                                models.append({"model": model_name, "name": model_name})

                        logger.info(f"成功使用ollama命令行工具获取模型列表，模型数量: {len(models)}")
                        for i, model in enumerate(models):
                            logger.info(f"  模型 {i+1}: {model.get('model', 'unknown')}")
                    else:
                        logger.warning("使用ollama命令行工具获取模型列表成功，但模型列表为空")
                else:
                    logger.warning("使用ollama命令行工具获取模型列表成功，但输出为空")
            except Exception as e:
                logger.warning(f"使用ollama命令行工具获取模型列表失败: {e}")

        # 4. 如果前三个方法都失败，尝试使用Ollama Python客户端
        if not models and OLLAMA_AVAILABLE:
            try:
                logger.info("尝试使用Ollama Python客户端获取模型列表...")
                # 创建一个新的客户端实例，设置更长的超时时间
                client = ollama.Client(host='http://localhost:11434', timeout=30)
                models_response = client.list()
                logger.info(f"从Ollama API获取的原始响应: {models_response}")
                models = models_response.get("models", [])

                if models:
                    logger.info(f"成功使用Ollama Python客户端获取模型列表，模型数量: {len(models)}")
                    # 添加模型详细信息的日志
                    for i, model in enumerate(models):
                        logger.info(f"  模型 {i+1}: {model.get('model', 'unknown')}")
                else:
                    logger.warning("使用Ollama Python客户端获取模型列表成功，但模型列表为空")
            except Exception as e:
                logger.warning(f"使用Ollama Python客户端获取模型列表失败: {e}")

        # 如果成功获取到模型列表，返回结果
        if models:
            return {"models": models}

        # 所有方法均失败，抛出异常
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="无法从Ollama服务获取模型列表，请确保Ollama服务正在运行且可访问"
        )
    except Exception as e:
        logger.exception(f"获取 Ollama 模型列表时出错: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"获取 Ollama 模型列表时出错: {str(e)}"},
        )

@router.get("/api/v1/ollama/library")
async def get_ollama_library():
    """获取 Ollama 模型库中的可用模型列表。

    Returns:
        Ollama 模型库中的可用模型列表。
    """
    try:
        # 定义常用模型列表
        common_models = [
            {"name": "llama3", "description": "Meta的Llama 3模型", "tags": ["text", "chat", "general"]},
            {"name": "llama3:8b", "description": "Meta的Llama 3 8B参数模型", "tags": ["text", "chat", "general"]},
            {"name": "llama3:70b", "description": "Meta的Llama 3 70B参数模型", "tags": ["text", "chat", "general"]},
            {"name": "gemma", "description": "Google的Gemma模型", "tags": ["text", "chat", "general"]},
            {"name": "gemma:2b", "description": "Google的Gemma 2B参数模型", "tags": ["text", "chat", "general"]},
            {"name": "gemma:7b", "description": "Google的Gemma 7B参数模型", "tags": ["text", "chat", "general"]},
            {"name": "mistral", "description": "Mistral AI的开源模型", "tags": ["text", "chat", "general"]},
            {"name": "mixtral", "description": "Mistral AI的混合专家模型", "tags": ["text", "chat", "general"]},
            {"name": "phi3", "description": "Microsoft的Phi-3模型", "tags": ["text", "chat", "general"]},
            {"name": "phi3:mini", "description": "Microsoft的Phi-3 Mini模型", "tags": ["text", "chat", "general"]},
            {"name": "qwen", "description": "阿里巴巴的通义千问模型", "tags": ["text", "chat", "general"]},
            {"name": "qwen:14b", "description": "阿里巴巴的通义千问14B参数模型", "tags": ["text", "chat", "general"]},
            {"name": "qwen:72b", "description": "阿里巴巴的通义千问72B参数模型", "tags": ["text", "chat", "general"]},
            {"name": "codellama", "description": "Meta的代码生成专用模型", "tags": ["code", "programming"]},
            {"name": "codellama:7b", "description": "Meta的代码生成专用7B参数模型", "tags": ["code", "programming"]},
            {"name": "codellama:13b", "description": "Meta的代码生成专用13B参数模型", "tags": ["code", "programming"]},
            {"name": "codellama:34b", "description": "Meta的代码生成专用34B参数模型", "tags": ["code", "programming"]},
            {"name": "deepseek-coder", "description": "DeepSeek的代码生成专用模型", "tags": ["code", "programming"]},
            {"name": "wizardcoder", "description": "代码生成专用模型", "tags": ["code", "programming"]},
            {"name": "llava", "description": "多模态视觉语言模型", "tags": ["vision", "multimodal"]},
            {"name": "bakllava", "description": "基于Llama 2的多模态视觉语言模型", "tags": ["vision", "multimodal"]},
            {"name": "moondream", "description": "轻量级视觉语言模型", "tags": ["vision", "multimodal"]},
            {"name": "tinyllama", "description": "轻量级Llama模型", "tags": ["text", "chat", "small"]},
            {"name": "orca-mini", "description": "轻量级Orca模型", "tags": ["text", "chat", "small"]},
            {"name": "stablelm", "description": "Stability AI的语言模型", "tags": ["text", "chat", "general"]},
            {"name": "neural-chat", "description": "Intel的神经聊天模型", "tags": ["text", "chat", "general"]},
            {"name": "starling-lm", "description": "Berkeley的对齐语言模型", "tags": ["text", "chat", "general"]},
            {"name": "qwq", "description": "自定义测试模型", "tags": ["text", "chat", "small"]},
            {"name": "deepseek-r1:14b", "description": "DeepSeek的R1 14B参数模型", "tags": ["text", "chat", "general"]},
        ]

        # 尝试获取最新的Ollama模型
        try:
            # 尝试从Ollama官方获取最新模型
            latest_models = await get_latest_ollama_models()
            if latest_models and len(latest_models) > 0:
                # 将最新模型添加到常用模型列表中
                for model in latest_models:
                    # 检查模型是否已经在列表中
                    if not any(m["name"] == model["name"] for m in common_models):
                        common_models.append(model)
                logger.info(f"成功添加 {len(latest_models)} 个最新Ollama模型到模型库")
        except Exception as e:
            logger.warning(f"获取最新Ollama模型时出错: {e}")

        # 尝试从已安装模型中获取当前已安装的模型名称
        installed_models = []
        try:
            # 尝试使用curl命令获取已安装的模型列表
            import subprocess
            import json

            logger.info(f"尝试使用curl命令获取已安装的模型列表...")
            result = subprocess.run(
                ['curl', '-s', f'http://localhost:11434/api/tags'],
                capture_output=True, text=True, check=True
            )

            if result.stdout:
                try:
                    response_data = json.loads(result.stdout)
                    if "models" in response_data:
                        installed_models = [model["name"] for model in response_data["models"]]
                        logger.info(f"成功使用curl获取已安装的模型列表，模型数量: {len(installed_models)}")
                except json.JSONDecodeError:
                    logger.warning(f"使用curl获取已安装的模型列表时，响应不是JSON格式: {result.stdout}")

            # 如果curl命令失败或没有返回模型列表，尝试使用Python客户端
            if not installed_models and OLLAMA_AVAILABLE:
                logger.info(f"尝试使用Ollama Python客户端获取已安装的模型列表...")
                client = ollama.Client(host='http://localhost:11434', timeout=30)
                models_list = client.list()
                installed_models = [model["model"] for model in models_list.get("models", [])]
                logger.info(f"成功使用Ollama Python客户端获取已安装的模型列表，模型数量: {len(installed_models)}")

        except Exception as e:
            logger.warning(f"获取已安装模型列表时出错: {e}")
            # 如果无法获取已安装的模型列表，尝试使用get_ollama_models函数的结果
            try:
                models_response = await get_ollama_models()
                if isinstance(models_response, dict) and "models" in models_response:
                    installed_models = [model["model"] for model in models_response["models"]]
                    logger.info(f"使用get_ollama_models函数获取已安装的模型列表，模型数量: {len(installed_models)}")
            except Exception as e2:
                logger.warning(f"使用get_ollama_models函数获取已安装的模型列表时出错: {e2}")

        # 为每个模型添加是否已安装的标志
        for model in common_models:
            model["installed"] = model["name"] in installed_models

        return {"models": common_models}
    except Exception as e:
        logger.exception(f"获取 Ollama 模型库时出错: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"获取 Ollama 模型库时出错: {str(e)}"},
        )

@router.get("/api/v1/ollama/pull/progress/{model_name}")
async def get_model_pull_progress(model_name: str):
    """获取模型拉取进度。

    Args:
        model_name: 模型名称。

    Returns:
        模型拉取进度信息。
    """
    global _model_download_progress

    if model_name not in _model_download_progress:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"没有找到模型 {model_name} 的下载进度信息"},
        )

    # 如果状态是下载中，计算当前下载速度和预计剩余时间
    progress_info = _model_download_progress[model_name]
    if progress_info["status"] == "downloading":
        current_time = time.time()
        elapsed_time = current_time - progress_info["start_time"]

        # 更新下载速度（字节/秒）
        if elapsed_time > 0 and progress_info["downloaded_size"] > 0:
            progress_info["speed"] = progress_info["downloaded_size"] / elapsed_time

        # 更新预计剩余时间（秒）
        if progress_info["speed"] > 0 and progress_info["total_size"] > 0:
            remaining_bytes = progress_info["total_size"] - progress_info["downloaded_size"]
            progress_info["eta"] = remaining_bytes / progress_info["speed"]

    return progress_info

@router.post("/api/v1/ollama/pull")
async def pull_ollama_model(request: dict = Body(...)):
    """拉取 Ollama 模型。

    Args:
        request: 包含模型名称的请求。

    Returns:
        拉取结果。
    """
    global _model_download_progress

    model_name = request.get("model")
    if not model_name:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "缺少模型名称"},
        )

    # 初始化进度信息
    _model_download_progress[model_name] = {
        "status": "downloading",
        "progress": 0.0,
        "downloaded_size": 0,
        "total_size": 0,
        "speed": 0,
        "eta": 0,
        "start_time": time.time(),
        "update_time": time.time()
    }

    # 启动一个后台任务来拉取模型
    asyncio.create_task(pull_model_background(model_name))

    # 立即返回，让前端可以开始轮询进度
    return {"status": "started", "message": f"模型 {model_name} 开始拉取，请通过进度API查询下载进度"}

async def pull_model_background(model_name: str):
    """在后台拉取模型。

    Args:
        model_name: 模型名称。
    """
    global _model_download_progress

    try:
        # 尝试使用curl命令拉取模型
        import subprocess
        import json
        import re
        from asyncio import create_subprocess_exec
        from asyncio.subprocess import PIPE

        try:
            logger.info(f"尝试使用curl命令拉取Ollama模型: {model_name}...")

            # 创建一个子进程来执行curl命令，并实时获取输出
            process = await create_subprocess_exec(
                'curl', '-s', '-N', '-X', 'POST', 'http://localhost:11434/api/pull',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps({"name": model_name}),
                stdout=PIPE, stderr=PIPE
            )

            # 读取输出并解析进度信息
            async for line in process.stdout:
                line_str = line.decode('utf-8').strip()
                if line_str:
                    try:
                        data = json.loads(line_str)

                        # 更新进度信息
                        if "status" in data:
                            if data["status"] == "pulling manifest" or data["status"] == "pulling":
                                _model_download_progress[model_name]["status"] = "downloading"

                        if "completed" in data and "total" in data:
                            downloaded = data["completed"]
                            total = data["total"]

                            _model_download_progress[model_name]["downloaded_size"] = downloaded
                            _model_download_progress[model_name]["total_size"] = total

                            if total > 0:
                                _model_download_progress[model_name]["progress"] = downloaded / total

                            _model_download_progress[model_name]["update_time"] = time.time()

                        # 检查是否完成
                        if "status" in data and data["status"] == "success":
                            _model_download_progress[model_name]["status"] = "completed"
                            _model_download_progress[model_name]["progress"] = 1.0
                            _model_download_progress[model_name]["update_time"] = time.time()
                            logger.info(f"成功使用curl拉取模型 {model_name}")
                            break

                    except json.JSONDecodeError:
                        logger.warning(f"解析拉取模型响应行失败: {line_str[:100]}")

            # 等待进程结束
            await process.wait()

            # 如果进程正常结束但没有标记为完成，也标记为完成
            if process.returncode == 0 and _model_download_progress[model_name]["status"] != "completed":
                _model_download_progress[model_name]["status"] = "completed"
                _model_download_progress[model_name]["progress"] = 1.0
                _model_download_progress[model_name]["update_time"] = time.time()
                logger.info(f"成功使用curl拉取模型 {model_name}")

            # 如果进程异常结束，标记为失败
            elif process.returncode != 0:
                stderr = await process.stderr.read()
                stderr_str = stderr.decode('utf-8')
                _model_download_progress[model_name]["status"] = "failed"
                _model_download_progress[model_name]["error"] = f"拉取模型失败: {stderr_str}"
                logger.warning(f"使用curl拉取模型失败: {stderr_str}")

                # 如果curl命令失败，尝试使用Python客户端
                if OLLAMA_AVAILABLE:
                    try:
                        logger.info(f"尝试使用Ollama Python客户端拉取模型: {model_name}...")
                        # 重置进度信息
                        _model_download_progress[model_name] = {
                            "status": "downloading",
                            "progress": 0.0,
                            "downloaded_size": 0,
                            "total_size": 0,
                            "speed": 0,
                            "eta": 0,
                            "start_time": time.time(),
                            "update_time": time.time()
                        }

                        # 创建一个新的客户端实例，设置更长的超时时间
                        client = ollama.Client(host='http://localhost:11434', timeout=300)

                        # 使用Python客户端拉取模型
                        for progress in await asyncio.to_thread(client.pull, model_name, stream=True):
                            if "status" in progress:
                                if progress["status"] == "pulling manifest" or progress["status"] == "pulling":
                                    _model_download_progress[model_name]["status"] = "downloading"

                            if "completed" in progress and "total" in progress:
                                downloaded = progress["completed"]
                                total = progress["total"]

                                _model_download_progress[model_name]["downloaded_size"] = downloaded
                                _model_download_progress[model_name]["total_size"] = total

                                if total > 0:
                                    _model_download_progress[model_name]["progress"] = downloaded / total

                                _model_download_progress[model_name]["update_time"] = time.time()

                            # 检查是否完成
                            if "status" in progress and progress["status"] == "success":
                                _model_download_progress[model_name]["status"] = "completed"
                                _model_download_progress[model_name]["progress"] = 1.0
                                _model_download_progress[model_name]["update_time"] = time.time()
                                logger.info(f"成功使用Ollama Python客户端拉取模型 {model_name}")
                                break

                        # 如果没有标记为完成，也标记为完成
                        if _model_download_progress[model_name]["status"] != "completed":
                            _model_download_progress[model_name]["status"] = "completed"
                            _model_download_progress[model_name]["progress"] = 1.0
                            _model_download_progress[model_name]["update_time"] = time.time()
                            logger.info(f"成功使用Ollama Python客户端拉取模型 {model_name}")

                    except Exception as e:
                        logger.exception(f"使用Ollama Python客户端拉取模型失败: {e}")
                        _model_download_progress[model_name]["status"] = "failed"
                        _model_download_progress[model_name]["error"] = f"使用Ollama Python客户端拉取模型失败: {str(e)}"
                else:
                    _model_download_progress[model_name]["status"] = "failed"
                    _model_download_progress[model_name]["error"] = f"拉取模型失败，curl错误: {stderr_str}"

        except Exception as e:
            logger.exception(f"拉取模型时出错: {e}")
            _model_download_progress[model_name]["status"] = "failed"
            _model_download_progress[model_name]["error"] = f"拉取模型时出错: {str(e)}"

            # 如果出现其他错误，尝试使用Python客户端
            if OLLAMA_AVAILABLE:
                try:
                    logger.info(f"尝试使用Ollama Python客户端拉取模型: {model_name}...")
                    # 重置进度信息
                    _model_download_progress[model_name] = {
                        "status": "downloading",
                        "progress": 0.0,
                        "downloaded_size": 0,
                        "total_size": 0,
                        "speed": 0,
                        "eta": 0,
                        "start_time": time.time(),
                        "update_time": time.time()
                    }

                    # 创建一个新的客户端实例，设置更长的超时时间
                    client = ollama.Client(host='http://localhost:11434', timeout=300)

                    # 使用Python客户端拉取模型
                    for progress in await asyncio.to_thread(client.pull, model_name, stream=True):
                        if "status" in progress:
                            if progress["status"] == "pulling manifest" or progress["status"] == "pulling":
                                _model_download_progress[model_name]["status"] = "downloading"

                        if "completed" in progress and "total" in progress:
                            downloaded = progress["completed"]
                            total = progress["total"]

                            _model_download_progress[model_name]["downloaded_size"] = downloaded
                            _model_download_progress[model_name]["total_size"] = total

                            if total > 0:
                                _model_download_progress[model_name]["progress"] = downloaded / total

                            _model_download_progress[model_name]["update_time"] = time.time()

                        # 检查是否完成
                        if "status" in progress and progress["status"] == "success":
                            _model_download_progress[model_name]["status"] = "completed"
                            _model_download_progress[model_name]["progress"] = 1.0
                            _model_download_progress[model_name]["update_time"] = time.time()
                            logger.info(f"成功使用Ollama Python客户端拉取模型 {model_name}")
                            break

                    # 如果没有标记为完成，也标记为完成
                    if _model_download_progress[model_name]["status"] != "completed":
                        _model_download_progress[model_name]["status"] = "completed"
                        _model_download_progress[model_name]["progress"] = 1.0
                        _model_download_progress[model_name]["update_time"] = time.time()
                        logger.info(f"成功使用Ollama Python客户端拉取模型 {model_name}")

                except Exception as e:
                    logger.exception(f"使用Ollama Python客户端拉取模型失败: {e}")
                    _model_download_progress[model_name]["status"] = "failed"
                    _model_download_progress[model_name]["error"] = f"使用Ollama Python客户端拉取模型失败: {str(e)}"

    except Exception as e:
        logger.exception(f"拉取 Ollama 模型时出错: {e}")
        _model_download_progress[model_name]["status"] = "failed"
        _model_download_progress[model_name]["error"] = f"拉取 Ollama 模型时出错: {str(e)}"

@router.delete("/api/v1/ollama/delete/{model_name}")
async def delete_ollama_model(model_name: str):
    """删除 Ollama 模型。

    Args:
        model_name: 模型名称。

    Returns:
        删除结果。
    """
    try:
        # 尝试使用curl命令删除模型
        import subprocess
        import json

        try:
            logger.info(f"尝试使用curl命令删除Ollama模型: {model_name}...")
            # 执行curl命令
            result = subprocess.run(
                ['curl', '-s', '-X', 'DELETE', f'http://localhost:11434/api/delete',
                 '-H', 'Content-Type: application/json',
                 '-d', json.dumps({"name": model_name})],
                capture_output=True, text=True, check=True
            )

            # 检查响应
            if result.stdout:
                try:
                    response_data = json.loads(result.stdout)
                    logger.info(f"成功使用curl删除模型 {model_name}，响应: {response_data}")
                    return {"status": "success", "message": f"模型 {model_name} 已成功删除"}
                except json.JSONDecodeError:
                    # 如果响应不是JSON格式，但命令成功执行
                    logger.info(f"成功使用curl删除模型 {model_name}，但响应不是JSON格式: {result.stdout}")
                    return {"status": "success", "message": f"模型 {model_name} 已成功删除"}
            else:
                # 如果没有输出但命令成功执行
                logger.info(f"成功使用curl删除模型 {model_name}，但没有响应")
                return {"status": "success", "message": f"模型 {model_name} 已成功删除"}

        except subprocess.CalledProcessError as e:
            logger.warning(f"使用curl删除模型失败: {e}, stderr: {e.stderr}")
            # 如果curl命令失败，尝试使用Python客户端
            if OLLAMA_AVAILABLE:
                logger.info(f"尝试使用Ollama Python客户端删除模型: {model_name}...")
                # 创建一个新的客户端实例，设置更长的超时时间
                client = ollama.Client(host='http://localhost:11434', timeout=60)
                await asyncio.to_thread(client.delete, model_name)
                logger.info(f"成功使用Ollama Python客户端删除模型 {model_name}")
                return {"status": "success", "message": f"模型 {model_name} 已成功删除"}
            else:
                raise Exception(f"删除模型失败，curl错误: {e.stderr}")

        except Exception as e:
            logger.warning(f"使用curl删除模型时发生未知错误: {e}")
            # 如果curl命令出现其他错误，尝试使用Python客户端
            if OLLAMA_AVAILABLE:
                logger.info(f"尝试使用Ollama Python客户端删除模型: {model_name}...")
                # 创建一个新的客户端实例，设置更长的超时时间
                client = ollama.Client(host='http://localhost:11434', timeout=60)
                await asyncio.to_thread(client.delete, model_name)
                logger.info(f"成功使用Ollama Python客户端删除模型 {model_name}")
                return {"status": "success", "message": f"模型 {model_name} 已成功删除"}
            else:
                raise Exception(f"删除模型失败，未知错误: {e}")

    except Exception as e:
        logger.exception(f"删除 Ollama 模型时出错: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"删除 Ollama 模型时出错: {str(e)}"},
        )

@router.get("/api/v1/admin/console")
async def admin_console():
    """
    提供管理控制台的系统状态信息。

    Returns:
        系统状态的详细信息。
    """
    try:
        # 获取队列状态
        queue_status = queue_manager.queue.get_queue_sizes()

        # 获取活动请求数
        active_requests = queue_status.get("active_requests", 0)

        # 获取规则统计信息
        rules_count = {
            "prompt_injection": len(json.load(open(settings.security.prompt_injection_rules_path))),
            "harmful_content": len(json.load(open(settings.security.harmful_content_rules_path))),
            "compliance": len(json.load(open(settings.security.compliance_rules_path))),
        }

        # 返回系统状态
        return {
            "queue_status": queue_status,
            "active_requests": active_requests,
            "rules_count": rules_count,
            "status": "ok",
        }
    except Exception as e:
        logger.error(f"获取管理控制台信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取管理控制台信息失败: {str(e)}"
        )

@router.api_route("/api/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def catch_all(request: Request, path: str):
    """Catch-all route for proxying requests to LLM APIs.

    Args:
        request: The incoming request.
        path: The request path.

    Returns:
        The response from the LLM API.
    """
    # Process the request
    return await interceptor.intercept(request)
