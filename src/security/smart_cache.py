"""
智能缓存系统
支持多层缓存架构、智能失效策略和缓存预热
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

from src.logger import logger
from src.utils.redis_client import redis_client


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "L1_MEMORY"      # 内存缓存 - 最快
    L2_REDIS = "L2_REDIS"        # Redis缓存 - 中等速度
    L3_DISK = "L3_DISK"          # 磁盘缓存 - 最慢但容量大


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """缓存未命中率"""
        return 1.0 - self.hit_rate


@dataclass
class CacheItem:
    """缓存项"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[float] = None  # TTL (Time To Live) in seconds
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间和次数"""
        self.accessed_at = time.time()
        self.access_count += 1


class CachePolicy(ABC):
    """缓存淘汰策略抽象基类"""
    
    @abstractmethod
    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        """判断是否应该淘汰此项"""
        pass
    
    @abstractmethod
    def get_eviction_candidates(self, cache: Dict[str, CacheItem], count: int) -> List[str]:
        """获取需要淘汰的候选项"""
        pass


class LRUPolicy(CachePolicy):
    """LRU (Least Recently Used) 淘汰策略"""
    
    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return cache_size >= max_size
    
    def get_eviction_candidates(self, cache: Dict[str, CacheItem], count: int) -> List[str]:
        # 按照访问时间排序，最久未访问的排在前面
        sorted_items = sorted(cache.items(), key=lambda x: x[1].accessed_at)
        return [key for key, _ in sorted_items[:count]]


class LFUPolicy(CachePolicy):
    """LFU (Least Frequently Used) 淘汰策略"""
    
    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return cache_size >= max_size
    
    def get_eviction_candidates(self, cache: Dict[str, CacheItem], count: int) -> List[str]:
        # 按照访问次数排序，访问次数最少的排在前面
        sorted_items = sorted(cache.items(), key=lambda x: (x[1].access_count, x[1].accessed_at))
        return [key for key, _ in sorted_items[:count]]


class TTLPolicy(CachePolicy):
    """TTL (Time To Live) 淘汰策略"""
    
    def should_evict(self, item: CacheItem, cache_size: int, max_size: int) -> bool:
        return item.is_expired()
    
    def get_eviction_candidates(self, cache: Dict[str, CacheItem], count: int) -> List[str]:
        # 获取所有过期的项
        expired_keys = [key for key, item in cache.items() if item.is_expired()]
        return expired_keys[:count]


class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 10000, policy: CachePolicy = None):
        self.max_size = max_size
        self.policy = policy or LRUPolicy()
        self._cache: Dict[str, CacheItem] = {}
        self._lock = asyncio.Lock()
        self.stats = CacheStats()
    
    def _generate_key(self, key: Union[str, Dict, Any]) -> str:
        """生成缓存键"""
        if isinstance(key, str):
            return key
        elif isinstance(key, dict):
            # 对字典进行排序后生成hash
            sorted_key = json.dumps(key, sort_keys=True)
            return hashlib.md5(sorted_key.encode()).hexdigest()
        else:
            # 对其他对象生成hash
            return hashlib.md5(str(key).encode()).hexdigest()
    
    async def get(self, key: Union[str, Dict, Any]) -> Optional[Any]:
        """获取缓存值"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            self.stats.total_requests += 1
            
            if cache_key in self._cache:
                item = self._cache[cache_key]
                
                # 检查是否过期
                if item.is_expired():
                    del self._cache[cache_key]
                    self.stats.misses += 1
                    self.stats.evictions += 1
                    logger.debug(f"MemoryCache: 缓存项已过期并移除: {cache_key}")
                    return None
                
                # 更新访问信息
                item.touch()
                self.stats.hits += 1
                logger.debug(f"MemoryCache: 缓存命中: {cache_key}")
                return item.value
            
            self.stats.misses += 1
            logger.debug(f"MemoryCache: 缓存未命中: {cache_key}")
            return None
    
    async def set(self, key: Union[str, Dict, Any], value: Any, ttl: Optional[float] = None):
        """设置缓存值"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            current_time = time.time()
            
            # 检查是否需要淘汰
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                await self._evict()
            
            # 创建缓存项
            item = CacheItem(
                key=cache_key,
                value=value,
                created_at=current_time,
                accessed_at=current_time,
                access_count=1,
                ttl=ttl
            )
            
            self._cache[cache_key] = item
            logger.debug(f"MemoryCache: 设置缓存: {cache_key} (TTL: {ttl})")
    
    async def delete(self, key: Union[str, Dict, Any]):
        """删除缓存项"""
        cache_key = self._generate_key(key)
        
        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"MemoryCache: 删除缓存: {cache_key}")
    
    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            logger.info("MemoryCache: 缓存已清空")
    
    async def _evict(self):
        """执行缓存淘汰"""
        # 首先淘汰过期项
        ttl_policy = TTLPolicy()
        expired_keys = ttl_policy.get_eviction_candidates(self._cache, len(self._cache))
        
        for key in expired_keys:
            del self._cache[key]
            self.stats.evictions += 1
        
        # 如果还需要淘汰，使用配置的策略
        if len(self._cache) >= self.max_size:
            evict_count = max(1, len(self._cache) // 10)  # 淘汰10%
            candidates = self.policy.get_eviction_candidates(self._cache, evict_count)
            
            for key in candidates:
                if key in self._cache:
                    del self._cache[key]
                    self.stats.evictions += 1
        
        logger.info(f"MemoryCache: 执行缓存淘汰，当前大小: {len(self._cache)}")
    
    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        return self.stats
    
    def get_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class SmartCacheManager:
    """智能缓存管理器 - 支持多层缓存架构"""
    
    def __init__(self, 
                 l1_size: int = 10000,
                 l2_enabled: bool = False,
                 l3_enabled: bool = False):
        # L1缓存 - 内存缓存
        self.l1_cache = MemoryCache(max_size=l1_size, policy=LRUPolicy())
        
        # L2缓存 - Redis缓存 (可选)
        self.l2_cache = None
        self.l2_enabled = l2_enabled
        
        # L3缓存 - 磁盘缓存 (可选)
        self.l3_cache = None
        self.l3_enabled = l3_enabled
        
        # 缓存预热配置
        self.preload_configs: List[Dict] = []
        
        logger.info(f"SmartCacheManager 初始化: L1({l1_size}), L2({l2_enabled}), L3({l3_enabled})")
    
    async def get_or_compute(self, 
                           key: Union[str, Dict, Any], 
                           compute_func: Callable[[], Any],
                           ttl: Optional[float] = None,
                           cache_level: CacheLevel = CacheLevel.L1_MEMORY) -> Any:
        """获取缓存值或计算新值"""
        
        # 1. 尝试从L1缓存获取
        result = await self.l1_cache.get(key)
        if result is not None:
            logger.debug(f"SmartCache: L1缓存命中: {key}")
            return result
        
        # 2. 尝试从L2缓存获取 (如果启用)
        if self.l2_enabled and self.l2_cache:
            result = await self._get_from_l2(key)
            if result is not None:
                # 将结果存入L1缓存
                await self.l1_cache.set(key, result, ttl)
                logger.debug(f"SmartCache: L2缓存命中，已存入L1: {key}")
                return result
        
        # 3. 尝试从L3缓存获取 (如果启用)
        if self.l3_enabled and self.l3_cache:
            result = await self._get_from_l3(key)
            if result is not None:
                # 将结果存入上级缓存
                await self.l1_cache.set(key, result, ttl)
                if self.l2_enabled:
                    await self._set_to_l2(key, result, ttl)
                logger.debug(f"SmartCache: L3缓存命中，已存入上级缓存: {key}")
                return result
        
        # 4. 执行计算函数
        logger.debug(f"SmartCache: 缓存全部未命中，执行计算: {key}")
        if asyncio.iscoroutinefunction(compute_func):
            result = await compute_func()
        else:
            result = compute_func()
        
        # 5. 将结果存入缓存
        await self._cache_result(key, result, ttl, cache_level)
        
        return result
    
    async def _cache_result(self, key: Union[str, Dict, Any], result: Any, ttl: Optional[float], level: CacheLevel):
        """将结果存入指定级别的缓存"""
        
        # 总是存入L1缓存
        await self.l1_cache.set(key, result, ttl)
        
        # 根据配置存入其他级别
        if level in [CacheLevel.L2_REDIS, CacheLevel.L3_DISK] and self.l2_enabled:
            await self._set_to_l2(key, result, ttl)
        
        if level == CacheLevel.L3_DISK and self.l3_enabled:
            await self._set_to_l3(key, result, ttl)
    
    async def _get_from_l2(self, key: Union[str, Dict, Any]) -> Optional[Any]:
        """从L2缓存获取 (Redis)"""
        if not getattr(redis_client, "_is_connected", False):
            return None
            
        cache_key = self.l1_cache._generate_key(key)
        redis_key = f"cache:l2:{cache_key}"
        try:
            return await redis_client.get_json(redis_key)
        except Exception as e:
            logger.error(f"L2缓存获取失败: {e}")
            return None
    
    async def _set_to_l2(self, key: Union[str, Dict, Any], value: Any, ttl: Optional[float]):
        """存入L2缓存 (Redis)"""
        if not getattr(redis_client, "_is_connected", False):
            return
            
        cache_key = self.l1_cache._generate_key(key)
        redis_key = f"cache:l2:{cache_key}"
        try:
            ex = int(ttl) if ttl else None
            await redis_client.set_json(redis_key, value, ex=ex)
        except Exception as e:
            logger.error(f"L2缓存写入失败: {e}")
    
    async def _get_from_l3(self, key: Union[str, Dict, Any]) -> Optional[Any]:
        """从L3缓存获取 (磁盘)"""
        # TODO: 实现磁盘缓存逻辑
        return None
    
    async def _set_to_l3(self, key: Union[str, Dict, Any], value: Any, ttl: Optional[float]):
        """存入L3缓存 (磁盘)"""
        # TODO: 实现磁盘缓存逻辑
        pass
    
    async def invalidate(self, key: Union[str, Dict, Any]):
        """使缓存失效"""
        await self.l1_cache.delete(key)
        if self.l2_enabled and getattr(redis_client, "_is_connected", False):
            cache_key = self.l1_cache._generate_key(key)
            redis_key = f"cache:l2:{cache_key}"
            await redis_client.delete(redis_key)
        # TODO: 也从L3缓存中删除
        logger.debug(f"SmartCache: 使缓存失效: {key}")
    
    async def clear_all(self):
        """清空所有缓存"""
        await self.l1_cache.clear()
        
        if self.l2_enabled and getattr(redis_client, "_is_connected", False):
            try:
                cursor = "0"
                while cursor != 0:
                    cursor, keys = await redis_client.client.scan(cursor=cursor, match="cache:l2:*", count=100)
                    if keys:
                        await redis_client.client.delete(*keys)
            except Exception as e:
                logger.error(f"L2缓存清空失败: {e}")
                
        # TODO: 也清空L3缓存
        logger.info("SmartCache: 已清空所有缓存")
    
    async def preload_cache(self):
        """缓存预热"""
        logger.info("SmartCache: 开始缓存预热...")
        
        for config in self.preload_configs:
            try:
                key = config['key']
                compute_func = config['compute_func']
                ttl = config.get('ttl')
                
                # 执行预热
                await self.get_or_compute(key, compute_func, ttl)
                logger.debug(f"SmartCache: 预热缓存项: {key}")
                
            except Exception as e:
                logger.error(f"SmartCache: 预热缓存失败: {config.get('key', 'unknown')} - {e}")
        
        logger.info("SmartCache: 缓存预热完成")
    
    def add_preload_config(self, key: Union[str, Dict, Any], compute_func: Callable, ttl: Optional[float] = None):
        """添加预热配置"""
        self.preload_configs.append({
            'key': key,
            'compute_func': compute_func,
            'ttl': ttl
        })
    
    def get_stats(self) -> Dict[str, CacheStats]:
        """获取所有缓存层的统计信息"""
        stats = {
            'L1': self.l1_cache.get_stats()
        }
        
        # TODO: 添加L2、L3统计信息
        
        return stats
    
    async def optimize_cache(self):
        """缓存优化 - 后台任务"""
        while True:
            try:
                # 定期清理过期项
                await asyncio.sleep(300)  # 5分钟执行一次
                
                # 执行L1缓存清理
                await self._cleanup_expired()
                
                # 记录统计信息
                stats = self.get_stats()
                l1_stats = stats['L1']
                logger.info(f"SmartCache统计: 命中率={l1_stats.hit_rate:.2%}, "
                          f"请求数={l1_stats.total_requests}, "
                          f"缓存大小={self.l1_cache.get_size()}")
                
            except Exception as e:
                logger.error(f"SmartCache: 缓存优化任务错误: {e}")
    
    async def _cleanup_expired(self):
        """清理过期缓存项"""
        # L1缓存会在访问时自动清理过期项
        # 这里可以主动执行清理
        pass


# 全局缓存管理器实例
cache_manager = SmartCacheManager(
    l1_size=10000,
    l2_enabled=True,  # 启用Redis缓存 (断开时自动降级)
    l3_enabled=False   # 暂时禁用磁盘缓存
)