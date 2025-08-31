"""
高性能数据库管理器
支持SQLite、批量操作、索引优化和连接池
"""

import asyncio
import aiosqlite
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import time
import threading
from enum import Enum

from src.logger import logger
from src.config import settings
from src.models_interceptor import DetectionResult, DetectionType, Severity


class QueryType(Enum):
    """查询类型枚举"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"


@dataclass
class QueryStats:
    """查询统计"""
    query_type: QueryType
    execution_time: float
    rows_affected: int
    timestamp: float


class DatabasePerformanceManager:
    """数据库性能管理器"""
    
    def __init__(self):
        self.query_stats: List[QueryStats] = []
        self.slow_query_threshold = 0.1  # 100ms
        self.stats_lock = threading.Lock()
    
    def record_query(self, query_type: QueryType, execution_time: float, rows_affected: int = 0):
        """记录查询统计"""
        with self.stats_lock:
            stat = QueryStats(
                query_type=query_type,
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=time.time()
            )
            self.query_stats.append(stat)
            
            # 记录慢查询
            if execution_time > self.slow_query_threshold:
                logger.warning(f"慢查询检测: {query_type.value} 耗时 {execution_time:.3f}s")
            
            # 保持统计数据不超过1000条
            if len(self.query_stats) > 1000:
                self.query_stats = self.query_stats[-1000:]
    
    def get_performance_stats(self, minutes: int = 10) -> Dict[str, Any]:
        """获取性能统计"""
        cutoff_time = time.time() - (minutes * 60)
        
        with self.stats_lock:
            recent_stats = [s for s in self.query_stats if s.timestamp >= cutoff_time]
        
        if not recent_stats:
            return {"message": "无统计数据"}
        
        # 按查询类型分组统计
        stats_by_type = {}
        for stat in recent_stats:
            query_type = stat.query_type.value
            if query_type not in stats_by_type:
                stats_by_type[query_type] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'max_time': 0,
                    'rows_affected': 0
                }
            
            stats_by_type[query_type]['count'] += 1
            stats_by_type[query_type]['total_time'] += stat.execution_time
            stats_by_type[query_type]['max_time'] = max(
                stats_by_type[query_type]['max_time'], 
                stat.execution_time
            )
            stats_by_type[query_type]['rows_affected'] += stat.rows_affected
        
        # 计算平均时间
        for query_type in stats_by_type:
            count = stats_by_type[query_type]['count']
            stats_by_type[query_type]['avg_time'] = (
                stats_by_type[query_type]['total_time'] / count
            )
        
        return {
            'time_range_minutes': minutes,
            'total_queries': len(recent_stats),
            'stats_by_type': stats_by_type,
            'slow_queries': len([s for s in recent_stats if s.execution_time > self.slow_query_threshold])
        }


class AsyncDatabasePool:
    """异步数据库连接池"""
    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = asyncio.Queue(maxsize=pool_size)
        self.active_connections = 0
        self.lock = asyncio.Lock()
        self.performance_manager = DatabasePerformanceManager()
    
    async def initialize(self):
        """初始化连接池"""
        # 预创建连接池
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            # 启用WAL模式以提高并发性能
            await conn.execute("PRAGMA journal_mode=WAL")
            # 启用外键约束
            await conn.execute("PRAGMA foreign_keys=ON")
            # 优化SQLite性能参数
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            await conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            await self.pool.put(conn)
        
        logger.info(f"数据库连接池初始化完成，池大小: {self.pool_size}")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        start_time = time.time()
        conn = await self.pool.get()
        
        try:
            async with self.lock:
                self.active_connections += 1
            
            yield conn
            
        finally:
            async with self.lock:
                self.active_connections -= 1
            
            await self.pool.put(conn)
            
            # 记录连接使用统计
            usage_time = time.time() - start_time
            if usage_time > 1.0:  # 连接使用超过1秒记录警告
                logger.warning(f"数据库连接使用时间过长: {usage_time:.3f}s")
    
    async def execute_query(self, query: str, params: Tuple = (), query_type: QueryType = QueryType.SELECT):
        """执行查询"""
        start_time = time.time()
        
        async with self.get_connection() as conn:
            try:
                if query_type == QueryType.SELECT:
                    cursor = await conn.execute(query, params)
                    result = await cursor.fetchall()
                    rows_affected = len(result)
                else:
                    cursor = await conn.execute(query, params)
                    await conn.commit()
                    rows_affected = cursor.rowcount
                    result = cursor.lastrowid if query_type == QueryType.INSERT else cursor.rowcount
                
                execution_time = time.time() - start_time
                self.performance_manager.record_query(query_type, execution_time, rows_affected)
                
                return result
                
            except Exception as e:
                logger.error(f"数据库查询失败: {query} - {e}")
                raise
    
    async def execute_batch(self, query: str, params_list: List[Tuple], query_type: QueryType = QueryType.INSERT):
        """批量执行查询"""
        start_time = time.time()
        
        async with self.get_connection() as conn:
            try:
                cursor = await conn.executemany(query, params_list)
                await conn.commit()
                
                execution_time = time.time() - start_time
                self.performance_manager.record_query(query_type, execution_time, len(params_list))
                
                return cursor.rowcount
                
            except Exception as e:
                logger.error(f"批量数据库操作失败: {query} - {e}")
                raise
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            'pool_size': self.pool_size,
            'active_connections': self.active_connections,
            'available_connections': self.pool.qsize(),
            'performance_stats': self.performance_manager.get_performance_stats()
        }
    
    async def close(self):
        """关闭连接池"""
        while not self.pool.empty():
            conn = await self.pool.get()
            await conn.close()
        
        logger.info("数据库连接池已关闭")


class OptimizedSecurityEventDB:
    """优化的安全事件数据库管理器"""
    
    def __init__(self, db_path: str = "data/security_events.db", pool_size: int = 10):
        self.db_path = db_path
        self.pool = AsyncDatabasePool(db_path, pool_size)
        self._batch_buffer: List[Dict[str, Any]] = []
        self._batch_lock = asyncio.Lock()
        self._batch_size = 100
        self._batch_timeout = 30.0  # 30秒
        self._last_batch_time = time.time()
    
    async def initialize(self):
        """初始化数据库"""
        await self.pool.initialize()
        await self._create_tables()
        await self._create_indexes()
        
        # 启动批处理任务
        asyncio.create_task(self._batch_processor())
        
        logger.info("优化的安全事件数据库初始化完成")
    
    async def _create_tables(self):
        """创建数据表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            timestamp REAL NOT NULL,
            detection_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            reason TEXT NOT NULL,
            details TEXT,
            content TEXT NOT NULL,
            rule_id TEXT,
            rule_name TEXT,
            matched_pattern TEXT,
            matched_text TEXT,
            matched_keyword TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            indexed_at DATETIME
        );
        """
        
        await self.pool.execute_query(create_table_sql, (), QueryType.CREATE)
        logger.info("安全事件表创建完成")
    
    async def _create_indexes(self):
        """创建索引以优化查询性能"""
        indexes = [
            # 时间戳索引 - 用于时间范围查询
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON security_events(timestamp);",
            
            # 检测类型索引 - 用于按类型过滤
            "CREATE INDEX IF NOT EXISTS idx_detection_type ON security_events(detection_type);",
            
            # 严重性索引 - 用于按严重性过滤
            "CREATE INDEX IF NOT EXISTS idx_severity ON security_events(severity);",
            
            # 规则ID索引 - 用于按规则查询
            "CREATE INDEX IF NOT EXISTS idx_rule_id ON security_events(rule_id);",
            
            # 复合索引 - 时间戳+检测类型，常用查询组合
            "CREATE INDEX IF NOT EXISTS idx_timestamp_type ON security_events(timestamp, detection_type);",
            
            # 复合索引 - 时间戳+严重性
            "CREATE INDEX IF NOT EXISTS idx_timestamp_severity ON security_events(timestamp, severity);",
            
            # 事件ID索引 - 用于快速查找特定事件
            "CREATE INDEX IF NOT EXISTS idx_event_id ON security_events(event_id);",
            
            # 创建时间索引 - 用于数据归档
            "CREATE INDEX IF NOT EXISTS idx_created_at ON security_events(created_at);"
        ]
        
        for index_sql in indexes:
            await self.pool.execute_query(index_sql, (), QueryType.CREATE)
        
        logger.info("数据库索引创建完成")
    
    async def log_event(self, result: DetectionResult, content: str):
        """记录安全事件（批量模式）"""
        if result.is_allowed:
            return
        
        event_data = {
            'event_id': f"event-{int(time.time() * 1000000)}-{id(result)}",
            'timestamp': time.time(),
            'detection_type': result.detection_type.value if hasattr(result.detection_type, 'value') else str(result.detection_type),
            'severity': result.severity.value if hasattr(result.severity, 'value') else str(result.severity),
            'reason': result.reason,
            'details': json.dumps(result.details) if result.details else None,
            'content': content[:1000],  # 限制内容长度
            'rule_id': result.details.get('rule_id') if result.details else None,
            'rule_name': result.details.get('rule_name') if result.details else None,
            'matched_pattern': result.details.get('matched_pattern') if result.details else None,
            'matched_text': result.details.get('matched_text') if result.details else None,
            'matched_keyword': result.details.get('matched_keyword') if result.details else None
        }
        
        async with self._batch_lock:
            self._batch_buffer.append(event_data)
            
            # 如果达到批量大小或超时，立即处理
            if (len(self._batch_buffer) >= self._batch_size or 
                time.time() - self._last_batch_time >= self._batch_timeout):
                await self._flush_batch()
    
    async def _flush_batch(self):
        """刷新批量缓存到数据库"""
        if not self._batch_buffer:
            return
        
        insert_sql = """
        INSERT INTO security_events (
            event_id, timestamp, detection_type, severity, reason, details, content,
            rule_id, rule_name, matched_pattern, matched_text, matched_keyword
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for event in self._batch_buffer:
            params_list.append((
                event['event_id'], event['timestamp'], event['detection_type'],
                event['severity'], event['reason'], event['details'], event['content'],
                event['rule_id'], event['rule_name'], event['matched_pattern'],
                event['matched_text'], event['matched_keyword']
            ))
        
        try:
            rows_inserted = await self.pool.execute_batch(insert_sql, params_list, QueryType.INSERT)
            logger.info(f"批量插入安全事件: {rows_inserted} 条记录")
            
            self._batch_buffer.clear()
            self._last_batch_time = time.time()
            
        except Exception as e:
            logger.error(f"批量插入安全事件失败: {e}")
            # 保持缓存，下次重试
    
    async def _batch_processor(self):
        """批处理后台任务"""
        while True:
            try:
                await asyncio.sleep(self._batch_timeout)
                
                async with self._batch_lock:
                    if self._batch_buffer:
                        await self._flush_batch()
                        
            except Exception as e:
                logger.error(f"批处理任务错误: {e}")
    
    async def get_events(self, 
                        limit: int = 100, 
                        offset: int = 0,
                        detection_type: Optional[str] = None,
                        severity: Optional[str] = None,
                        hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取安全事件列表（优化查询）"""
        
        # 构建查询条件
        conditions = []
        params = []
        
        if detection_type:
            conditions.append("detection_type = ?")
            params.append(detection_type)
        
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        
        if hours:
            cutoff_time = time.time() - (hours * 3600)
            conditions.append("timestamp >= ?")
            params.append(cutoff_time)
        
        # 构建SQL查询
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        SELECT * FROM security_events 
        WHERE {where_clause}
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        rows = await self.pool.execute_query(query, tuple(params), QueryType.SELECT)
        
        # 转换为字典格式
        columns = [
            'id', 'event_id', 'timestamp', 'detection_type', 'severity', 
            'reason', 'details', 'content', 'rule_id', 'rule_name',
            'matched_pattern', 'matched_text', 'matched_keyword', 
            'created_at', 'indexed_at'
        ]
        
        events = []
        for row in rows:
            event_dict = dict(zip(columns, row))
            # 解析JSON字段
            if event_dict['details']:
                try:
                    event_dict['details'] = json.loads(event_dict['details'])
                except:
                    pass
            events.append(event_dict)
        
        return events
    
    async def get_event_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取事件统计信息（优化查询）"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        # 按检测类型统计
        type_stats_query = """
        SELECT detection_type, COUNT(*) as count 
        FROM security_events 
        WHERE timestamp >= ?
        GROUP BY detection_type
        ORDER BY count DESC
        """
        
        # 按严重性统计
        severity_stats_query = """
        SELECT severity, COUNT(*) as count 
        FROM security_events 
        WHERE timestamp >= ?
        GROUP BY severity
        ORDER BY count DESC
        """
        
        # 每日统计
        daily_stats_query = """
        SELECT DATE(datetime(timestamp, 'unixepoch')) as date, COUNT(*) as count
        FROM security_events 
        WHERE timestamp >= ?
        GROUP BY DATE(datetime(timestamp, 'unixepoch'))
        ORDER BY date DESC
        """
        
        type_stats = await self.pool.execute_query(type_stats_query, (cutoff_time,), QueryType.SELECT)
        severity_stats = await self.pool.execute_query(severity_stats_query, (cutoff_time,), QueryType.SELECT)
        daily_stats = await self.pool.execute_query(daily_stats_query, (cutoff_time,), QueryType.SELECT)
        
        return {
            'time_range_days': days,
            'detection_type_stats': [{'type': row[0], 'count': row[1]} for row in type_stats],
            'severity_stats': [{'severity': row[0], 'count': row[1]} for row in severity_stats],
            'daily_stats': [{'date': row[0], 'count': row[1]} for row in daily_stats],
            'total_events': sum(row[1] for row in type_stats)
        }
    
    async def cleanup_old_events(self, days: int = 30):
        """清理旧事件数据"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        delete_query = "DELETE FROM security_events WHERE timestamp < ?"
        deleted_rows = await self.pool.execute_query(delete_query, (cutoff_time,), QueryType.DELETE)
        
        # 执行VACUUM以回收空间
        await self.pool.execute_query("VACUUM", (), QueryType.DELETE)
        
        logger.info(f"清理了 {deleted_rows} 条超过 {days} 天的事件记录")
        return deleted_rows
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        pool_stats = self.pool.get_pool_stats()
        
        return {
            'pool_stats': pool_stats,
            'batch_buffer_size': len(self._batch_buffer),
            'batch_size_limit': self._batch_size,
            'batch_timeout': self._batch_timeout
        }
    
    async def close(self):
        """关闭数据库连接"""
        # 刷新剩余的批量数据
        async with self._batch_lock:
            if self._batch_buffer:
                await self._flush_batch()
        
        await self.pool.close()


# 全局数据库实例
optimized_event_db = OptimizedSecurityEventDB()