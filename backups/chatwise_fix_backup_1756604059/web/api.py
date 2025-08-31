"""API router for the web interface."""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
from json import JSONEncoder

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Body
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Literal

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
from src.security.api_auth import api_key_manager, get_api_key, check_client_license


router = APIRouter()
queue_manager = None
interceptor = None
security_detector = None

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "ollama_available": OLLAMA_AVAILABLE,
        "version": "1.0.2"
    }


@router.get("/api/v1/license/clients")
async def get_license_clients(api_key: str = Depends(get_api_key)):
    """获取当前活跃客户端信息。"""
    from src.security.license_manager import client_tracker
    
    clients = client_tracker.get_clients_by_api_key(api_key)
    license_config = api_key_manager.get_license_config(api_key)
    
    return {
        "api_key": api_key[:8] + "...",
        "max_clients": license_config["max_clients"],
        "current_clients": len(clients),
        "clients": [
            {
                "client_id": client.client_id,
                "ip_address": client.ip_address,
                "user_agent": client.user_agent[:50] + "..." if len(client.user_agent) > 50 else client.user_agent,
                "connected_at": client.connected_at,
                "last_activity": client.last_activity,
                "session_id": client.session_id
            }
            for client in clients
        ],
        "timestamp": time.time()
    }


@router.get("/api/v1/license/stats")
async def get_license_stats(api_key: str = Depends(get_api_key)):
    """获取许可证统计信息。"""
    from src.security.license_manager import client_tracker
    
    stats = client_tracker.get_stats()
    license_config = api_key_manager.get_license_config(api_key)
    
    return {
        "license": license_config,
        "usage": {
            "current_clients": client_tracker.get_active_count(api_key),
            "max_clients": license_config["max_clients"],
            "utilization": f"{client_tracker.get_active_count(api_key) / license_config['max_clients'] * 100:.1f}%"
        },
        "global_stats": stats,
        "timestamp": time.time()
    }


# API密钥管理端点
@router.get("/api/v1/auth/api-keys")
async def get_api_keys(api_key: str = Depends(get_api_key)):
    """获取所有API密钥列表（需要管理员权限）。"""
    # 检查是否为管理员权限
    if not api_key_manager.check_permission(api_key, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限才能访问API密钥列表"
        )
    
    # 获取所有API密钥信息（隐藏完整密钥，只显示部分）
    api_keys_info = []
    for key, config in api_key_manager.api_keys.items():
        api_keys_info.append({
            "key": key[:8] + "..." if len(key) > 8 else key,
            "full_key": key,  # 注意：实际使用时应该更安全地处理
            "name": config.get("name", "未命名"),
            "description": config.get("description", ""),
            "permissions": config.get("permissions", []),
            "rate_limit": config.get("rate_limit", 0),
            "models": config.get("models", []),
            "created_at": config.get("created_at", 0),
            "license": config.get("license", {
                "max_clients": 10,
                "license_type": "standard",
                "client_timeout": 300
            })
        })
    
    return {
        "api_keys": api_keys_info,
        "total_count": len(api_keys_info),
        "timestamp": time.time()
    }


@router.post("/api/v1/auth/api-keys")
async def create_api_key(
    request: Request,
    name: str = Body(..., description="API密钥名称"),
    permissions: List[str] = Body(..., description="权限列表"),
    rate_limit: int = Body(60, description="速率限制（每分钟请求数）"),
    models: List[str] = Body(["*"], description="允许访问的模型列表"),
    max_clients: int = Body(10, description="最大客户端连接数"),
    license_type: str = Body("standard", description="许可证类型"),
    description: str = Body("", description="密钥描述")
):
    """创建新的API密钥（需要管理员权限）。"""
    # 从请求中提取API密钥进行权限验证
    from src.security.api_auth import extract_api_key_from_request
    api_key = extract_api_key_from_request(request)
    
    if not api_key or not api_key_manager.check_permission(api_key, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限才能创建API密钥"
        )
    
    # 创建新的API密钥
    try:
        new_api_key = api_key_manager.create_api_key(
            name=name,
            permissions=permissions,
            rate_limit=rate_limit,
            models=models,
            max_clients=max_clients,
            license_type=license_type
        )
        
        # 添加描述信息
        if description:
            api_key_info = api_key_manager.get_api_key_info(new_api_key)
            if api_key_info:
                api_key_info["description"] = description
                api_key_manager.save_api_keys()
        
        return {
            "success": True,
            "api_key": new_api_key,
            "message": "API密钥创建成功",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"创建API密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建API密钥失败: {str(e)}"
        )


@router.delete("/api/v1/auth/api-keys/{target_api_key}")
async def delete_api_key(request: Request, target_api_key: str):
    """删除API密钥（需要管理员权限）。"""
    # 从请求中提取API密钥进行权限验证
    from src.security.api_auth import extract_api_key_from_request
    api_key = extract_api_key_from_request(request)
    
    if not api_key or not api_key_manager.check_permission(api_key, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限才能删除API密钥"
        )
    
    # 防止删除自己的API密钥
    if target_api_key == api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前正在使用的API密钥"
        )
    
    # 删除API密钥
    success = api_key_manager.delete_api_key(target_api_key)
    
    if success:
        return {
            "success": True,
            "message": "API密钥删除成功",
            "timestamp": time.time()
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API密钥不存在"
        )


@router.get("/api/v1/auth/stats")
async def get_auth_stats(api_key: str = Depends(get_api_key)):
    """获取认证统计信息。"""
    from src.security.license_manager import client_tracker
    
    # 获取当前API密钥的统计信息
    current_clients = client_tracker.get_active_count(api_key)
    license_config = api_key_manager.get_license_config(api_key)
    
    # 获取全局统计（需要管理员权限）
    global_stats = {}
    if api_key_manager.check_permission(api_key, "admin"):
        global_stats = {
            "total_api_keys": len(api_key_manager.api_keys),
            "active_clients": client_tracker.get_stats()["total_clients"],
            "total_requests_today": 0,  # 需要实现日请求统计
            "blocked_requests_today": 0  # 需要实现日阻止统计
        }
    
    return {
        "current": {
            "api_key": api_key[:8] + "...",
            "current_clients": current_clients,
            "max_clients": license_config["max_clients"],
            "utilization": f"{current_clients / license_config['max_clients'] * 100:.1f}%"
        },
        "global": global_stats,
        "timestamp": time.time()
    }


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
                        # 解析Ollama JSON响应
                        ollama_chunk = json.loads(line)
                        
                        # 将Ollama格式转换为OpenAI格式
                        openai_chunk = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": None
                                }
                            ]
                        }
                        
                        # 提取内容
                        if "message" in ollama_chunk and "content" in ollama_chunk["message"]:
                            content = ollama_chunk["message"]["content"]
                            openai_chunk["choices"][0]["delta"]["content"] = content
                            
                        # 检查是否完成
                        if ollama_chunk.get("done", False):
                            openai_chunk["choices"][0]["finish_reason"] = "stop"
                            openai_chunk["choices"][0]["delta"] = {}
                        
                        # 格式化为SSE格式
                        formatted_line = f"data: {json.dumps(openai_chunk)}\n\n"
                        buffer.append(formatted_line)
                        count += 1

                        # 当缓冲区达到批处理大小或者是最后一个响应时，发送批量数据
                        if count >= _BATCH_SIZE or ollama_chunk.get("done", False):
                            # 将批量数据添加到缓存
                            _response_cache[cache_key]['chunks'].extend(buffer)

                            # 发送批量数据
                            for chunk in buffer:
                                yield chunk

                            # 重置缓冲区和计数器
                            buffer = []
                            count = 0
                            
                            # 如果完成，发送结束信号
                            if ollama_chunk.get("done", False):
                                done_signal = "data: [DONE]\n\n"
                                _response_cache[cache_key]['chunks'].append(done_signal)
                                yield done_signal
                                return
                                
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
                            # 将Ollama格式转换为OpenAI格式
                            openai_chunk = {
                                "id": f"chatcmpl-{int(time.time())}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": None
                                    }
                                ]
                            }
                            
                            # 提取内容
                            if hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                                content = chunk.message.content
                                openai_chunk["choices"][0]["delta"]["content"] = content
                            elif isinstance(chunk, dict):
                                if "message" in chunk and "content" in chunk["message"]:
                                    content = chunk["message"]["content"]
                                    openai_chunk["choices"][0]["delta"]["content"] = content
                                    
                            # 检查是否完成
                            chunk_done = False
                            if hasattr(chunk, 'done'):
                                chunk_done = chunk.done
                            elif isinstance(chunk, dict):
                                chunk_done = chunk.get('done', False)
                                
                            if chunk_done:
                                openai_chunk["choices"][0]["finish_reason"] = "stop"
                                openai_chunk["choices"][0]["delta"] = {}
                            
                            # 格式化为SSE格式
                            formatted_chunk = f"data: {json.dumps(openai_chunk)}\n\n"
                            buffer.append(formatted_chunk)
                            count += 1

                            # 当缓冲区达到批处理大小或者是最后一个响应时，发送批量数据
                            if count >= _BATCH_SIZE or chunk_done:
                                # 将批量数据添加到缓存
                                _response_cache[cache_key]['chunks'].extend(buffer)

                                # 发送批量数据
                                for chunk_data in buffer:
                                    yield chunk_data

                                # 重置缓冲区和计数器
                                buffer = []
                                count = 0
                                
                                # 如果完成，发送结束信号并退出
                                if chunk_done:
                                    done_signal = "data: [DONE]\n\n"
                                    _response_cache[cache_key]['chunks'].append(done_signal)
                                    yield done_signal
                                    return
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
    import psutil
    
    queue_sizes = queue_manager.queue.get_queue_sizes()
    
    # 获取实时系统资源数据
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    return {
        "queue_sizes": queue_sizes,
        "active_requests": queue_sizes["active_requests"],
        "total_requests": 0,  # 占位符，可以从统计数据获取
        "blocked_requests": 0,  # 占位符
        "security_events": 0,  # 占位符
        "active_models": 0,  # 占位符
        # 添加前端需要的字段
        "cpu_usage": round(cpu_usage, 2),
        "memory_usage": round(memory.percent, 2),
        "avg_response_time": 250.0,  # 模拟平均响应时间
    }


@router.get("/api/v1/metrics/resource")
async def get_resource_metrics(minutes: int = 60):
    """Get resource usage metrics.
    
    Args:
        minutes: Time range in minutes
        
    Returns:
        Resource usage data
    """
    import psutil
    import time
    import random
    
    # 生成模拟的时间序列数据
    current_time = int(time.time())
    data_points = min(minutes, 60)  # 最多60个数据点
    interval = (minutes * 60) // data_points
    
    result = []
    for i in range(data_points):
        timestamp = current_time - (data_points - i - 1) * interval
        
        # 获取实时系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=0.01)
        memory = psutil.virtual_memory()
        
        # 添加一些随机波动使数据更真实
        cpu_variation = random.uniform(-5, 5)
        memory_variation = random.uniform(-2, 2)
        
        # 添加时间格式转换，确保返回正确的timestamp格式
        current_timestamp = int(time.time())
        iso_timestamp = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(current_timestamp - (data_points - i - 1) * interval))
        
        result.append({
            "timestamp": iso_timestamp,  # 使用ISO格式确保兼容性
            "cpu_usage": round(max(0, min(100, cpu_percent + cpu_variation)), 2),
            "memory_usage": round(max(0, min(100, memory.percent + memory_variation)), 2),
            "disk_usage": round(psutil.disk_usage('/').percent, 2)
        })
    
    return JSONResponse(content=result)


@router.get("/api/v1/metrics/requests")
async def get_request_metrics(minutes: int = 60):
    """Get request statistics.
    
    Args:
        minutes: Time range in minutes
        
    Returns:
        Request statistics data
    """
    import time
    import random
    
    # 生成模拟的请求统计数据
    current_time = int(time.time())
    data_points = min(minutes, 60)
    interval = (minutes * 60) // data_points
    
    result = []
    for i in range(data_points):
        timestamp = current_time - (data_points - i - 1) * interval
        
        # 模拟请求数据，可以基于实际统计
        base_requests = random.randint(5, 20)
        base_blocked = random.randint(0, 3)
        
        # 使用ISO格式的timestamp
        iso_timestamp = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(timestamp))
        
        result.append({
            "timestamp": iso_timestamp,
            "total_requests": base_requests,
            "success_requests": base_requests - base_blocked,  # 修正字段名
            "blocked_requests": base_blocked,
            "avg_response_time": round(random.uniform(200, 800), 1)
        })
    
    return JSONResponse(content=result)


@router.get("/api/v1/metrics/events")
async def get_event_metrics(days: int = 7):
    """Get security event statistics.
    
    Args:
        days: Time range in days
        
    Returns:
        Security event statistics
    """
    try:
        # 尝试从安全事件日志获取真实数据
        from src.audit.event_logger import event_logger
        
        events_data = []
        for day in range(days):
            # 这里可以根据实际的事件日志来统计
            events_data.append({
                "date": f"Day {day + 1}",
                "prompt_injection": 0,
                "jailbreak": 0, 
                "harmful_content": 0,
                "sensitive_info": 0,
                "compliance_violation": 0  # 添加缺失的字段
            })
        
        return events_data
    except Exception as e:
        # 如果获取失败，返回空数据
        return []


@router.get("/api/v1/metrics/models")
async def get_model_metrics():
    """Get model usage statistics.
    
    Returns:
        Model usage statistics
    """
    # 模拟模型使用统计，可以从实际的模型调用记录获取
    models = [
        {"model_name": "tinyllama:latest", "request_count": 45, "avg_response_time": 500},
        {"model_name": "llama2:7b", "request_count": 23, "avg_response_time": 800},
        {"model_name": "codellama:7b", "request_count": 12, "avg_response_time": 600},
    ]
    
    return models


@router.get("/api/v1/metrics/queues")
async def get_queue_metrics():
    """Get queue status.
    
    Returns:
        Queue status data
    """
    try:
        queue_sizes = queue_manager.queue.get_queue_sizes()
        
        queues = [
            {
                "name": "High Priority",
                "size": queue_sizes.get("high_priority", 0),
                "max_size": 100,
                "processing_time": "1.2s"
            },
            {
                "name": "Normal Priority", 
                "size": queue_sizes.get("normal_priority", 0),
                "max_size": 500,
                "processing_time": "2.5s"
            },
            {
                "name": "Low Priority",
                "size": queue_sizes.get("low_priority", 0), 
                "max_size": 1000,
                "processing_time": "5.0s"
            }
        ]
        
        return queues
    except Exception as e:
        return []


@router.get("/api/v1/topology")
async def get_system_topology():
    """Get system architecture topology data.
    
    Returns:
        System topology with nodes, connections, and real-time metrics
    """
    try:
        import psutil
        import time
        from datetime import datetime
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check Ollama service status
        ollama_status = "online"
        ollama_response_time = 0
        try:
            import requests
            start_time = time.time()
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            ollama_response_time = round((time.time() - start_time) * 1000)  # ms
            if response.status_code != 200:
                ollama_status = "warning"
        except Exception:
            ollama_status = "offline"
            ollama_response_time = -1
        
        # Check security detector status
        security_status = "online" if security_detector else "offline"
        
        # Get request metrics with fallback values
        total_requests = getattr(queue_manager, '_total_requests', 42) if queue_manager else 42
        blocked_requests = getattr(security_detector, '_blocked_count', 3) if security_detector else 3
        
        # If no real data is available, generate some sample data for demonstration
        if total_requests == 0:
            total_requests = 127
            blocked_requests = 8
        
        # Calculate current timestamp
        current_time = datetime.now().isoformat()
        
        # Get queue sizes safely
        queue_sizes = {}
        if queue_manager and hasattr(queue_manager, 'queue') and hasattr(queue_manager.queue, 'get_queue_sizes'):
            try:
                queue_sizes = queue_manager.queue.get_queue_sizes()
            except:
                queue_sizes = {"high": 2, "normal": 5, "low": 1}
        else:
            queue_sizes = {"high": 2, "normal": 5, "low": 1}
        # Get active connections count
        active_connections = len(getattr(queue_manager.queue, 'active_tasks', [])) if queue_manager else 5
        
        topology_data = {
            "timestamp": current_time,
            "nodes": [
                {
                    "id": "client",
                    "name": "客户端",
                    "type": "client",
                    "status": "online",
                    "metrics": {
                        "active_connections": active_connections,
                        "total_requests": total_requests,
                        "avg_response_time": ollama_response_time if ollama_response_time > 0 else 156
                    },
                    "position": {"x": 100, "y": 150}
                },
                {
                    "id": "security", 
                    "name": "安全防护层",
                    "type": "security",
                    "status": security_status,
                    "metrics": {
                        "blocked_requests": blocked_requests,
                        "detection_rate": round((blocked_requests / max(total_requests, 1)) * 100, 2),
                        "rules_active": 5,  # Number of active security rules
                        "cpu_usage": round(cpu_usage, 1),
                        "memory_usage": round(memory.percent, 1)
                    },
                    "position": {"x": 300, "y": 150}
                },
                {
                    "id": "llm_service",
                    "name": "模型服务", 
                    "type": "llm",
                    "status": ollama_status,
                    "metrics": {
                        "model_count": 3,  # Default model count
                        "response_time": ollama_response_time if ollama_response_time > 0 else 156,
                        "queue_size": sum(queue_sizes.values()),
                        "disk_usage": round(disk.percent, 1)
                    },
                    "position": {"x": 500, "y": 150}
                }
            ],
            "connections": [
                {
                    "source": "client",
                    "target": "security", 
                    "type": "http",
                    "status": "active",
                    "metrics": {
                        "throughput": total_requests,
                        "latency": 25,  # ms
                        "error_rate": round((blocked_requests / max(total_requests, 1)) * 100, 2)
                    }
                },
                {
                    "source": "security",
                    "target": "llm_service",
                    "type": "http", 
                    "status": "active" if ollama_status == "online" else "error",
                    "metrics": {
                        "throughput": total_requests - blocked_requests,
                        "latency": ollama_response_time if ollama_response_time > 0 else 156,
                        "error_rate": 0.5 if ollama_status == "online" else 15.0
                    }
                }
            ],
            "flow_stats": {
                "total_requests": total_requests,
                "blocked_requests": blocked_requests,
                "passed_requests": total_requests - blocked_requests,
                "block_rate": round((blocked_requests / max(total_requests, 1)) * 100, 2),
                "avg_processing_time": ollama_response_time if ollama_response_time > 0 else 156
            }
        }
        
        return topology_data
        
    except Exception as e:
        logger.error(f"获取拓扑数据失败: {e}")
        from datetime import datetime
        # Return fallback topology data
        return {
            "timestamp": datetime.now().isoformat(),
            "nodes": [
                {
                    "id": "client",
                    "name": "客户端",
                    "type": "client", 
                    "status": "unknown",
                    "metrics": {"total_requests": 0},
                    "position": {"x": 100, "y": 150}
                },
                {
                    "id": "security",
                    "name": "安全防护层",
                    "type": "security",
                    "status": "unknown", 
                    "metrics": {"blocked_requests": 0},
                    "position": {"x": 300, "y": 150}
                },
                {
                    "id": "llm_service",
                    "name": "模型服务",
                    "type": "llm",
                    "status": "unknown",
                    "metrics": {"response_time": 0},
                    "position": {"x": 500, "y": 150}
                }
            ],
            "connections": [
                {
                    "source": "client",
                    "target": "security",
                    "type": "http",
                    "status": "inactive",
                    "metrics": {"throughput": 0, "latency": 0, "error_rate": 0}
                },
                {
                    "source": "security", 
                    "target": "llm_service",
                    "type": "http",
                    "status": "inactive",
                    "metrics": {"throughput": 0, "latency": 0, "error_rate": 0}
                }
            ],
            "flow_stats": {
                "total_requests": 0,
                "blocked_requests": 0,
                "passed_requests": 0,
                "block_rate": 0,
                "avg_processing_time": 0
            }
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

            # 🔧 修复上下文污染：只检测最后一条用户消息，而不是所有消息
            current_user_input = ""
            for msg in reversed(request.messages):
                if msg.role == "user":
                    current_user_input = msg.content
                    break
            
            logger.info(f"🔧 上下文污染修复：只检测当前用户输入: {current_user_input[:100]}...")
            logger.info(f"🔧 原始消息数量: {len(request.messages)}")

            # 创建请求对象 - 只包含当前用户输入
            intercepted_request = InterceptedRequest(
                method="POST",
                url="/api/v1/ollama/chat",
                headers={},
                body={
                    "model": request.model,
                    "messages": [{"role": "user", "content": current_user_input}] if current_user_input else []
                },
                query_params={},
                timestamp=time.time(),
                client_ip="127.0.0.1",
                provider="ollama"
            )

            # 执行安全检测
            logger.info(f"执行安全检测，当前用户输入长度: {len(current_user_input)}")
            logger.info(f"当前用户输入内容: {current_user_input[:200]}...")  # 记录当前用户输入的前200个字符
            
            # 为每个请求创建独立的安全检测器实例，避免状态污染
            from src.security.detector import SecurityDetector
            security_detector_instance = SecurityDetector()
            
            # 记录开始时间
            start_time = time.time()
            security_result = await security_detector_instance.check_request(intercepted_request)
            
            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000
            
            # 🔥 实时广播客户端输入事件
            from src.web.realtime_monitor_api import broadcast_realtime_event
            await broadcast_realtime_event(
                content=current_user_input,
                client_type="api",  # 或者从请求头中检测客户端类型
                client_id="unknown",  # 可以从API密钥或IP地址获取
                detection_result=security_result,
                response_time_ms=response_time_ms
            )

            if not security_result.is_allowed:
                logger.warning(f"安全检测失败: {security_result.reason}")
                
                # 🔧 改进错误消息显示：明确显示当前检测到的内容
                error_message = f"本地大模型防护系统阻止了请求: {security_result.reason}"
                if current_user_input:
                    error_message += f" (当前输入: {current_user_input[:50]}{'...' if len(current_user_input) > 50 else ''})"
                
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": error_message,
                        "type": "security_violation",
                        "code": 403,
                        "details": {
                            **(security_result.details if hasattr(security_result, 'details') and security_result.details else {}),
                            "current_input": current_user_input,
                            "detection_scope": "current_input_only"
                        }
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

                            # 创建OpenAI兼容的最终响应
                            response_data = {
                                "id": f"chatcmpl-{int(time.time())}",
                                "object": "chat.completion",
                                "created": int(time.time()),
                                "model": request.model,
                                "choices": [{
                                    "index": 0,
                                    "message": {
                                        "role": "assistant",
                                        "content": full_content
                                    },
                                    "finish_reason": "stop"
                                }],
                                "usage": {
                                    "prompt_tokens": len(' '.join([msg.content for msg in request.messages])) // 4,  # 粗略估算
                                    "completion_tokens": len(full_content) // 4,  # 粗略估算
                                    "total_tokens": (len(' '.join([msg.content for msg in request.messages])) + len(full_content)) // 4
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

@router.get("/api/v1/ollama")
async def get_ollama_info():
    """获取Ollama服务器信息。
    
    Returns:
        Ollama服务器状态和版本信息。
    """
    try:
        # 检查Ollama服务是否可用
        import subprocess
        import json
        
        # 使用curl检查Ollama服务状态
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Ollama服务可用
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "ok",
                    "service": "ollama",
                    "version": "1.0.0",
                    "message": "本地大模型防护系统 - Ollama API代理",
                    "endpoints": {
                        "models": "/api/v1/ollama/models",
                        "chat": "/api/v1/ollama/chat",
                        "library": "/api/v1/ollama/library"
                    }
                }
            )
        else:
            # Ollama服务不可用
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "service": "ollama",
                    "message": "Ollama服务不可用",
                    "error": "无法连接到Ollama服务"
                }
            )
    except Exception as e:
        logger.error(f"获取Ollama信息时出错: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error", 
                "service": "ollama",
                "message": "Ollama服务检查失败",
                "error": str(e)
            }
        )

@router.get("/api/v1")
async def get_api_info():
    """获取API版本信息。
    
    Returns:
        API版本和可用服务信息。
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "version": "v1",
            "service": "本地大模型防护系统",
            "description": "Local LLM Protection System API",
            "available_services": ["ollama"],
            "endpoints": {
                "ollama": "/api/v1/ollama"
            }
        }
    )

# Cherry Studio兼容路由
@router.get("/api/v1/ollama/v1/models")
async def get_openai_models_for_cherry(request: Request):
    """为Cherry Studio提供OpenAI兼容的模型列表端点。"""
    # 重定向到标准模型端点
    return await get_ollama_models(request)

@router.post("/api/v1/ollama/v1/chat/completions")
async def openai_chat_completions_for_cherry(request: Request):
    """为Cherry Studio提供OpenAI兼容的聊天完成端点。"""
    try:
        # 获取请求体
        body = await request.json()
        
        # 如果是空请求或者检测请求，返回成功状态
        if not body or not body.get("model") or not body.get("messages"):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "tinyllama:latest",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "本地大模型防护系统连接正常，可以开始对话。"
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30
                    }
                }
            )
        
        # 如果是完整的聊天请求，转换为OllamaRequest格式
        try:
            ollama_request = OllamaRequest(
                model=body.get("model", "tinyllama:latest"),
                messages=body.get("messages", []),
                stream=body.get("stream", False),
                temperature=body.get("temperature"),
                max_tokens=body.get("max_tokens")
            )
            return await ollama_chat(ollama_request)
        except Exception as e:
            logger.error(f"转换Cherry Studio聊天请求失败: {e}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "id": "chatcmpl-error",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": body.get("model", "tinyllama:latest"),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "连接正常，但请求格式需要调整。"
                        },
                        "finish_reason": "stop"
                    }]
                }
            )
            
    except Exception as e:
        logger.error(f"处理Cherry Studio聊天完成端点请求失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "id": "chatcmpl-error",
                "object": "chat.completion", 
                "created": int(time.time()),
                "model": "tinyllama:latest",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "本地大模型防护系统连接正常。"
                    },
                    "finish_reason": "stop"
                }]
            }
        )

@router.post("/api/v1/ollama/v1/responses")
async def openai_responses_for_cherry(request: Request):
    """为Cherry Studio提供responses端点（处理连接检测）。"""
    try:
        # 获取请求体
        body = await request.json()
        
        # 如果是空请求或者检测请求，返回成功状态
        if not body or not body.get("model") or not body.get("messages"):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "object": "response",
                    "status": "success",
                    "message": "本地大模型防护系统连接正常",
                    "available_models": ["tinyllama:latest", "phi3:latest", "llama3.2:latest", "qwen3:latest", "deepseek-r1:14b"]
                }
            )
        
        # 如果是完整的聊天请求，转换为OllamaRequest格式
        try:
            ollama_request = OllamaRequest(
                model=body.get("model", "tinyllama:latest"),
                messages=body.get("messages", []),
                stream=body.get("stream", False),
                temperature=body.get("temperature"),
                max_tokens=body.get("max_tokens")
            )
            return await ollama_chat(ollama_request)
        except Exception as e:
            logger.error(f"转换Cherry Studio请求失败: {e}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "object": "response", 
                    "status": "success",
                    "message": "本地大模型防护系统连接正常"
                }
            )
    
    except Exception as e:
        logger.error(f"处理Cherry Studio响应端点请求失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "object": "response",
                "status": "success", 
                "message": "本地大模型防护系统连接正常"
            }
        )

# Cherry Studio路径重复问题修复 - 处理 /v1/v1 重复路径
@router.post("/api/v1/ollama/v1/v1/responses")
async def openai_responses_for_cherry_duplicate(request: Request):
    """处理Cherry Studio路径重复问题的responses端点。"""
    return await openai_responses_for_cherry(request)

@router.post("/api/v1/ollama/v1/v1/chat/completions")
async def openai_chat_for_cherry_duplicate(request: OllamaRequest):
    """处理Cherry Studio路径重复问题的聊天端点。"""
    return await ollama_chat(request)

@router.get("/api/v1/ollama/v1/v1/models")
async def get_models_for_cherry_duplicate(request: Request):
    """处理Cherry Studio路径重复问题的模型列表端点。"""
    return await get_ollama_models(request)

@router.get("/api/v1/ollama/v1")
async def get_openai_info_for_cherry():
    """为Cherry Studio提供OpenAI兼容的基础信息端点。"""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "object": "api",
            "version": "v1",
            "provider": "ollama",
            "service": "本地大模型防护系统",
            "endpoints": {
                "models": "/api/v1/ollama/v1/models",
                "chat": "/api/v1/ollama/v1/chat/completions"
            }
        }
    )

# Cherry Studio调试和连接测试端点
@router.get("/v1/test")
async def test_connection():
    """为Cherry Studio提供连接测试端点。"""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": "本地大模型防火墙连接正常",
            "service": "LLM Protection System",
            "version": "1.0.2",
            "endpoints": {
                "models": "/v1/models",
                "chat": "/v1/chat/completions"
            }
        }
    )

@router.options("/v1/models")
async def models_options():
    """处理模型列表端点的OPTIONS请求。"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "86400"
        }
    )

@router.options("/v1/chat/completions")
async def chat_options():
    """处理聊天完成端点的OPTIONS请求。"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "86400"
        }
    )

# 标准OpenAI格式路由（适用于更多客户端）
@router.get("/v1/models")
async def get_openai_models(request: Request):
    """标准OpenAI兼容的模型列表端点。"""
    return await get_ollama_models(request)

@router.post("/v1/chat/completions")
async def openai_chat_completions(request: OllamaRequest, 
                                client_id: str = Depends(check_client_license)):
    """标准OpenAI兼容的聊天完成端点。"""
    # 记录客户端活动
    from src.security.license_manager import client_tracker
    await client_tracker.update_client_activity(client_id)
    
    return await ollama_chat(request)

@router.get("/api/v1/ollama/models")
async def get_ollama_models(request: Request):
    """获取已安装的 Ollama 模型列表。

    Returns:
        已安装的 Ollama 模型列表。
    """
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

        # 如果成功获取到模型列表，转换为OpenAI格式并返回
        if models:
            # 转换为OpenAI格式的模型列表
            openai_models = {
                "object": "list",
                "data": []
            }

            for model in models:
                model_name = model.get("name") or model.get("model", "unknown")
                openai_models["data"].append({
                    "id": model_name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "ollama",
                    "permission": [],
                    "root": model_name,
                    "parent": None
                })

            return openai_models

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
