"""
Hugging Face风格的模型市场API
支持模型浏览、筛选、下载和社区功能
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.logger import logger
from src.config import settings

router = APIRouter()

# 模型数据结构
class ModelMetadata(BaseModel):
    """模型元数据"""
    id: str = Field(..., description="模型唯一标识")
    name: str = Field(..., description="模型名称")
    description: str = Field(..., description="模型描述")
    author: str = Field(..., description="作者/机构")
    license: str = Field(..., description="许可证")
    framework: str = Field(..., description="框架: pytorch, tensorflow, onnx, etc.")
    domain: str = Field(..., description="技术领域: nlp, cv, audio, multimodal")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    downloads: int = Field(0, description="下载次数")
    likes: int = Field(0, description="点赞数")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    size: str = Field(..., description="模型大小")
    language: str = Field("en", description="支持语言")
    hardware_requirements: str = Field("", description="硬件要求")

class ModelVersion(BaseModel):
    """模型版本信息"""
    version: str = Field(..., description="版本号")
    download_url: str = Field(..., description="下载地址")
    checksum: str = Field(..., description="校验和")
    release_notes: str = Field("", description="发布说明")
    created_at: str = Field(..., description="发布时间")

class ModelDetail(BaseModel):
    """模型详细信息"""
    metadata: ModelMetadata
    versions: List[ModelVersion]
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")
    community_rating: float = Field(0.0, description="社区评分")
    user_reviews: List[Dict[str, Any]] = Field(default_factory=list, description="用户评价")

class ModelFilter(BaseModel):
    """模型筛选条件"""
    framework: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[List[str]] = None
    min_downloads: Optional[int] = None
    min_rating: Optional[float] = None
    search_query: Optional[str] = None
    sort_by: str = "downloads"  # downloads, rating, date, name
    sort_order: str = "desc"  # asc, desc

# 模拟数据存储
MODELS_DB = {}
REVIEWS_DB = {}

def init_sample_data():
    """初始化示例模型数据"""
    sample_models = [
        {
            "metadata": {
                "id": "llama-3.1-405b",
                "name": "Llama 3.1 405B",
                "description": "Meta最新的405B参数超大语言模型，具备顶级的推理和代码生成能力，支持多语言对话",
                "author": "Meta AI",
                "license": "LLAMA 3.1 COMMUNITY LICENSE",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "multilingual", "code", "reasoning", "latest"],
                "downloads": 892340,
                "likes": 45621,
                "created_at": "2024-07-23",
                "updated_at": "2024-08-15",
                "size": "810GB",
                "language": "multilingual",
                "hardware_requirements": "8x A100 80GB, 1TB+ RAM"
            },
            "versions": [
                {
                    "version": "3.1",
                    "download_url": "/api/v1/models/llama-3.1-405b/download",
                    "checksum": "sha256:abc123405b",
                    "release_notes": "405B参数版本，显著提升推理和代码能力",
                    "created_at": "2024-07-23"
                }
            ],
            "performance_metrics": {
                "mmlu": 88.6,
                "gsm8k": 96.8,
                "human_eval": 89.0,
                "winogrande": 87.5
            },
            "community_rating": 4.9
        },
        {
            "metadata": {
                "id": "llama-3.1-70b",
                "name": "Llama 3.1 70B",
                "description": "Meta开源的70B参数大语言模型，在性能和效率之间取得完美平衡",
                "author": "Meta AI",
                "license": "LLAMA 3.1 COMMUNITY LICENSE",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "multilingual", "code", "efficient"],
                "downloads": 654230,
                "likes": 32891,
                "created_at": "2024-07-23",
                "updated_at": "2024-08-15",
                "size": "140GB",
                "language": "multilingual",
                "hardware_requirements": "2x A100 80GB, 256GB+ RAM"
            },
            "versions": [
                {
                    "version": "3.1",
                    "download_url": "/api/v1/models/llama-3.1-70b/download",
                    "checksum": "sha256:abc12370b",
                    "release_notes": "70B参数版本，优化的推理性能",
                    "created_at": "2024-07-23"
                }
            ],
            "performance_metrics": {
                "mmlu": 83.6,
                "gsm8k": 95.1,
                "human_eval": 80.5,
                "winogrande": 85.0
            },
            "community_rating": 4.8
        },
        {
            "metadata": {
                "id": "qwen2.5-72b",
                "name": "Qwen2.5 72B",
                "description": "阿里巴巴最新的72B参数大语言模型，在中文理解和推理方面表现卓越",
                "author": "Alibaba Cloud",
                "license": "Apache 2.0",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "chinese", "multilingual", "reasoning", "latest"],
                "downloads": 423156,
                "likes": 28934,
                "created_at": "2024-09-19",
                "updated_at": "2024-10-15",
                "size": "144GB",
                "language": "multilingual",
                "hardware_requirements": "2x A100 80GB, 256GB+ RAM"
            },
            "versions": [
                {
                    "version": "2.5",
                    "download_url": "/api/v1/models/qwen2.5-72b/download",
                    "checksum": "sha256:qwen25072b",
                    "release_notes": "大幅提升中文理解和数学推理能力",
                    "created_at": "2024-09-19"
                }
            ],
            "performance_metrics": {
                "mmlu": 84.2,
                "gsm8k": 91.6,
                "human_eval": 64.6,
                "c_eval": 89.5
            },
            "community_rating": 4.7
        },
        {
            "metadata": {
                "id": "deepseek-coder-v2",
                "name": "DeepSeek Coder V2",
                "description": "DeepSeek最新的代码生成模型，支持236种编程语言，代码生成能力业界领先",
                "author": "DeepSeek AI",
                "license": "DeepSeek License",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["code", "programming", "multilingual", "latest"],
                "downloads": 387642,
                "likes": 25678,
                "created_at": "2024-06-20",
                "updated_at": "2024-08-10",
                "size": "67GB",
                "language": "multilingual",
                "hardware_requirements": "A100 80GB, 128GB+ RAM"
            },
            "versions": [
                {
                    "version": "2.0",
                    "download_url": "/api/v1/models/deepseek-coder-v2/download",
                    "checksum": "sha256:deepseekv2",
                    "release_notes": "支持236种编程语言，大幅提升代码生成质量",
                    "created_at": "2024-06-20"
                }
            ],
            "performance_metrics": {
                "human_eval": 90.2,
                "mbpp": 76.2,
                "code_contests": 28.5,
                "apps": 48.8
            },
            "community_rating": 4.8
        },
        {
            "metadata": {
                "id": "llama-3-8b",
                "name": "Llama 3 8B",
                "description": "Meta开源的8B参数大语言模型，支持多语言和代码生成",
                "author": "Meta AI",
                "license": "LLAMA 3 COMMUNITY LICENSE",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "multilingual", "code"],
                "downloads": 1254230,
                "likes": 68921,
                "created_at": "2024-04-18",
                "updated_at": "2024-07-15",
                "size": "15.2GB",
                "language": "multilingual",
                "hardware_requirements": "16GB+ RAM, GPU recommended"
            },
            "versions": [
                {
                    "version": "1.0.0",
                    "download_url": "/api/v1/models/llama-3-8b/download",
                    "checksum": "sha256:abc123",
                    "release_notes": "初始版本发布",
                    "created_at": "2024-04-18"
                }
            ],
            "performance_metrics": {
                "mmlu": 68.4,
                "gsm8k": 79.6,
                "human_eval": 26.2,
                "winogrande": 81.1
            },
            "community_rating": 4.7
        },
        {
            "metadata": {
                "id": "flux-1-dev",
                "name": "FLUX.1 [dev]",
                "description": "Black Forest Labs最新的文本到图像生成模型，具备卓越的图像质量和文本理解能力",
                "author": "Black Forest Labs",
                "license": "FLUX.1 [dev] Non-Commercial License",
                "framework": "pytorch",
                "domain": "cv",
                "tags": ["diffusion", "image-generation", "text-to-image", "latest", "high-quality"],
                "downloads": 567890,
                "likes": 34521,
                "created_at": "2024-08-01",
                "updated_at": "2024-09-15",
                "size": "23.8GB",
                "language": "multilingual",
                "hardware_requirements": "24GB+ VRAM, RTX 4090 or A100"
            },
            "versions": [
                {
                    "version": "1.0",
                    "download_url": "/api/v1/models/flux-1-dev/download",
                    "checksum": "sha256:flux1dev",
                    "release_notes": "革命性的图像生成质量，支持复杂文本渲染",
                    "created_at": "2024-08-01"
                }
            ],
            "performance_metrics": {
                "fid": 8.7,
                "clip_score": 0.89,
                "aesthetic_score": 8.9,
                "inference_time": "12.5s"
            },
            "community_rating": 4.9
        },
        {
            "metadata": {
                "id": "stable-diffusion-3-medium",
                "name": "Stable Diffusion 3 Medium",
                "description": "Stability AI最新的SD3系列中等规模模型，在图像质量和效率间取得平衡",
                "author": "Stability AI",
                "license": "Stability AI Community License",
                "framework": "pytorch",
                "domain": "cv",
                "tags": ["diffusion", "image-generation", "text-to-image", "latest"],
                "downloads": 445670,
                "likes": 28934,
                "created_at": "2024-06-12",
                "updated_at": "2024-08-20",
                "size": "5.1GB",
                "language": "multilingual",
                "hardware_requirements": "12GB+ VRAM, RTX 3080 or better"
            },
            "versions": [
                {
                    "version": "3.0",
                    "download_url": "/api/v1/models/stable-diffusion-3-medium/download",
                    "checksum": "sha256:sd3medium",
                    "release_notes": "SD3架构，改进的文本理解和图像质量",
                    "created_at": "2024-06-12"
                }
            ],
            "performance_metrics": {
                "fid": 15.2,
                "clip_score": 0.76,
                "aesthetic_score": 7.8,
                "inference_time": "4.8s"
            },
            "community_rating": 4.7
        },
        {
            "metadata": {
                "id": "stable-diffusion-xl",
                "name": "Stable Diffusion XL",
                "description": "Stability AI开源的文本到图像生成模型",
                "author": "Stability AI",
                "license": "CreativeML Open RAIL++-M License",
                "framework": "pytorch",
                "domain": "cv",
                "tags": ["text-to-image", "generative", "diffusion"],
                "downloads": 1287450,
                "likes": 75632,
                "created_at": "2023-07-26",
                "updated_at": "2024-01-10",
                "size": "6.9GB",
                "language": "en",
                "hardware_requirements": "8GB+ RAM, GPU required"
            },
            "versions": [
                {
                    "version": "1.0",
                    "download_url": "/api/v1/models/stable-diffusion-xl/download",
                    "checksum": "sha256:def456",
                    "release_notes": "SDXL基础版本",
                    "created_at": "2023-07-26"
                }
            ],
            "performance_metrics": {
                "fid": 8.32,
                "clip_score": 0.301,
                "aesthetic_score": 6.23
            },
            "community_rating": 4.5
        },
        {
            "metadata": {
                "id": "whisper-large-v3-turbo",
                "name": "Whisper Large v3 Turbo",
                "description": "OpenAI最新的Whisper Turbo版本，大幅提升推理速度，支持实时语音识别",
                "author": "OpenAI",
                "license": "MIT",
                "framework": "pytorch",
                "domain": "audio",
                "tags": ["speech-to-text", "multilingual", "transcription", "real-time", "latest"],
                "downloads": 456780,
                "likes": 28934,
                "created_at": "2024-11-20",
                "updated_at": "2024-11-20",
                "size": "1.5GB",
                "language": "multilingual",
                "hardware_requirements": "2GB+ RAM, optimized for CPU"
            },
            "versions": [
                {
                    "version": "turbo",
                    "download_url": "/api/v1/models/whisper-large-v3-turbo/download",
                    "checksum": "sha256:whisperturbo",
                    "release_notes": "8倍速度提升，保持高精度，支持实时转录",
                    "created_at": "2024-11-20"
                }
            ],
            "performance_metrics": {
                "wer_english": 2.1,
                "wer_multilingual": 6.8,
                "latency": 0.1,
                "speed_improvement": "8x"
            },
            "community_rating": 4.9
        },
        {
            "metadata": {
                "id": "whisper-large-v3",
                "name": "Whisper Large v3",
                "description": "OpenAI开源的语音识别模型，支持99种语言",
                "author": "OpenAI",
                "license": "MIT",
                "framework": "pytorch",
                "domain": "audio",
                "tags": ["speech-to-text", "multilingual", "transcription"],
                "downloads": 1189230,
                "likes": 60245,
                "created_at": "2023-10-30",
                "updated_at": "2024-03-15",
                "size": "2.9GB",
                "language": "multilingual",
                "hardware_requirements": "4GB+ RAM"
            },
            "versions": [
                {
                    "version": "v3",
                    "download_url": "/api/v1/models/whisper-large-v3/download",
                    "checksum": "sha256:ghi789",
                    "release_notes": "支持更多语言，提升准确率",
                    "created_at": "2023-10-30"
                }
            ],
            "performance_metrics": {
                "wer_english": 2.7,
                "wer_multilingual": 8.3,
                "latency": 0.8
            },
            "community_rating": 4.8
        },
        {
            "metadata": {
                "id": "claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic最新的Claude 3.5 Sonnet模型，在推理、编程和创意写作方面表现卓越",
                "author": "Anthropic",
                "license": "Anthropic Commercial License",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "reasoning", "coding", "creative", "latest", "claude"],
                "downloads": 756890,
                "likes": 42156,
                "created_at": "2024-06-20",
                "updated_at": "2024-10-22",
                "size": "Unknown",
                "language": "multilingual",
                "hardware_requirements": "API Access Only"
            },
            "versions": [
                {
                    "version": "3.5",
                    "download_url": "/api/v1/models/claude-3.5-sonnet/download",
                    "checksum": "sha256:claude35sonnet",
                    "release_notes": "大幅提升编程和推理能力，支持200K上下文",
                    "created_at": "2024-06-20"
                }
            ],
            "performance_metrics": {
                "mmlu": 88.7,
                "human_eval": 92.0,
                "gsm8k": 96.4,
                "math": 71.1
            },
            "community_rating": 4.9
        },
        {
            "metadata": {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI最新的多模态大语言模型，支持文本、图像、音频的理解和生成",
                "author": "OpenAI",
                "license": "OpenAI Commercial License",
                "framework": "pytorch",
                "domain": "multimodal",
                "tags": ["llm", "multimodal", "vision", "audio", "latest", "gpt"],
                "downloads": 892340,
                "likes": 51234,
                "created_at": "2024-05-13",
                "updated_at": "2024-11-20",
                "size": "Unknown",
                "language": "multilingual",
                "hardware_requirements": "API Access Only"
            },
            "versions": [
                {
                    "version": "4o",
                    "download_url": "/api/v1/models/gpt-4o/download",
                    "checksum": "sha256:gpt4o",
                    "release_notes": "多模态能力，实时语音对话，图像理解",
                    "created_at": "2024-05-13"
                }
            ],
            "performance_metrics": {
                "mmlu": 87.2,
                "human_eval": 90.2,
                "gsm8k": 95.8,
                "vision_qa": 88.4
            },
            "community_rating": 4.8
        },
        {
            "metadata": {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "description": "Google最新的Gemini 1.5 Pro模型，支持200万token超长上下文，多模态理解能力强",
                "author": "Google DeepMind",
                "license": "Google AI License",
                "framework": "tensorflow",
                "domain": "multimodal",
                "tags": ["llm", "multimodal", "long-context", "vision", "latest", "gemini"],
                "downloads": 634567,
                "likes": 38921,
                "created_at": "2024-02-15",
                "updated_at": "2024-10-15",
                "size": "Unknown",
                "language": "multilingual",
                "hardware_requirements": "API Access Only"
            },
            "versions": [
                {
                    "version": "1.5",
                    "download_url": "/api/v1/models/gemini-1.5-pro/download",
                    "checksum": "sha256:gemini15pro",
                    "release_notes": "200万token上下文，多模态理解，代码生成",
                    "created_at": "2024-02-15"
                }
            ],
            "performance_metrics": {
                "mmlu": 85.9,
                "human_eval": 84.7,
                "gsm8k": 91.7,
                "long_context": 99.2
            },
            "community_rating": 4.7
        },
        {
            "metadata": {
                "id": "yi-34b-chat",
                "name": "Yi-34B-Chat",
                "description": "零一万物开源的34B参数对话模型，在中英文理解和生成方面表现优异",
                "author": "01.AI",
                "license": "Apache 2.0",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "chinese", "chat", "multilingual", "open-source"],
                "downloads": 345678,
                "likes": 23456,
                "created_at": "2024-01-23",
                "updated_at": "2024-08-15",
                "size": "68GB",
                "language": "multilingual",
                "hardware_requirements": "A100 80GB, 128GB+ RAM"
            },
            "versions": [
                {
                    "version": "1.0",
                    "download_url": "/api/v1/models/yi-34b-chat/download",
                    "checksum": "sha256:yi34bchat",
                    "release_notes": "34B参数对话模型，优秀的中英文能力",
                    "created_at": "2024-01-23"
                }
            ],
            "performance_metrics": {
                "mmlu": 76.3,
                "c_eval": 81.8,
                "gsm8k": 67.9,
                "human_eval": 26.2
            },
            "community_rating": 4.6
        },
        {
            "metadata": {
                "id": "mixtral-8x22b",
                "name": "Mixtral 8x22B",
                "description": "Mistral AI最新的专家混合模型，141B总参数，39B激活参数，性能卓越",
                "author": "Mistral AI",
                "license": "Apache 2.0",
                "framework": "pytorch",
                "domain": "nlp",
                "tags": ["llm", "mixture-of-experts", "multilingual", "latest", "open-source"],
                "downloads": 287654,
                "likes": 19876,
                "created_at": "2024-04-17",
                "updated_at": "2024-09-10",
                "size": "281GB",
                "language": "multilingual",
                "hardware_requirements": "4x A100 80GB, 512GB+ RAM"
            },
            "versions": [
                {
                    "version": "1.0",
                    "download_url": "/api/v1/models/mixtral-8x22b/download",
                    "checksum": "sha256:mixtral8x22b",
                    "release_notes": "专家混合架构，141B参数，39B激活",
                    "created_at": "2024-04-17"
                }
            ],
            "performance_metrics": {
                "mmlu": 77.8,
                "gsm8k": 88.4,
                "human_eval": 45.1,
                "winogrande": 78.6
            },
            "community_rating": 4.7
        },
        {
            "metadata": {
                "id": "midjourney-v6",
                "name": "Midjourney v6",
                "description": "Midjourney最新的v6版本，图像生成质量和文本理解能力大幅提升",
                "author": "Midjourney Inc.",
                "license": "Midjourney Commercial License",
                "framework": "proprietary",
                "domain": "cv",
                "tags": ["image-generation", "text-to-image", "artistic", "latest", "commercial"],
                "downloads": 1234567,
                "likes": 89012,
                "created_at": "2023-12-21",
                "updated_at": "2024-11-01",
                "size": "Unknown",
                "language": "multilingual",
                "hardware_requirements": "Discord Bot Access Only"
            },
            "versions": [
                {
                    "version": "6.0",
                    "download_url": "/api/v1/models/midjourney-v6/download",
                    "checksum": "sha256:midjourneyv6",
                    "release_notes": "更精确的文本理解，更高的图像质量",
                    "created_at": "2023-12-21"
                }
            ],
            "performance_metrics": {
                "aesthetic_score": 9.2,
                "text_adherence": 8.8,
                "style_consistency": 9.0,
                "user_preference": 92.5
            },
            "community_rating": 4.9
        },
        {
            "metadata": {
                "id": "suno-v3.5",
                "name": "Suno v3.5",
                "description": "Suno最新的AI音乐生成模型，支持从文本生成高质量音乐和歌曲",
                "author": "Suno Inc.",
                "license": "Suno Commercial License",
                "framework": "proprietary",
                "domain": "audio",
                "tags": ["music-generation", "text-to-music", "audio", "latest", "creative"],
                "downloads": 456789,
                "likes": 34567,
                "created_at": "2024-03-21",
                "updated_at": "2024-10-15",
                "size": "Unknown",
                "language": "multilingual",
                "hardware_requirements": "Web App Access Only"
            },
            "versions": [
                {
                    "version": "3.5",
                    "download_url": "/api/v1/models/suno-v3.5/download",
                    "checksum": "sha256:sunov35",
                    "release_notes": "更长的音乐生成，更好的音质和风格控制",
                    "created_at": "2024-03-21"
                }
            ],
            "performance_metrics": {
                "audio_quality": 8.9,
                "text_adherence": 8.5,
                "musical_coherence": 8.7,
                "generation_time": "45s"
            },
            "community_rating": 4.8
        }
    ]

    for model_data in sample_models:
        model_id = model_data["metadata"]["id"]
        MODELS_DB[model_id] = model_data
        REVIEWS_DB[model_id] = []

# 初始化示例数据
init_sample_data()

@router.get("/models", response_model=List[ModelMetadata])
async def list_models(
    framework: Optional[str] = Query(None, description="框架筛选"),
    domain: Optional[str] = Query(None, description="领域筛选"),
    tag: Optional[str] = Query(None, description="标签筛选"),
    min_downloads: Optional[int] = Query(None, description="最小下载量"),
    min_rating: Optional[float] = Query(None, description="最小评分"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("downloads", description="排序字段: downloads, rating, date, name"),
    sort_order: str = Query("desc", description="排序顺序: asc, desc"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量")
):
    """获取模型列表（支持筛选和排序）"""
    try:
        models = list(MODELS_DB.values())
        
        # 应用筛选条件
        filtered_models = []
        for model in models:
            metadata = model["metadata"]
            
            if framework and metadata["framework"] != framework:
                continue
            if domain and metadata["domain"] != domain:
                continue
            if tag and tag not in metadata["tags"]:
                continue
            if min_downloads and metadata["downloads"] < min_downloads:
                continue
            if min_rating and model["community_rating"] < min_rating:
                continue
            if search and search.lower() not in metadata["name"].lower() and \
               search.lower() not in metadata["description"].lower():
                continue
                
            filtered_models.append(metadata)
        
        # 应用排序
        reverse = sort_order.lower() == "desc"
        if sort_by == "downloads":
            filtered_models.sort(key=lambda x: x["downloads"], reverse=reverse)
        elif sort_by == "rating":
            filtered_models.sort(key=lambda x: MODELS_DB[x["id"]]["community_rating"], reverse=reverse)
        elif sort_by == "date":
            filtered_models.sort(key=lambda x: x["created_at"], reverse=reverse)
        elif sort_by == "name":
            filtered_models.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        
        # 分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_models = filtered_models[start_idx:end_idx]
        
        return paginated_models
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")

@router.get("/models/{model_id}", response_model=ModelDetail)
async def get_model_detail(model_id: str):
    """获取模型详细信息"""
    if model_id not in MODELS_DB:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    model_data = MODELS_DB[model_id].copy()
    model_data["user_reviews"] = REVIEWS_DB.get(model_id, [])
    return model_data

@router.post("/models/{model_id}/download")
async def download_model(model_id: str):
    """下载模型（记录下载次数）"""
    if model_id not in MODELS_DB:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    # 增加下载计数
    MODELS_DB[model_id]["metadata"]["downloads"] += 1
    
    # 这里应该返回实际的模型文件
    # 目前返回下载信息
    return {
        "status": "success",
        "message": "开始下载",
        "download_url": MODELS_DB[model_id]["versions"][0]["download_url"],
        "model_id": model_id,
        "downloads": MODELS_DB[model_id]["metadata"]["downloads"]
    }

@router.post("/models/{model_id}/like")
async def like_model(model_id: str):
    """点赞模型"""
    if model_id not in MODELS_DB:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    MODELS_DB[model_id]["metadata"]["likes"] += 1
    return {
        "status": "success",
        "likes": MODELS_DB[model_id]["metadata"]["likes"]
    }

@router.post("/models/{model_id}/review")
async def add_model_review(
    model_id: str,
    rating: int = Query(..., ge=1, le=5, description="评分(1-5)"),
    comment: str = Query(..., description="评论内容"),
    user: str = Query("anonymous", description="用户名")
):
    """添加模型评价"""
    if model_id not in MODELS_DB:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="评分必须在1-5之间")
    
    review = {
        "id": str(uuid.uuid4()),
        "user": user,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now().isoformat(),
        "helpful": 0
    }
    
    REVIEWS_DB[model_id].append(review)
    
    # 更新平均评分
    reviews = REVIEWS_DB[model_id]
    total_rating = sum(r["rating"] for r in reviews)
    MODELS_DB[model_id]["community_rating"] = round(total_rating / len(reviews), 1)
    
    return {"status": "success", "review_id": review["id"]}

@router.get("/models/{model_id}/reviews")
async def get_model_reviews(
    model_id: str,
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量")
):
    """获取模型评价列表"""
    if model_id not in MODELS_DB:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    reviews = REVIEWS_DB.get(model_id, [])
    
    # 分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_reviews = reviews[start_idx:end_idx]
    
    return {
        "total": len(reviews),
        "page": page,
        "page_size": page_size,
        "reviews": paginated_reviews
    }

@router.get("/models/stats/summary")
async def get_model_stats():
    """获取模型市场统计信息"""
    total_models = len(MODELS_DB)
    total_downloads = sum(model["metadata"]["downloads"] for model in MODELS_DB.values())
    total_likes = sum(model["metadata"]["likes"] for model in MODELS_DB.values())
    
    # 按框架统计
    framework_stats = {}
    for model in MODELS_DB.values():
        framework = model["metadata"]["framework"]
        framework_stats[framework] = framework_stats.get(framework, 0) + 1
    
    # 按领域统计
    domain_stats = {}
    for model in MODELS_DB.values():
        domain = model["metadata"]["domain"]
        domain_stats[domain] = domain_stats.get(domain, 0) + 1
    
    return {
        "total_models": total_models,
        "total_downloads": total_downloads,
        "total_likes": total_likes,
        "frameworks": framework_stats,
        "domains": domain_stats
    }

@router.get("/models/search/suggestions")
async def get_search_suggestions(q: str = Query(..., description="搜索关键词")):
    """获取搜索建议"""
    suggestions = []
    
    for model in MODELS_DB.values():
        metadata = model["metadata"]
        name = metadata["name"]
        description = metadata["description"]
        tags = metadata["tags"]
        
        if q.lower() in name.lower():
            suggestions.append({
                "type": "model",
                "id": metadata["id"],
                "name": name,
                "match_type": "name"
            })
        elif q.lower() in description.lower():
            suggestions.append({
                "type": "model", 
                "id": metadata["id"],
                "name": name,
                "match_type": "description"
            })
        elif any(q.lower() in tag.lower() for tag in tags):
            suggestions.append({
                "type": "model",
                "id": metadata["id"],
                "name": name,
                "match_type": "tag"
            })
    
    return {"query": q, "suggestions": suggestions[:10]}

# 注册到主应用
def setup_model_market(app):
    """设置模型市场路由"""
    app.include_router(router)
    logger.info("模型市场API已注册")