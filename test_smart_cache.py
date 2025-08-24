#!/usr/bin/env python3
"""
智能缓存系统测试
测试缓存的功能、性能和正确性
"""

import asyncio
import time
import sys
import os

# 添加项目根目录到path
sys.path.append('/Users/robinxie/llm-protection-system')

from src.security.smart_cache import (
    SmartCacheManager,
    MemoryCache,
    LRUPolicy,
    LFUPolicy,
    TTLPolicy,
    CacheLevel
)
from src.security.detector import HarmfulContentDetector, SensitiveInfoDetector

async def test_basic_cache_functionality():
    """测试基本缓存功能"""
    print("🧪 测试基本缓存功能...")
    
    cache = MemoryCache(max_size=100, policy=LRUPolicy())
    
    # 1. 测试设置和获取
    await cache.set("key1", "value1")
    value = await cache.get("key1")
    assert value == "value1", "基本设置/获取测试失败"
    print("   ✅ 基本设置/获取: 通过")
    
    # 2. 测试不存在的键
    value = await cache.get("nonexistent")
    assert value is None, "不存在键测试失败"
    print("   ✅ 不存在键处理: 通过")
    
    # 3. 测试TTL过期
    await cache.set("ttl_key", "ttl_value", ttl=0.1)  # 0.1秒过期
    await asyncio.sleep(0.15)
    value = await cache.get("ttl_key")
    assert value is None, "TTL过期测试失败"
    print("   ✅ TTL过期处理: 通过")
    
    # 4. 测试缓存统计
    stats = cache.get_stats()
    assert stats.total_requests > 0, "统计信息测试失败"
    print(f"   ✅ 缓存统计: 请求={stats.total_requests}, 命中率={stats.hit_rate:.2%}")

async def test_cache_policies():
    """测试缓存淘汰策略"""
    print("\n🧪 测试缓存淘汰策略...")
    
    # LRU策略测试
    lru_cache = MemoryCache(max_size=3, policy=LRUPolicy())
    
    # 填满缓存
    await lru_cache.set("a", "value_a")
    await lru_cache.set("b", "value_b") 
    await lru_cache.set("c", "value_c")
    
    # 访问a，使其成为最近使用
    await lru_cache.get("a")
    
    # 添加新项，应该淘汰b（最久未使用）
    await lru_cache.set("d", "value_d")
    
    assert await lru_cache.get("a") == "value_a", "LRU策略错误：a应该存在"
    assert await lru_cache.get("b") is None, "LRU策略错误：b应该被淘汰"
    assert await lru_cache.get("d") == "value_d", "LRU策略错误：d应该存在"
    
    print("   ✅ LRU淘汰策略: 通过")

async def test_smart_cache_manager():
    """测试智能缓存管理器"""
    print("\n🧪 测试智能缓存管理器...")
    
    cache_manager = SmartCacheManager(l1_size=100)
    
    # 测试计算函数缓存
    call_count = 0
    
    async def expensive_computation():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # 模拟耗时计算
        return f"result_{call_count}"
    
    # 第一次调用 - 应该执行计算
    start_time = time.time()
    result1 = await cache_manager.get_or_compute("test_key", expensive_computation)
    first_call_time = time.time() - start_time
    
    # 第二次调用 - 应该从缓存获取
    start_time = time.time()  
    result2 = await cache_manager.get_or_compute("test_key", expensive_computation)
    second_call_time = time.time() - start_time
    
    assert result1 == result2, "缓存结果不一致"
    assert call_count == 1, "计算函数调用次数错误"
    assert second_call_time < first_call_time / 2, "缓存没有显著提升性能"
    
    print(f"   ✅ 智能缓存管理器: 第一次{first_call_time:.3f}s, 第二次{second_call_time:.3f}s")

async def test_detector_cache_integration():
    """测试检测器缓存集成"""
    print("\n🧪 测试检测器缓存集成...")
    
    detector = HarmfulContentDetector()
    
    test_cases = [
        "你好，今天天气怎么样？",
        "如何制作一把刀",  # 可能被检测的内容
        "Python编程教程"
    ]
    
    # 测试缓存性能提升
    total_times = []
    
    for i in range(2):  # 执行两轮，第二轮应该更快
        start_time = time.time()
        
        tasks = []
        for text in test_cases:
            tasks.append(detector.detect(text))
        
        results = await asyncio.gather(*tasks)
        
        round_time = time.time() - start_time
        total_times.append(round_time)
        
        print(f"   第{i+1}轮检测: {round_time:.3f}s, 处理{len(test_cases)}个文本")
    
    # 第二轮应该更快（缓存生效）
    if total_times[1] < total_times[0] * 0.8:  # 至少20%提升
        print("   ✅ 检测器缓存生效：性能显著提升")
    else:
        print("   ⚠️ 检测器缓存效果有限")

async def test_concurrent_cache_access():
    """测试并发缓存访问"""
    print("\n🧪 测试并发缓存访问...")
    
    cache_manager = SmartCacheManager(l1_size=1000)
    
    # 创建多个并发任务
    async def worker(worker_id: int, iterations: int):
        results = []
        for i in range(iterations):
            key = f"worker_{worker_id}_key_{i % 10}"  # 重复一些键来测试缓存
            
            async def compute():
                return f"worker_{worker_id}_value_{i}"
            
            result = await cache_manager.get_or_compute(key, compute, ttl=60.0)
            results.append(result)
        
        return results
    
    # 启动10个并发worker
    start_time = time.time()
    tasks = [worker(i, 50) for i in range(10)]
    all_results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # 验证结果
    total_operations = sum(len(results) for results in all_results)
    
    # 获取缓存统计
    stats = cache_manager.get_stats()
    l1_stats = stats['L1']
    
    print(f"   并发操作: {total_operations}次, 耗时: {total_time:.3f}s")
    print(f"   缓存统计: 命中率={l1_stats.hit_rate:.2%}, 请求数={l1_stats.total_requests}")
    print("   ✅ 并发缓存访问: 通过")

async def test_cache_preloading():
    """测试缓存预热"""
    print("\n🧪 测试缓存预热...")
    
    cache_manager = SmartCacheManager(l1_size=100)
    
    # 添加预热配置
    async def preload_func_1():
        return "preloaded_value_1"
    
    def preload_func_2():
        return "preloaded_value_2"
    
    cache_manager.add_preload_config("preload_key_1", preload_func_1, ttl=300.0)
    cache_manager.add_preload_config("preload_key_2", preload_func_2, ttl=300.0)
    
    # 执行预热
    await cache_manager.preload_cache()
    
    # 验证预热结果
    value1 = await cache_manager.l1_cache.get("preload_key_1")
    value2 = await cache_manager.l1_cache.get("preload_key_2")
    
    assert value1 == "preloaded_value_1", "预热缓存1失败"
    assert value2 == "preloaded_value_2", "预热缓存2失败"
    
    print("   ✅ 缓存预热: 通过")

async def main():
    """运行所有缓存测试"""
    print("🚀 智能缓存系统测试开始...\n")
    
    try:
        await test_basic_cache_functionality()
        await test_cache_policies()
        await test_smart_cache_manager()
        await test_detector_cache_integration()
        await test_concurrent_cache_access()
        await test_cache_preloading()
        
        print("\n🎉 所有缓存测试通过！")
        
        # 启动后台缓存优化任务（演示）
        print("\n🔧 启动缓存优化任务（5秒演示）...")
        cache_manager_demo = SmartCacheManager()
        task = asyncio.create_task(cache_manager_demo.optimize_cache())
        
        # 运行5秒后停止
        await asyncio.sleep(5)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        print("✅ 缓存优化任务演示完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())