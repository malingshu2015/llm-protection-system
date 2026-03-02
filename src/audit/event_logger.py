"""安全事件记录器。"""

import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionResult, DetectionType, Severity

# 导入优化的数据库管理器
try:
    from src.database.optimized_db import optimized_event_db
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("优化数据库不可用，将使用文件存储模式")


# 日志脱敏工具
class ContentSanitizer:
    """内容脱敏工具类。"""
    
    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        # 信用卡号 - 16位数字，可以包含空格或连字符
        (r'\b(?:\d{4}[\s-]?){3}\d{4}\b', '[CREDIT_CARD]'),
        # 邮箱地址
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        # 电话号码 - 支持多种格式
        (r'\b(?:\d{3}-?\d{3}-?\d{4}|\d{11}|\d{3}\s\d{3}\s\d{4})\b', '[PHONE]'),
        # API密钥 - 以sk-开头的长字符串
        (r'\b(?:sk-|api-|key-)?[a-zA-Z0-9]{32,}\b', '[API_KEY]'),
        # 身份证号 - 18位，最后一位可以是X
        (r'\b\d{17}[\dXx]\b', '[ID_CARD]'),
        # 密码
        (r'(?i)(?:password|passwd|pwd)\s*[:=]\s*\S+', '[PASSWORD]'),
        # 银行账号
        (r'\b\d{16,19}\b', '[BANK_ACCOUNT]'),
    ]
    
    @classmethod
    def sanitize_content(cls, content: str, max_length: int = 500) -> str:
        """
        脱敏敏感信息。
        
        Args:
            content: 原始内容
            max_length: 最大长度限制
            
        Returns:
            脱敏后的内容
        """
        if not content:
            return content
            
        sanitized = content
        
        # 应用脱敏模式
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        # 限制长度
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
            
        return sanitized


class SecurityEvent:
    """安全事件模型。"""

    def __init__(
        self,
        event_id: str,
        timestamp: float,
        detection_type: DetectionType,
        severity: Severity,
        reason: str,
        details: Dict,
        content: str,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        matched_pattern: Optional[str] = None,
        matched_text: Optional[str] = None,
        matched_keyword: Optional[str] = None,
    ):
        """初始化安全事件。

        Args:
            event_id: 事件ID
            timestamp: 时间戳
            detection_type: 检测类型
            severity: 严重程度
            reason: 原因
            details: 详细信息
            content: 触发事件的内容
            rule_id: 规则ID
            rule_name: 规则名称
            matched_pattern: 匹配的模式
            matched_text: 匹配的文本
            matched_keyword: 匹配的关键词
        """
        self.event_id = event_id
        self.timestamp = timestamp
        self.detection_type = detection_type
        self.severity = severity
        self.reason = reason
        self.details = details
        self.content = content
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.matched_pattern = matched_pattern
        self.matched_text = matched_text
        self.matched_keyword = matched_keyword

    def to_dict(self) -> Dict:
        """转换为字典。

        Returns:
            字典表示
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "detection_type": self.detection_type.value if self.detection_type else None,
            "severity": self.severity.value if self.severity else None,
            "reason": self.reason,
            "details": self.details,
            "content": self.content,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "matched_pattern": self.matched_pattern,
            "matched_text": self.matched_text,
            "matched_keyword": self.matched_keyword,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SecurityEvent":
        """从字典创建安全事件。

        Args:
            data: 字典数据

        Returns:
            安全事件
        """
        detection_type = None
        if data.get("detection_type"):
            try:
                detection_type = DetectionType(data["detection_type"])
            except ValueError:
                detection_type = None

        severity = None
        if data.get("severity"):
            try:
                severity = Severity(data["severity"])
            except ValueError:
                severity = None

        return cls(
            event_id=data.get("event_id", ""),
            timestamp=data.get("timestamp", 0.0),
            detection_type=detection_type,
            severity=severity,
            reason=data.get("reason", ""),
            details=data.get("details", {}),
            content=data.get("content", ""),
            rule_id=data.get("rule_id"),
            rule_name=data.get("rule_name"),
            matched_pattern=data.get("matched_pattern"),
            matched_text=data.get("matched_text"),
            matched_keyword=data.get("matched_keyword"),
        )


class SecurityEventLogger:
    """安全事件记录器。"""

    def __init__(self):
        """初始化安全事件记录器。"""
        self.events_dir = os.path.join(settings.data_dir, "security_events")
        self.events_file = os.path.join(self.events_dir, "events.json")
        self.events: List[SecurityEvent] = []
        self.use_optimized_db = DATABASE_AVAILABLE
        self.db = optimized_event_db if DATABASE_AVAILABLE else None
        self._load_events()

    def _load_events(self) -> None:
        """加载安全事件。"""
        try:
            # 确保目录存在
            os.makedirs(self.events_dir, exist_ok=True)

            # 如果文件不存在，创建空文件
            if not os.path.exists(self.events_file):
                with open(self.events_file, "w") as f:
                    json.dump([], f)
                return

            # 加载事件
            with open(self.events_file, "r") as f:
                events_data = json.load(f)

            self.events = [SecurityEvent.from_dict(event) for event in events_data]
            logger.info(f"已加载 {len(self.events)} 个安全事件")
        except Exception as e:
            logger.error(f"加载安全事件失败: {e}")
            self.events = []

    def _save_events(self) -> None:
        """保存安全事件。"""
        try:
            # 确保目录存在
            os.makedirs(self.events_dir, exist_ok=True)

            # 保存事件
            with open(self.events_file, "w") as f:
                json.dump([event.to_dict() for event in self.events], f, indent=2)
        except Exception as e:
            logger.error(f"保存安全事件失败: {e}")

    def log_event(self, result: DetectionResult, content: str) -> None:
        """记录安全事件。

        Args:
            result: 检测结果
            content: 触发事件的内容
        """
        if result.is_allowed:
            return

        # 脱敏敏感信息
        sanitized_content = ContentSanitizer.sanitize_content(content)

        # 尝试使用优化数据库
        if DATABASE_AVAILABLE:
            try:
                # 使用异步数据库（在后台任务中处理）
                import asyncio
                loop = asyncio.get_event_loop()
                
                # M3.1: Elasticsearch Dual-write
                from src.audit.elasticsearch_adapter import es_adapter
                event_id = f"event-{int(time.time() * 1000000)}-{id(result)}"
                
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务双写 (SQLite Optimization DB + ES)
                    loop.create_task(optimized_event_db.log_event(result, sanitized_content))
                    if getattr(es_adapter, "is_connected", False):
                        loop.create_task(es_adapter.log_event(result, sanitized_content, event_id))
                else:
                    # 如果没有事件循环，使用文件存储作为备份
                    self._log_event_to_file(result, sanitized_content)
                return
            except Exception as e:
                logger.warning(f"数据库记录失败，使用文件存储: {e}")
        
        # 回退到文件存储
        self._log_event_to_file(result, sanitized_content)
    
    def _log_event_to_file(self, result: DetectionResult, content: str) -> None:
        """记录安全事件到文件（备用方法）"""
        # 生成事件ID
        event_id = f"event-{int(time.time())}-{len(self.events) + 1}"

        # 提取规则信息
        rule_id = None
        rule_name = None
        matched_pattern = None
        matched_text = None
        matched_keyword = None

        if result.details:
            rule_id = result.details.get("rule_id")
            rule_name = result.details.get("rule_name")
            matched_pattern = result.details.get("matched_pattern")
            matched_text = result.details.get("matched_text")
            matched_keyword = result.details.get("matched_keyword")

        # 创建安全事件
        event = SecurityEvent(
            event_id=event_id,
            timestamp=time.time(),
            detection_type=result.detection_type,
            severity=result.severity,
            reason=result.reason,
            details=result.details,
            content=content,
            rule_id=rule_id,
            rule_name=rule_name,
            matched_pattern=matched_pattern,
            matched_text=matched_text,
            matched_keyword=matched_keyword,
        )

        # 添加到事件列表
        self.events.append(event)

        # 保存事件
        self._save_events()

        logger.info(f"已记录安全事件: {event_id}, 类型: {result.detection_type}, 原因: {result.reason}")


    async def get_events_async(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        detection_type: Optional[DetectionType] = None,
        severity: Optional[Severity] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SecurityEvent]:
        # 如果使用优化数据库，从数据库获取
        if self.use_optimized_db and self.db:
            try:
                db_events = await self.db.get_events_by_time_range(
                    start_time=start_time,
                    end_time=end_time,
                    detection_type=detection_type.value if detection_type else None,
                    severity=severity.value if severity else None,
                    limit=limit,
                    offset=offset
                )
                
                # Convert list of dict back to SecurityEvent
                # FIXME: from_dict 是 SecurityEvent 的 classmethod，不能通过 self 调用
                return [SecurityEvent.from_dict(d) for d in db_events]
            except Exception as e:
                logger.error(f"Failed to query optimized DB: {e}", exc_info=True)
                
        # Fallback to sync memory
        return self.get_events(start_time, end_time, detection_type, severity, limit, offset)

    async def get_events_count_async(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        detection_type: Optional[DetectionType] = None,
        severity: Optional[Severity] = None,
    ) -> int:
        if self.use_optimized_db and self.db:
            try:
                return await self.db.get_events_count_by_time_range(
                    start_time=start_time,
                    end_time=end_time,
                    detection_type=detection_type.value if detection_type else None,
                    severity=severity.value if severity else None
                )
            except Exception as e:
                logger.error(f"Failed to query count from optimized DB: {e}")
                
        return self.get_events_count(start_time, end_time, detection_type, severity)

    async def get_events_stats_async(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, int]:
        if self.use_optimized_db and self.db:
            try:
                return await self.db.get_events_stats_by_time_range(
                    start_time=start_time,
                    end_time=end_time
                )
            except Exception as e:
                logger.error(f"Failed to query stats from optimized DB: {e}")
                
        return self.get_events_stats(start_time, end_time)

    async def get_event_async(self, event_id: str) -> Optional[SecurityEvent]:
        # For singular event from DB
        if self.use_optimized_db and self.db:
            try:
                query = "SELECT * FROM security_events WHERE event_id = ?"
                rows = await self.db.pool.execute_query(query, (event_id,), QueryType.SELECT)
                if rows:
                    columns = [
                        'id', 'event_id', 'timestamp', 'detection_type', 'severity', 
                        'reason', 'details', 'content', 'rule_id', 'rule_name',
                        'matched_pattern', 'matched_text', 'matched_keyword', 
                        'created_at', 'indexed_at'
                    ]
                    event_dict = dict(zip(columns, rows[0]))
                    import json
                    if event_dict['details']:
                        try:
                            event_dict['details'] = json.loads(event_dict['details'])
                        except:
                            pass
                    return self.from_dict(event_dict)
            except Exception as e:
                logger.error(f"Failed to get event from optimized DB: {e}")
        return self.get_event(event_id)

    def get_events(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        detection_type: Optional[DetectionType] = None,
        severity: Optional[Severity] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SecurityEvent]:
        """获取安全事件。

        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳
            detection_type: 检测类型
            severity: 严重程度
            limit: 限制数量
            offset: 偏移量

        Returns:
            安全事件列表
        """
        # 过滤事件
        filtered_events = self.events

        if start_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        if detection_type is not None:
            filtered_events = [e for e in filtered_events if e.detection_type == detection_type]

        if severity is not None:
            filtered_events = [e for e in filtered_events if e.severity == severity]

        # 按时间戳降序排序
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)

        # 分页
        paginated_events = filtered_events[offset:offset + limit]

        return paginated_events

    def get_event(self, event_id: str) -> Optional[SecurityEvent]:
        """获取特定安全事件。

        Args:
            event_id: 事件ID

        Returns:
            安全事件，如果不存在则返回None
        """
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def get_events_count(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        detection_type: Optional[DetectionType] = None,
        severity: Optional[Severity] = None,
    ) -> int:
        """获取安全事件数量。

        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳
            detection_type: 检测类型
            severity: 严重程度

        Returns:
            安全事件数量
        """
        # 过滤事件
        filtered_events = self.events

        if start_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        if detection_type is not None:
            filtered_events = [e for e in filtered_events if e.detection_type == detection_type]

        if severity is not None:
            filtered_events = [e for e in filtered_events if e.severity == severity]

        return len(filtered_events)

    def get_events_stats(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, int]:
        """获取安全事件统计。

        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳

        Returns:
            安全事件统计
        """
        # 过滤事件
        filtered_events = self.events

        if start_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time is not None:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        # 统计各类型事件数量
        stats = {
            "prompt_injection": 0,
            "jailbreak": 0,
            "role_play": 0,
            "sensitive_info": 0,
            "harmful_content": 0,
            "compliance_violation": 0,
            "custom": 0,
            "total": len(filtered_events),
        }

        for event in filtered_events:
            if event.detection_type:
                stats[event.detection_type.value] += 1

        return stats

    async def get_rule_hit_ranking(self, limit: int = 10) -> List[Dict]:
        """获取命中次数最多的安全规则排名 (M3.2)。"""
        if self.use_optimized_db and self.db:
            try:
                return await self.db.get_rule_ranking(limit)
            except Exception as e:
                logger.error(f"获取规则排名失败: {e}")
        
        # 回退到内存统计
        from collections import Counter
        counter = Counter()
        rule_map = {}
        for event in self.events:
            if event.rule_id:
                counter[event.rule_id] += 1
                rule_map[event.rule_id] = event.rule_name or "Unknown"
        
        return [
            {"rule_id": rid, "rule_name": rule_map.get(rid, "Unknown"), "hit_count": count}
            for rid, count in counter.most_common(limit)
        ]


# 创建全局事件记录器实例
event_logger = SecurityEventLogger()
