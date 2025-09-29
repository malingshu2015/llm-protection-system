"""
模型同步系统的数据模型定义
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SyncStatusEnum(str, Enum):
    """同步状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RawModelData(BaseModel):
    """原始模型数据（来自外部源）"""
    source_id: str = Field(..., description="源平台模型ID")
    name: str = Field(..., description="模型名称")
    description: Optional[str] = Field(None, description="模型描述")
    author: Optional[str] = Field(None, description="作者")
    license: Optional[str] = Field(None, description="许可证")
    framework: Optional[str] = Field(None, description="框架")
    domain: Optional[str] = Field(None, description="技术领域")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    downloads: int = Field(0, description="下载次数")
    likes: int = Field(0, description="点赞数")
    size: Optional[str] = Field(None, description="模型大小")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始数据")


class RawModelDetail(BaseModel):
    """原始模型详细信息"""
    basic_info: RawModelData
    readme: Optional[str] = Field(None, description="README内容")
    model_card: Optional[Dict[str, Any]] = Field(None, description="模型卡片信息")
    files: List[Dict[str, Any]] = Field(default_factory=list, description="文件列表")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")
    usage_examples: List[str] = Field(default_factory=list, description="使用示例")


class UnifiedModelData(BaseModel):
    """统一的模型数据结构"""
    id: str = Field(..., description="全局唯一ID")
    source: str = Field(..., description="数据源标识")
    source_id: str = Field(..., description="源平台ID")
    name: str = Field(..., description="模型名称")
    description: str = Field("", description="模型描述")
    author: str = Field("", description="作者")
    license: str = Field("", description="许可证")
    framework: str = Field("", description="框架")
    domain: str = Field("", description="技术领域")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    downloads: int = Field(0, description="下载次数")
    likes: int = Field(0, description="点赞数")
    size: str = Field("", description="模型大小")
    language: str = Field("en", description="支持语言")
    hardware_requirements: str = Field("", description="硬件要求")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_sync: datetime = Field(default_factory=datetime.now, description="最后同步时间")
    sync_status: SyncStatusEnum = Field(SyncStatusEnum.PENDING, description="同步状态")
    
    # 扩展信息
    readme: Optional[str] = Field(None, description="README内容")
    model_card: Optional[Dict[str, Any]] = Field(None, description="模型卡片")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")
    
    class Config:
        use_enum_values = True


class SyncStatus(BaseModel):
    """同步状态跟踪"""
    source: str = Field(..., description="数据源名称")
    last_sync: Optional[datetime] = Field(None, description="最后同步时间")
    total_models: int = Field(0, description="总模型数")
    new_models: int = Field(0, description="新增模型数")
    updated_models: int = Field(0, description="更新模型数")
    failed_models: int = Field(0, description="失败模型数")
    sync_duration: float = Field(0.0, description="同步耗时(秒)")
    status: SyncStatusEnum = Field(SyncStatusEnum.PENDING, description="同步状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        use_enum_values = True


class SourceConfig(BaseModel):
    """数据源配置"""
    name: str = Field(..., description="数据源名称")
    enabled: bool = Field(True, description="是否启用")
    api_url: str = Field(..., description="API地址")
    api_token: Optional[str] = Field(None, description="API令牌")
    rate_limit: int = Field(60, description="每分钟请求限制")
    timeout: int = Field(30, description="请求超时(秒)")
    batch_size: int = Field(100, description="批处理大小")
    sync_interval: int = Field(3600, description="同步间隔(秒)")
    full_sync_interval: int = Field(86400, description="全量同步间隔(秒)")
    
    # 数据映射配置
    field_mapping: Dict[str, str] = Field(default_factory=dict, description="字段映射")
    default_values: Dict[str, Any] = Field(default_factory=dict, description="默认值")


class SyncConfig(BaseModel):
    """同步系统配置"""
    sources: Dict[str, SourceConfig] = Field(default_factory=dict, description="数据源配置")
    sync_interval: int = Field(3600, description="默认同步间隔(秒)")
    batch_size: int = Field(100, description="默认批处理大小")
    max_retries: int = Field(3, description="最大重试次数")
    timeout: int = Field(30, description="默认请求超时(秒)")
    enable_monitoring: bool = Field(True, description="启用监控")
    log_level: str = Field("INFO", description="日志级别")
    
    # 数据库配置
    database_url: Optional[str] = Field(None, description="数据库连接URL")
    cache_ttl: int = Field(3600, description="缓存TTL(秒)")
    
    # 并发控制
    max_concurrent_syncs: int = Field(3, description="最大并发同步数")
    worker_pool_size: int = Field(10, description="工作线程池大小")