"""
模型同步系统
支持从多个外部源同步模型数据
"""

from .models import (
    UnifiedModelData, 
    SyncStatus, 
    RawModelData, 
    RawModelDetail,
    SourceConfig,
    SyncConfig,
    SyncStatusEnum
)
from .adapters import (
    ModelSourceAdapter, 
    AdapterRegistry, 
    register_adapter
)

__all__ = [
    "UnifiedModelData",
    "SyncStatus", 
    "RawModelData",
    "RawModelDetail",
    "SourceConfig",
    "SyncConfig", 
    "SyncStatusEnum",
    "ModelSourceAdapter",
    "AdapterRegistry",
    "register_adapter"
]