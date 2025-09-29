"""
测试数据模型和适配器接口
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from .models import UnifiedModelData, SyncStatus, RawModelData, SourceConfig, SyncStatusEnum
from .adapters import ModelSourceAdapter, AdapterRegistry, register_adapter


@register_adapter("test")
class TestAdapter(ModelSourceAdapter):
    """测试适配器实现"""
    
    async def fetch_models(
        self, 
        limit: int = 100, 
        offset: int = 0,
        since: Optional[datetime] = None
    ) -> List[RawModelData]:
        """返回测试数据"""
        test_models = []
        for i in range(min(limit, 3)):  # 最多返回3个测试模型
            model = RawModelData(
                source_id=f"test-model-{offset + i}",
                name=f"Test Model {offset + i}",
                description=f"This is test model {offset + i}",
                author="Test Author",
                license="MIT",
                framework="pytorch",
                domain="nlp",
                tags=["test", "example"],
                downloads=100 + i,
                likes=10 + i,
                size="1.2GB",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            test_models.append(model)
        return test_models
    
    async def fetch_model_detail(self, model_id: str) -> Optional[RawModelData]:
        """返回测试模型详情"""
        if model_id.startswith("test-model-"):
            return RawModelData(
                source_id=model_id,
                name=f"Detailed {model_id}",
                description=f"Detailed description for {model_id}",
                author="Test Author",
                license="MIT",
                framework="pytorch",
                domain="nlp",
                tags=["test", "detailed"],
                downloads=500,
                likes=50,
                size="2.1GB"
            )
        return None
    
    async def get_total_count(self, since: Optional[datetime] = None) -> int:
        """返回测试总数"""
        return 10
    
    def get_source_name(self) -> str:
        """返回数据源名称"""
        return "test"


async def test_models():
    """测试数据模型"""
    print("测试数据模型...")
    
    # 测试UnifiedModelData
    model = UnifiedModelData(
        id="test-1",
        source="test",
        source_id="test-model-1",
        name="Test Model",
        description="A test model",
        author="Test Author"
    )
    print(f"创建模型: {model.name}")
    
    # 测试SyncStatus
    status = SyncStatus(
        source="test",
        total_models=10,
        new_models=5,
        status=SyncStatusEnum.COMPLETED
    )
    print(f"同步状态: {status.status}")
    
    print("数据模型测试完成 ✓")


async def test_adapter():
    """测试适配器接口"""
    print("\n测试适配器接口...")
    
    # 创建测试配置
    config = SourceConfig(
        name="test",
        api_url="http://test.example.com",
        field_mapping={
            "name": "model_name",
            "description": "model_desc"
        }
    )
    
    # 创建适配器
    adapter = AdapterRegistry.create_adapter("test", config)
    if not adapter:
        print("❌ 无法创建测试适配器")
        return
    
    print(f"创建适配器: {adapter.get_source_name()}")
    
    # 测试获取模型列表
    models = await adapter.fetch_models(limit=2)
    print(f"获取到 {len(models)} 个模型")
    for model in models:
        print(f"  - {model.name} ({model.source_id})")
    
    # 测试获取模型详情
    if models:
        detail = await adapter.fetch_model_detail(models[0].source_id)
        if detail:
            print(f"获取详情: {detail.name}")
    
    # 测试获取总数
    total = await adapter.get_total_count()
    print(f"总模型数: {total}")
    
    # 测试连接验证
    is_valid = await adapter.validate_connection()
    print(f"连接验证: {'✓' if is_valid else '❌'}")
    
    print("适配器接口测试完成 ✓")


async def test_registry():
    """测试适配器注册表"""
    print("\n测试适配器注册表...")
    
    # 列出已注册的适配器
    adapters = AdapterRegistry.list_adapters()
    print(f"已注册适配器: {adapters}")
    
    # 测试获取适配器
    adapter_class = AdapterRegistry.get_adapter("test")
    print(f"获取适配器类: {adapter_class.__name__ if adapter_class else 'None'}")
    
    print("注册表测试完成 ✓")


async def main():
    """运行所有测试"""
    print("开始测试模型同步基础组件...\n")
    
    await test_models()
    await test_adapter()
    await test_registry()
    
    print("\n所有测试完成! 🎉")


if __name__ == "__main__":
    asyncio.run(main())