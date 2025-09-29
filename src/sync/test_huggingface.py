"""
测试Hugging Face适配器
"""

import asyncio
from datetime import datetime, timedelta

from .models import SourceConfig
from .adapters import AdapterRegistry
from .huggingface_adapter import HuggingFaceAdapter


async def test_huggingface_adapter():
    """测试Hugging Face适配器"""
    print("测试Hugging Face适配器...")
    
    # 创建配置
    config = SourceConfig(
        name="huggingface",
        api_url="https://huggingface.co/api",
        rate_limit=10,  # 降低速率限制用于测试
        timeout=30,
        batch_size=5
    )
    
    # 创建适配器
    adapter = AdapterRegistry.create_adapter("huggingface", config)
    if not adapter:
        print("❌ 无法创建HuggingFace适配器")
        return
        
    print(f"✓ 创建适配器: {adapter.get_source_name()}")
    
    try:
        async with adapter:
            # 测试连接验证
            print("测试连接...")
            is_valid = await adapter.validate_connection()
            print(f"连接验证: {'✓' if is_valid else '❌'}")
            
            if not is_valid:
                print("连接失败，跳过其他测试")
                return
                
            # 测试获取模型列表
            print("\n获取模型列表...")
            models = await adapter.fetch_models(limit=3)
            print(f"获取到 {len(models)} 个模型:")
            
            for i, model in enumerate(models[:3]):
                print(f"  {i+1}. {model.name}")
                print(f"     作者: {model.author}")
                print(f"     描述: {model.description[:100]}...")
                print(f"     框架: {model.framework}")
                print(f"     领域: {model.domain}")
                print(f"     下载: {model.downloads}")
                print(f"     标签: {model.tags[:3]}")
                print()
                
            # 测试获取模型详情
            if models:
                print("获取模型详情...")
                model_id = models[0].source_id
                detail = await adapter.fetch_model_detail(model_id)
                
                if detail:
                    print(f"✓ 获取详情成功: {detail.basic_info.name}")
                    print(f"  README长度: {len(detail.readme) if detail.readme else 0}")
                    print(f"  文件数量: {len(detail.files)}")
                    print(f"  性能指标: {len(detail.performance_metrics)}")
                else:
                    print("❌ 获取详情失败")
                    
            # 测试获取总数（可能很慢，所以跳过）
            # print("\n获取总数...")
            # total = await adapter.get_total_count()
            # print(f"总模型数: {total}")
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        
    print("HuggingFace适配器测试完成")


async def test_rate_limiting():
    """测试速率限制功能"""
    print("\n测试速率限制...")
    
    config = SourceConfig(
        name="huggingface",
        api_url="https://huggingface.co/api",
        rate_limit=2,  # 很低的限制用于测试
        timeout=10
    )
    
    adapter = HuggingFaceAdapter(config)
    
    try:
        async with adapter:
            start_time = datetime.now()
            
            # 快速发起多个请求
            tasks = []
            for i in range(3):
                task = adapter.fetch_models(limit=1, offset=i)
                tasks.append(task)
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"3个请求耗时: {duration:.1f}秒")
            print(f"成功请求: {sum(1 for r in results if not isinstance(r, Exception))}")
            
            if duration > 5:  # 如果耗时超过5秒，说明速率限制生效
                print("✓ 速率限制正常工作")
            else:
                print("⚠️ 速率限制可能未生效（或API响应很快）")
                
    except Exception as e:
        print(f"❌ 速率限制测试失败: {e}")


async def test_data_parsing():
    """测试数据解析功能"""
    print("\n测试数据解析...")
    
    # 模拟HuggingFace API响应
    mock_data = {
        "id": "microsoft/DialoGPT-medium",
        "description": "A conversational AI model trained on Reddit conversations",
        "downloads": 150000,
        "likes": 250,
        "tags": ["pytorch", "text-generation", "conversational"],
        "pipeline_tag": "text-generation",
        "createdAt": "2020-05-01T10:00:00.000Z",
        "lastModified": "2023-08-15T14:30:00.000Z",
        "cardData": {
            "license": "mit"
        },
        "safetensors": {
            "total": 863000000  # ~863MB
        }
    }
    
    config = SourceConfig(name="huggingface", api_url="https://huggingface.co/api")
    adapter = HuggingFaceAdapter(config)
    
    try:
        model = adapter._parse_model_data(mock_data)
        
        print("解析结果:")
        print(f"  ID: {model.source_id}")
        print(f"  名称: {model.name}")
        print(f"  作者: {model.author}")
        print(f"  描述: {model.description}")
        print(f"  框架: {model.framework}")
        print(f"  领域: {model.domain}")
        print(f"  许可证: {model.license}")
        print(f"  大小: {model.size}")
        print(f"  下载数: {model.downloads}")
        print(f"  标签: {model.tags}")
        
        # 验证解析结果
        assert model.source_id == "microsoft/DialoGPT-medium"
        assert model.name == "DialoGPT-medium"
        assert model.author == "microsoft"
        assert model.framework == "pytorch"
        assert model.domain == "nlp"
        assert model.license == "mit"
        assert "823" in model.size or "863" in model.size  # 允许一些计算差异
        
        print("✓ 数据解析测试通过")
        
    except Exception as e:
        print(f"❌ 数据解析测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """运行所有测试"""
    print("开始测试HuggingFace适配器...\n")
    
    await test_data_parsing()
    await test_huggingface_adapter()
    await test_rate_limiting()
    
    print("\n所有测试完成! 🎉")


if __name__ == "__main__":
    asyncio.run(main())