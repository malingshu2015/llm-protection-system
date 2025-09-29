"""
数据源适配器基础接口和抽象类
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import RawModelData, RawModelDetail, SyncStatus, SourceConfig


class ModelSourceAdapter(ABC):
    """模型数据源适配器抽象基类"""
    
    def __init__(self, config: SourceConfig):
        """
        初始化适配器
        
        Args:
            config: 数据源配置
        """
        self.config = config
        self.source_name = config.name
        self._session = None
        
    @abstractmethod
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
            since: 获取此时间之后更新的模型（增量同步）
            
        Returns:
            原始模型数据列表
        """
        pass
    
    @abstractmethod
    async def fetch_model_detail(self, model_id: str) -> Optional[RawModelDetail]:
        """
        获取模型详细信息
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型详细信息，如果不存在返回None
        """
        pass
    
    @abstractmethod
    async def get_total_count(self, since: Optional[datetime] = None) -> int:
        """
        获取模型总数
        
        Args:
            since: 统计此时间之后的模型数量
            
        Returns:
            模型总数
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        获取数据源名称
        
        Returns:
            数据源名称
        """
        pass
    
    async def validate_connection(self) -> bool:
        """
        验证连接是否正常
        
        Returns:
            连接是否正常
        """
        try:
            # 尝试获取少量数据来验证连接
            await self.fetch_models(limit=1)
            return True
        except Exception:
            return False
    
    async def get_sync_info(self) -> Dict[str, Any]:
        """
        获取同步相关信息
        
        Returns:
            同步信息字典
        """
        return {
            "source_name": self.get_source_name(),
            "api_url": self.config.api_url,
            "rate_limit": self.config.rate_limit,
            "batch_size": self.config.batch_size,
            "enabled": self.config.enabled
        }
    
    def transform_raw_data(self, raw_data: Dict[str, Any]) -> RawModelData:
        """
        转换原始数据为标准格式
        
        Args:
            raw_data: 原始数据字典
            
        Returns:
            标准化的模型数据
        """
        # 应用字段映射
        mapped_data = {}
        for target_field, source_field in self.config.field_mapping.items():
            if source_field in raw_data:
                mapped_data[target_field] = raw_data[source_field]
        
        # 应用默认值
        for field, default_value in self.config.default_values.items():
            if field not in mapped_data:
                mapped_data[field] = default_value
        
        # 确保必填字段存在
        if "source_id" not in mapped_data:
            mapped_data["source_id"] = raw_data.get("id", "")
        if "name" not in mapped_data:
            mapped_data["name"] = raw_data.get("name", "")
        
        # 保存原始数据
        mapped_data["raw_data"] = raw_data
        
        return RawModelData(**mapped_data)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    async def connect(self):
        """建立连接"""
        # 子类可以重写此方法来建立连接
        pass
    
    async def disconnect(self):
        """断开连接"""
        # 子类可以重写此方法来清理资源
        if self._session:
            await self._session.close()
            self._session = None


class AdapterRegistry:
    """适配器注册表"""
    
    _adapters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, source_name: str, adapter_class: type):
        """
        注册适配器
        
        Args:
            source_name: 数据源名称
            adapter_class: 适配器类
        """
        cls._adapters[source_name] = adapter_class
    
    @classmethod
    def get_adapter(cls, source_name: str) -> Optional[type]:
        """
        获取适配器类
        
        Args:
            source_name: 数据源名称
            
        Returns:
            适配器类，如果不存在返回None
        """
        return cls._adapters.get(source_name)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """
        列出所有已注册的适配器
        
        Returns:
            适配器名称列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def create_adapter(cls, source_name: str, config: SourceConfig) -> Optional[ModelSourceAdapter]:
        """
        创建适配器实例
        
        Args:
            source_name: 数据源名称
            config: 配置
            
        Returns:
            适配器实例，如果不存在返回None
        """
        adapter_class = cls.get_adapter(source_name)
        if adapter_class:
            return adapter_class(config)
        return None


def register_adapter(source_name: str):
    """
    适配器注册装饰器
    
    Args:
        source_name: 数据源名称
    """
    def decorator(adapter_class):
        AdapterRegistry.register(source_name, adapter_class)
        return adapter_class
    return decorator