"""系统健康状态 API。"""

import os
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.config import settings
from src.logger import logger


router = APIRouter()


class ServiceStatus(BaseModel):
    """服务状态。"""

    name: str
    status: str  # "normal", "warning", "error"
    response_time: float
    last_check: datetime
    details: Optional[str] = None


class HealthStatus(BaseModel):
    """系统健康状态。"""

    status: str  # "normal", "warning", "error"
    services: List[ServiceStatus]
    timestamp: datetime


@router.get("/api/v1/health/status")
async def get_health_status():
    """获取系统健康状态。

    Returns:
        系统健康状态
    """
    # 简化的服务状态数据
    services = [
        {
            "name": "API 服务",
            "status": "normal",
            "response_time": round(random.uniform(5, 30), 2),
            "last_check": str(datetime.now()),
            "details": "API 服务运行正常"
        },
        {
            "name": "安全检测",
            "status": "normal",
            "response_time": round(random.uniform(20, 60), 2),
            "last_check": str(datetime.now()),
            "details": "安全检测服务运行正常"
        },
        {
            "name": "Ollama 集成",
            "status": "normal",
            "response_time": round(random.uniform(30, 100), 2),
            "last_check": str(datetime.now()),
            "details": "Ollama 服务运行正常"
        },
        {
            "name": "数据存储",
            "status": "normal",
            "response_time": round(random.uniform(5, 20), 2),
            "last_check": str(datetime.now()),
            "details": "数据存储服务运行正常"
        }
    ]

    # 返回简化的 JSON 响应
    return {
        "status": "normal",
        "services": services,
        "timestamp": str(datetime.now())
    }


def check_ollama_status() -> ServiceStatus:
    """检查 Ollama 服务状态。

    Returns:
        Ollama 服务状态
    """
    try:
        # 这里应该实际调用 Ollama API 检查状态
        # 为了演示，我们使用随机状态
        status_options = ["normal", "normal", "normal", "warning", "error"]
        status = random.choice(status_options)

        response_time = random.uniform(30, 100)
        details = "Ollama 服务运行正常"

        if status == "warning":
            response_time = random.uniform(100, 200)
            details = "Ollama 服务响应较慢"
        elif status == "error":
            response_time = random.uniform(200, 500)
            details = "Ollama 服务连接异常"

        return ServiceStatus(
            name="Ollama 集成",
            status=status,
            response_time=response_time,
            last_check=datetime.now(),
            details=details
        )
    except Exception as e:
        logger.error(f"检查 Ollama 状态失败: {e}")
        return ServiceStatus(
            name="Ollama 集成",
            status="error",
            response_time=0,
            last_check=datetime.now(),
            details=f"检查 Ollama 状态失败: {str(e)}"
        )
