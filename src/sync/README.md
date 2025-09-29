# 模型同步系统

这个模块提供了一个可扩展的模型同步系统，支持从多个外部模型仓库获取最新的模型信息。

## 核心组件

### 1. 数据模型

- `UnifiedModelData`: 统一的模型数据结构
- `RawModelData`: 原始模型数据（来自外部源）
- `SyncStatus`: 同步状态跟踪
- `SourceConfig`: 数据源配置
- `SyncConfig`: 同步系统配置

### 2. 适配器接口

- `ModelSourceAdapter`: 数据源适配器抽象基类
- `AdapterRegistry`: 适配器注册表
- `register_adapter`: 适配器注册装饰器

## 使用示例

### 创建自定义适配器

```python
from src.sync import ModelSourceAdapter, register_adapter, RawModelData
from typing import List, Optional
from datetime import datetime

@register_adapter("my_source")
class MySourceAdapter(ModelSourceAdapter):
    async def fetch_models(self, limit: int = 100, offset: int = 0, since: Optional[datetime] = None) -> List[RawModelData]:
        # 实现获取模型列表的逻辑
        pass
    
    async def fetch_model_detail(self, model_id: str) -> Optional[RawModelDetail]:
        # 实现获取模型详情的逻辑
        pass
    
    async def get_total_count(self, since: Optional[datetime] = None) -> int:
        # 实现获取总数的逻辑
        pass
    
    def get_source_name(self) -> str:
        return "my_source"
```

### 使用适配器

```python
from src.sync import AdapterRegistry, SourceConfig

# 创建配置
config = SourceConfig(
    name="my_source",
    api_url="https://api.example.com",
    api_token="your_token_here",
    batch_size=50
)

# 创建适配器实例
adapter = AdapterRegistry.create_adapter("my_source", config)

# 使用适配器
async with adapter:
    models = await adapter.fetch_models(limit=10)
    for model in models:
        print(f"Model: {model.name}")
```

### 配置数据源

```python
from src.sync import SourceConfig

config = SourceConfig(
    name="huggingface",
    api_url="https://huggingface.co/api/models",
    rate_limit=60,
    batch_size=100,
    field_mapping={
        "name": "modelId",
        "description": "description", 
        "downloads": "downloads",
        "likes": "likes"
    },
    default_values={
        "framework": "pytorch",
        "domain": "nlp"
    }
)
```

## 测试

运行测试来验证基础功能：

```bash
python -m src.sync.test_models
```

## 下一步

1. 实现具体的数据源适配器（Hugging Face、Ollama等）
2. 创建同步调度器
3. 添加数据存储层
4. 实现监控和日志系统