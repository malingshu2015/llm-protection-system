"""
第三方热门模型API接口
提供来自各大平台的最新流行大模型数据
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import httpx
import asyncio

router = APIRouter(prefix="/api/v1/trending", tags=["trending-models"])

class ModelMetrics(BaseModel):
    downloads: int
    likes: int
    rating: float
    recent_downloads: int

class TrendingModel(BaseModel):
    id: str
    name: str
    platform: str
    description: str
    size: str
    parameters: int
    downloads: str
    rating: float
    recentDownloads: str
    releaseDate: str
    features: List[str]
    trending: str
    license: str
    framework: str
    original_url: str
    last_updated: datetime

class TrendingStats(BaseModel):
    total_models: int
    total_downloads: str
    last_updated: datetime
    platforms: List[str]

# 模拟第三方平台的热门模型数据
MOCK_TRENDING_DATA = [
    {
        "id": "deepseek-r1",
        "name": "DeepSeek-R1",
        "platform": "deepseek",
        "description": "革命性的开源推理模型，性能媲美OpenAI-o1，训练成本降低15倍",
        "size": "671B (MoE)",
        "parameters": 671000000000,
        "downloads": "3.2M",
        "rating": 4.9,
        "recentDownloads": "+580K",
        "releaseDate": "2025-01-20",
        "features": ["推理能力", "链式思考", "多语言", "代码生成", "数学解题"],
        "trending": "🔥",
        "license": "MIT",
        "framework": "PyTorch",
        "original_url": "https://huggingface.co/deepseek-ai/DeepSeek-R1",
        "last_updated": datetime.now()
    },
    {
        "id": "llama-3.3-70b",
        "name": "Llama 3.3 70B",
        "platform": "meta",
        "description": "Meta最新旗舰模型，128K上下文，多语言支持，性能超越GPT-3.5",
        "size": "70B",
        "parameters": 70000000000,
        "downloads": "1.8M",
        "rating": 4.8,
        "recentDownloads": "+420K",
        "releaseDate": "2024-12-06",
        "features": ["超长上下文", "多语言", "工具调用", "安全对齐", "指令遵循"],
        "trending": "⭐",
        "license": "Llama 3.3",
        "framework": "PyTorch",
        "original_url": "https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct",
        "last_updated": datetime.now()
    },
    {
        "id": "qwen2.5-72b",
        "name": "Qwen2.5-72B",
        "platform": "alibaba",
        "description": "阿里巴巴开源的顶级模型，支持29种语言，代码和数学能力突出",
        "size": "72B",
        "parameters": 72000000000,
        "downloads": "1.5M",
        "rating": 4.8,
        "recentDownloads": "+380K",
        "releaseDate": "2024-09-19",
        "features": ["多语言", "代码生成", "数学推理", "工具调用", "MMLU SOTA"],
        "trending": "⭐",
        "license": "Apache 2.0",
        "framework": "PyTorch",
        "original_url": "https://huggingface.co/Qwen/Qwen2.5-72B-Instruct",
        "last_updated": datetime.now()
    },
    {
        "id": "exaone-4.0-32b",
        "name": "EXAONE-4.0-32B",
        "platform": "lg",
        "description": "LG最新开源模型，集成推理模式，支持英韩西三语，131K上下文",
        "size": "32B",
        "parameters": 32000000000,
        "downloads": "1.2M",
        "rating": 4.7,
        "recentDownloads": "+280K",
        "releaseDate": "2025-07-26",
        "features": ["混合注意力", "推理模式", "多语言", "长上下文", "全局理解"],
        "trending": "🆕",
        "license": "Apache 2.0",
        "framework": "PyTorch",
        "original_url": "https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-32B",
        "last_updated": datetime.now()
    },
    {
        "id": "gemma-2-27b",
        "name": "Gemma 2 27B",
        "platform": "google",
        "description": "Google开源的轻量级但强大的模型，27B参数实现SOTA性能",
        "size": "27B",
        "parameters": 27000000000,
        "downloads": "1.4M",
        "rating": 4.6,
        "recentDownloads": "+320K",
        "releaseDate": "2024-06-27",
        "features": ["轻量级", "高效", "多语言", "移动端优化", "量化支持"],
        "trending": "📱",
        "license": "Gemma",
        "framework": "JAX/TensorFlow",
        "original_url": "https://huggingface.co/google/gemma-2-27b-it",
        "last_updated": datetime.now()
    },
    {
        "id": "mistral-large-2",
        "name": "Mistral Large 2",
        "platform": "mistral",
        "description": "Mistral最新旗舰模型，128K上下文，代码和推理能力大幅提升",
        "size": "123B",
        "parameters": 123000000000,
        "downloads": "980K",
        "rating": 4.7,
        "recentDownloads": "+210K",
        "releaseDate": "2024-07-24",
        "features": ["代码生成", "推理能力", "长上下文", "函数调用", "多语言"],
        "trending": "🔥",
        "license": "Mistral Research",
        "framework": "PyTorch",
        "original_url": "https://huggingface.co/mistralai/Mistral-Large-Instruct-2407",
        "last_updated": datetime.now()
    },
    {
        "id": "command-r-08-2024",
        "name": "Command R 08-2024",
        "platform": "cohere",
        "description": "Cohere开源的32B参数模型，专为RAG优化，10语言支持",
        "size": "32B",
        "parameters": 32000000000,
        "downloads": "850K",
        "rating": 4.6,
        "recentDownloads": "+180K",
        "releaseDate": "2024-08-26",
        "features": ["RAG优化", "多语言", "长上下文", "工具调用", "检索增强"],
        "trending": "📈",
        "license": "CC-BY-NC",
        "framework": "PyTorch",
        "original_url": "https://huggingface.co/CohereLabs/c4ai-command-r-08-2024",
        "last_updated": datetime.now()
    },
    {
        "id": "phi-3.5-mini",
        "name": "Phi-3.5-mini",
        "platform": "microsoft",
        "description": "微软超轻量级模型，3.8B参数但性能媲美更大模型，移动端友好",
        "size": "3.8B",
        "parameters": 3800000000,
        "downloads": "2.1M",
        "rating": 4.5,
        "recentDownloads": "+450K",
        "releaseDate": "2024-08-20",
        "features": ["轻量级", "移动端", "低延迟", "量化支持", "设备端部署"],
        "trending": "📱",
        "license": "MIT",
        "framework": "ONNX",
        "original_url": "https://huggingface.co/microsoft/Phi-3.5-mini-instruct",
        "last_updated": datetime.now()
    }
]

@router.get("/models", response_model=List[TrendingModel])
async def get_trending_models(
    platform: Optional[str] = Query(None, description="按平台筛选"),
    size: Optional[str] = Query(None, description="按模型大小筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("popularity", description="排序方式")
):
    """获取热门大模型列表"""
    
    models = MOCK_TRENDING_DATA.copy()
    
    # 平台筛选
    if platform and platform != "all":
        models = [m for m in models if m["platform"] == platform]
    
    # 大小筛选
    if size:
        if size == "small":
            models = [m for m in models if m["parameters"] < 10000000000]
        elif size == "medium":
            models = [m for m in models if 10000000000 <= m["parameters"] <= 50000000000]
        elif size == "large":
            models = [m for m in models if m["parameters"] > 50000000000]
    
    # 搜索筛选
    if search:
        search_lower = search.lower()
        models = [m for m in models if 
                 search_lower in m["name"].lower() or 
                 search_lower in m["description"].lower() or
                 any(search_lower in f.lower() for f in m["features"])]
    
    # 排序
    if sort_by == "downloads":
        models.sort(key=lambda x: int(x["downloads"].replace("M", "000000").replace("K", "000")), reverse=True)
    elif sort_by == "rating":
        models.sort(key=lambda x: x["rating"], reverse=True)
    elif sort_by == "recent":
        models.sort(key=lambda x: x["releaseDate"], reverse=True)
    else:  # popularity
        models.sort(key=lambda x: int(x["recentDownloads"].replace("+", "").replace("K", "000").replace("M", "000000")), reverse=True)
    
    return [TrendingModel(**model) for model in models]

@router.get("/stats", response_model=TrendingStats)
async def get_trending_stats():
    """获取热门模型统计信息"""
    
    models = MOCK_TRENDING_DATA
    total_downloads = sum(int(m["downloads"].replace("M", "000000").replace("K", "000")) for m in models)
    platforms = list(set(m["platform"] for m in models))
    
    return TrendingStats(
        total_models=len(models),
        total_downloads=f"{total_downloads/1000000:.1f}M",
        last_updated=datetime.now(),
        platforms=platforms
    )

@router.get("/platforms")
async def get_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": [
            {"id": "deepseek", "name": "DeepSeek", "icon": "🤖"},
            {"id": "meta", "name": "Meta", "icon": "🦙"},
            {"id": "alibaba", "name": "Alibaba", "icon": "🛒"},
            {"id": "lg", "name": "LG", "icon": "📱"},
            {"id": "google", "name": "Google", "icon": "🔍"},
            {"id": "mistral", "name": "Mistral", "icon": "🌊"},
            {"id": "cohere", "name": "Cohere", "icon": "🔗"},
            {"id": "microsoft", "name": "Microsoft", "icon": "🪟"}
        ]
    }

@router.get("/sync")
async def sync_trending_models():
    """同步最新热门模型数据（模拟）"""
    # 这里可以集成实际的第三方API调用
    # 例如 Hugging Face Hub API, ModelScope API 等
    
    return {
        "status": "success",
        "message": "热门模型数据已同步",
        "synced_at": datetime.now(),
        "models_updated": len(MOCK_TRENDING_DATA)
    }