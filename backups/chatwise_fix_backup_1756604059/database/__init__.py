"""
数据库模块
提供高性能的数据库访问和优化功能
"""

from .optimized_db import OptimizedSecurityEventDB, optimized_event_db, AsyncDatabasePool, DatabasePerformanceManager

__all__ = [
    'OptimizedSecurityEventDB',
    'optimized_event_db', 
    'AsyncDatabasePool',
    'DatabasePerformanceManager'
]