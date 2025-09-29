"""
Hugging Face模型仓库适配器
"""

import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlencode

from src.logger import logger
from .models import RawModelData, RawModelDetail, SourceConfig
from .adapters import ModelSourceAdapter, register_adapter


@register_adapter("huggingface")
class HuggingFaceAdapter(ModelSourceAdapter):
    """Hugging Face模型仓库适配器"""
    
    def __init__(self, config: SourceConfig):
        super().__init__(config)
        self.base_url = config.api_url or "https://huggingface.co/api"
        self.api_token = config.api_token
        self.rate_limit = config.rate_limit
        self._last_request_time = 0
        self._request_count = 0
        
    async def connect(self):
        """建立HTTP会话"""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ModelSync/1.0)",
        }
        
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
            
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self._session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
        
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发起API请求，包含速率限制
        
        Args:
            endpoint: API端点
            params: 查询参数
            
        Returns:
            API响应数据
        """
        if not self._session:
            await self.connect()
            
        # 速率限制检查
        await self._check_rate_limit()
        
        url = urljoin(self.base_url, endpoint)
        if params:
            url += "?" + urlencode(params)
            
        try:
            async with self._session.get(url) as response:
                self._request_count += 1
                self._last_request_time = datetime.now().timestamp()
                
                if response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"HuggingFace API rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, params)
                
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"HuggingFace API request failed: {e}")
            raise
            
    async def _check_rate_limit(self):
        """检查并执行速率限制"""
        current_time = datetime.now().timestamp()
        
        # 如果在同一分钟内请求次数超过限制，等待
        if (current_time - self._last_request_time < 60 and 
            self._request_count >= self.rate_limit):
            wait_time = 60 - (current_time - self._last_request_time)
            logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            self._request_count = 0
            
    async def fetch_models(
        self, 
        limit: int = 100, 
        offset: int = 0,
        since: Optional[datetime] = None
    ) -> List[RawModelData]:
        """
        获取模型列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量  
            since: 获取此时间之后更新的模型
            
        Returns:
            原始模型数据列表
        """
        # 简化参数，只使用基本的limit参数
        params = {}
        if limit and limit > 0:
            params["limit"] = min(limit, 1000)
            
        try:
            data = await self._make_request("/models", params)
            
            if not isinstance(data, list):
                logger.error(f"Unexpected API response format: {type(data)}")
                return []
                
            models = []
            
            # 在客户端处理偏移量和时间过滤
            filtered_data = data
            if since:
                filtered_data = [
                    item for item in data 
                    if self._is_after_date(item.get("lastModified"), since)
                ]
            
            # 应用偏移量和限制
            start_idx = offset
            end_idx = offset + limit if limit > 0 else len(filtered_data)
            paginated_data = filtered_data[start_idx:end_idx]
            
            for item in paginated_data:
                try:
                    model = self._parse_model_data(item)
                    models.append(model)
                except Exception as e:
                    logger.warning(f"Failed to parse model {item.get('id', 'unknown')}: {e}")
                    continue
                    
            logger.info(f"Fetched {len(models)} models from HuggingFace")
            return models
            
        except Exception as e:
            logger.error(f"Failed to fetch models from HuggingFace: {e}")
            return []
            
    async def fetch_model_detail(self, model_id: str) -> Optional[RawModelDetail]:
        """
        获取模型详细信息
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型详细信息
        """
        try:
            # 获取基本信息
            model_data = await self._make_request(f"/models/{model_id}")
            basic_info = self._parse_model_data(model_data)
            
            # 获取README
            readme = None
            try:
                readme_data = await self._make_request(f"/models/{model_id}/readme")
                readme = readme_data.get("content", "")
            except:
                pass  # README可能不存在
                
            # 获取文件列表
            files = []
            try:
                files_data = await self._make_request(f"/models/{model_id}/tree/main")
                files = files_data if isinstance(files_data, list) else []
            except:
                pass
                
            return RawModelDetail(
                basic_info=basic_info,
                readme=readme,
                files=files,
                model_card=model_data.get("cardData", {}),
                performance_metrics=self._extract_metrics(model_data)
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch model detail for {model_id}: {e}")
            return None
            
    async def get_total_count(self, since: Optional[datetime] = None) -> int:
        """
        获取模型总数
        
        Args:
            since: 统计此时间之后的模型数量
            
        Returns:
            模型总数
        """
        try:
            params = {"limit": 1}  # 只需要获取总数
            if since:
                params["lastModified"] = since.isoformat()
                
            # HuggingFace API在响应头中返回总数
            if not self._session:
                await self.connect()
                
            url = urljoin(self.base_url, "/models")
            if params:
                url += "?" + urlencode(params)
                
            async with self._session.head(url) as response:
                total = response.headers.get("X-Total-Count")
                if total:
                    return int(total)
                    
            # 如果头部没有总数，尝试获取第一页来估算
            data = await self._make_request("/models", {"limit": 1})
            return len(data) * 1000  # 粗略估算
            
        except Exception as e:
            logger.error(f"Failed to get total count from HuggingFace: {e}")
            return 0
            
    def get_source_name(self) -> str:
        """获取数据源名称"""
        return "huggingface"
        
    def _parse_model_data(self, raw_data: Dict[str, Any]) -> RawModelData:
        """
        解析HuggingFace原始数据
        
        Args:
            raw_data: HuggingFace API返回的原始数据
            
        Returns:
            标准化的模型数据
        """
        # 解析时间
        created_at = None
        updated_at = None
        
        if "createdAt" in raw_data:
            created_at = datetime.fromisoformat(raw_data["createdAt"].replace("Z", "+00:00"))
        if "lastModified" in raw_data:
            updated_at = datetime.fromisoformat(raw_data["lastModified"].replace("Z", "+00:00"))
            
        # 解析标签和领域
        tags = raw_data.get("tags", [])
        pipeline_tag = raw_data.get("pipeline_tag", "")
        
        # 推断框架
        framework = "unknown"
        if any("pytorch" in tag.lower() for tag in tags):
            framework = "pytorch"
        elif any("tensorflow" in tag.lower() for tag in tags):
            framework = "tensorflow"
        elif any("jax" in tag.lower() for tag in tags):
            framework = "jax"
            
        # 推断领域
        domain = self._infer_domain(pipeline_tag, tags)
        
        return RawModelData(
            source_id=raw_data.get("id", ""),
            name=raw_data.get("id", "").split("/")[-1] if "/" in raw_data.get("id", "") else raw_data.get("id", ""),
            description=raw_data.get("description", ""),
            author=raw_data.get("id", "").split("/")[0] if "/" in raw_data.get("id", "") else "",
            license=self._extract_license(raw_data),
            framework=framework,
            domain=domain,
            tags=tags,
            downloads=raw_data.get("downloads", 0),
            likes=raw_data.get("likes", 0),
            size=self._format_size(raw_data.get("safetensors", {})),
            created_at=created_at,
            updated_at=updated_at,
            raw_data=raw_data
        )
        
    def _infer_domain(self, pipeline_tag: str, tags: List[str]) -> str:
        """根据pipeline_tag和tags推断技术领域"""
        if pipeline_tag:
            if pipeline_tag in ["text-generation", "text2text-generation", "fill-mask", "token-classification"]:
                return "nlp"
            elif pipeline_tag in ["image-classification", "object-detection", "image-segmentation"]:
                return "cv"
            elif pipeline_tag in ["automatic-speech-recognition", "text-to-speech"]:
                return "audio"
            elif pipeline_tag in ["image-to-text", "visual-question-answering"]:
                return "multimodal"
                
        # 从标签推断
        tag_str = " ".join(tags).lower()
        if any(keyword in tag_str for keyword in ["nlp", "text", "language", "bert", "gpt"]):
            return "nlp"
        elif any(keyword in tag_str for keyword in ["vision", "image", "cv", "resnet", "vit"]):
            return "cv"
        elif any(keyword in tag_str for keyword in ["audio", "speech", "wav2vec"]):
            return "audio"
        elif any(keyword in tag_str for keyword in ["multimodal", "clip", "blip"]):
            return "multimodal"
            
        return "other"
        
    def _extract_license(self, raw_data: Dict[str, Any]) -> str:
        """提取许可证信息"""
        card_data = raw_data.get("cardData", {})
        if "license" in card_data:
            return card_data["license"]
        if "license" in raw_data:
            return raw_data["license"]
        return "unknown"
        
    def _format_size(self, safetensors_data: Dict[str, Any]) -> str:
        """格式化模型大小"""
        if "total" in safetensors_data:
            size_bytes = safetensors_data["total"]
            if size_bytes > 1024**3:  # GB
                return f"{size_bytes / (1024**3):.1f}GB"
            elif size_bytes > 1024**2:  # MB
                return f"{size_bytes / (1024**2):.1f}MB"
            else:
                return f"{size_bytes / 1024:.1f}KB"
        return "unknown"
        
    def _extract_metrics(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取性能指标"""
        metrics = {}
        
        # 从model card提取指标
        card_data = raw_data.get("cardData", {})
        if "model-index" in card_data:
            model_index = card_data["model-index"]
            if isinstance(model_index, list) and model_index:
                results = model_index[0].get("results", [])
                for result in results:
                    if "metrics" in result:
                        for metric in result["metrics"]:
                            name = metric.get("name", "")
                            value = metric.get("value")
                            if name and value is not None:
                                metrics[name] = value
                                
        return metrics
        
    def _is_after_date(self, date_str: Optional[str], since: datetime) -> bool:
        """检查日期是否在指定时间之后"""
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date > since
        except:
            return False