"""检测结果缓存管理器。"""

import hashlib
import time
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

from src.logger import logger
from src.models_interceptor import DetectionResult


@dataclass
class CacheEntry:
    """缓存条目。"""
    result: DetectionResult
    timestamp: float
    hit_count: int = 0
    
    def is_expired(self, ttl: float) -> bool:
        """检查是否过期。"""
        return time.time() - self.timestamp > ttl


class DetectionCache:
    """检测结果缓存管理器。"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        """初始化缓存管理器。

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认缓存TTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.hit_stats = {"hits": 0, "misses": 0, "evictions": 0}
        
    def _generate_key(self, text: str, detector_type: str, additional_context: str = "") -> str:
        """生成缓存键。

        Args:
            text: 检测文本
            detector_type: 检测器类型
            additional_context: 额外上下文

        Returns:
            缓存键
        """
        # 使用SHA256哈希来生成固定长度的键
        content = f"{detector_type}:{text}:{additional_context}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]

    def get(self, text: str, detector_type: str, additional_context: str = "") -> Optional[DetectionResult]:
        """从缓存获取检测结果。

        Args:
            text: 检测文本
            detector_type: 检测器类型  
            additional_context: 额外上下文

        Returns:
            缓存的检测结果，如果不存在或过期则返回None
        """
        key = self._generate_key(text, detector_type, additional_context)
        
        if key not in self.cache:
            self.hit_stats["misses"] += 1
            return None
            
        entry = self.cache[key]
        
        # 检查是否过期
        if entry.is_expired(self.default_ttl):
            del self.cache[key]
            self.hit_stats["misses"] += 1
            logger.debug(f"DetectionCache: 缓存条目过期并删除: {key}")
            return None
            
        # 更新命中统计
        entry.hit_count += 1
        self.hit_stats["hits"] += 1
        logger.debug(f"DetectionCache: 缓存命中: {key}, 命中次数: {entry.hit_count}")
        
        return entry.result

    def put(self, text: str, detector_type: str, result: DetectionResult, 
            additional_context: str = "", ttl: Optional[float] = None) -> None:
        """将检测结果放入缓存。

        Args:
            text: 检测文本
            detector_type: 检测器类型
            result: 检测结果
            additional_context: 额外上下文
            ttl: 自定义TTL
        """
        key = self._generate_key(text, detector_type, additional_context)
        
        # 检查缓存大小，如果超过限制则清理
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
            
        # 创建缓存条目
        entry = CacheEntry(
            result=result,
            timestamp=time.time()
        )
        
        self.cache[key] = entry
        logger.debug(f"DetectionCache: 添加缓存条目: {key}")

    def _evict_oldest(self) -> None:
        """清理最旧的缓存条目。"""
        if not self.cache:
            return
            
        # 按时间戳排序，删除最旧的条目
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
        del self.cache[oldest_key]
        self.hit_stats["evictions"] += 1
        logger.debug(f"DetectionCache: 清理最旧缓存条目: {oldest_key}")

    def clear(self) -> None:
        """清空缓存。"""
        cache_size = len(self.cache)
        self.cache.clear()
        logger.info(f"DetectionCache: 清空缓存，删除了 {cache_size} 个条目")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。

        Returns:
            缓存统计字典
        """
        total_requests = self.hit_stats["hits"] + self.hit_stats["misses"]
        hit_rate = self.hit_stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "hits": self.hit_stats["hits"],
            "misses": self.hit_stats["misses"],
            "evictions": self.hit_stats["evictions"],
            "total_requests": total_requests
        }

    def cleanup_expired(self) -> int:
        """清理过期的缓存条目。

        Returns:
            删除的条目数量
        """
        expired_keys = []
        current_time = time.time()
        
        for key, entry in self.cache.items():
            if current_time - entry.timestamp > self.default_ttl:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            logger.info(f"DetectionCache: 清理了 {len(expired_keys)} 个过期缓存条目")
            
        return len(expired_keys)


# 创建全局缓存实例
detection_cache = DetectionCache(max_size=2000, default_ttl=600.0)  # 10分钟TTL


class CacheableDetectorMixin:
    """可缓存检测器混入类。"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_enabled = True
        self.detector_name = self.__class__.__name__
        
    def detect_with_cache(self, text: str, additional_context: str = "") -> Optional[DetectionResult]:
        """使用缓存的检测方法。

        Args:
            text: 检测文本
            additional_context: 额外上下文

        Returns:
            检测结果
        """
        if not self.cache_enabled:
            return None
            
        # 尝试从缓存获取
        cached_result = detection_cache.get(text, self.detector_name, additional_context)
        if cached_result:
            logger.debug(f"{self.detector_name}: 使用缓存结果")
            return cached_result
            
        return None
    
    def cache_result(self, text: str, result: DetectionResult, additional_context: str = "") -> None:
        """缓存检测结果。

        Args:
            text: 检测文本
            result: 检测结果
            additional_context: 额外上下文
        """
        if not self.cache_enabled:
            return
            
        # 只缓存确定的结果（高置信度或明确的允许/拒绝）
        if (result.is_allowed or 
            (hasattr(result, 'confidence_score') and result.confidence_score >= 0.7)):
            detection_cache.put(text, self.detector_name, result, additional_context)
            logger.debug(f"{self.detector_name}: 缓存检测结果")


def get_cache_stats() -> Dict[str, Any]:
    """获取全局缓存统计信息。

    Returns:
        缓存统计字典
    """
    return detection_cache.get_stats()


def clear_detection_cache() -> None:
    """清空检测缓存。"""
    detection_cache.clear()


def cleanup_expired_cache() -> int:
    """清理过期缓存。

    Returns:
        删除的条目数量
    """
    return detection_cache.cleanup_expired()