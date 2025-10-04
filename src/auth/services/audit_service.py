"""审计日志服务。"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.auth.models.audit import (
    AuditActionType,
    AuditLog,
    AuditLogLevel,
    AuditLogQuery,
    AuditLogResponse,
)
from src.logger import logger


class AuditService:
    """审计日志服务类。"""

    def __init__(self, storage_dir: str = "data/audit_logs"):
        """初始化审计日志服务。

        Args:
            storage_dir: 审计日志存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._logs_cache: List[AuditLog] = []
        self._load_logs()

    def _get_storage_path(self, date: Optional[datetime] = None) -> Path:
        """获取审计日志存储路径(按日期分文件)。

        Args:
            date: 日期,默认为今天

        Returns:
            存储路径
        """
        if date is None:
            date = datetime.utcnow()

        filename = f"audit_{date.strftime('%Y%m%d')}.json"
        return self.storage_dir / filename

    def _load_logs(self, days: int = 30) -> None:
        """从磁盘加载最近N天的审计日志。

        Args:
            days: 加载最近几天的日志
        """
        try:
            self._logs_cache = []

            # 加载最近N天的日志文件
            for file_path in sorted(self.storage_dir.glob("audit_*.json"), reverse=True)[:days]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        logs_data = json.load(f)
                        for log_data in logs_data:
                            log = AuditLog(**log_data)
                            self._logs_cache.append(log)
                except Exception as e:
                    logger.error(f"加载审计日志文件失败 {file_path}: {str(e)}")

            logger.info(f"已加载 {len(self._logs_cache)} 条审计日志")

        except Exception as e:
            logger.error(f"加载审计日志失败: {str(e)}")

    def _save_log(self, log: AuditLog) -> None:
        """保存审计日志到磁盘。

        Args:
            log: 审计日志对象
        """
        try:
            # 添加到缓存
            self._logs_cache.insert(0, log)

            # 保存到文件(按日期)
            file_path = self._get_storage_path(log.timestamp)
            existing_logs = []

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_logs = json.load(f)

            # 添加新日志到开头
            existing_logs.insert(0, log.model_dump(mode="json"))

            # 保存回文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            logger.error(f"保存审计日志失败: {str(e)}")
            raise

    async def log_action(
        self,
        action_type: AuditActionType,
        action_description: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        level: AuditLogLevel = AuditLogLevel.INFO,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """记录审计日志。

        Args:
            action_type: 动作类型
            action_description: 动作描述
            user_id: 用户ID
            username: 用户名
            resource_type: 资源类型
            resource_id: 资源ID
            ip_address: IP地址
            user_agent: 用户代理
            level: 日志级别
            success: 是否成功
            error_message: 错误消息
            metadata: 额外元数据

        Returns:
            审计日志对象
        """
        log = AuditLog(
            user_id=user_id,
            username=username,
            action_type=action_type,
            action_description=action_description,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            level=level,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )

        # 保存日志
        self._save_log(log)

        # 记录到系统日志
        log_message = (
            f"审计日志 - {action_type.value}: {action_description} "
            f"(用户: {username or 'system'}, 成功: {success})"
        )

        if level == AuditLogLevel.INFO:
            logger.info(log_message)
        elif level == AuditLogLevel.WARNING:
            logger.warning(log_message)
        elif level == AuditLogLevel.ERROR:
            logger.error(log_message)
        elif level == AuditLogLevel.CRITICAL:
            logger.critical(log_message)

        return log

    async def query_logs(
        self,
        query: AuditLogQuery
    ) -> AuditLogResponse:
        """查询审计日志。

        Args:
            query: 查询参数

        Returns:
            审计日志查询响应
        """
        filtered_logs = self._logs_cache.copy()

        # 应用过滤条件
        if query.user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == query.user_id]

        if query.username:
            filtered_logs = [log for log in filtered_logs if log.username == query.username]

        if query.action_type:
            filtered_logs = [log for log in filtered_logs if log.action_type == query.action_type]

        if query.resource_type:
            filtered_logs = [log for log in filtered_logs if log.resource_type == query.resource_type]

        if query.resource_id:
            filtered_logs = [log for log in filtered_logs if log.resource_id == query.resource_id]

        if query.level:
            filtered_logs = [log for log in filtered_logs if log.level == query.level]

        if query.success is not None:
            filtered_logs = [log for log in filtered_logs if log.success == query.success]

        if query.start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= query.start_time]

        if query.end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= query.end_time]

        # 统计总数
        total = len(filtered_logs)

        # 分页
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_logs = filtered_logs[start_idx:end_idx]

        return AuditLogResponse(
            total=total,
            logs=paginated_logs,
            limit=query.limit,
            offset=query.offset
        )

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动摘要。

        Args:
            user_id: 用户ID
            days: 统计最近几天

        Returns:
            活动摘要
        """
        # 查询用户的日志
        user_logs = [log for log in self._logs_cache if log.user_id == user_id]

        # 统计各类操作数量
        action_counts: Dict[str, int] = {}
        for log in user_logs:
            action_type = log.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        # 统计成功/失败操作
        success_count = sum(1 for log in user_logs if log.success)
        failure_count = len(user_logs) - success_count

        # 最近活动
        recent_activities = sorted(user_logs, key=lambda x: x.timestamp, reverse=True)[:10]

        return {
            "user_id": user_id,
            "total_actions": len(user_logs),
            "success_count": success_count,
            "failure_count": failure_count,
            "action_counts": action_counts,
            "recent_activities": [
                {
                    "timestamp": log.timestamp,
                    "action_type": log.action_type.value,
                    "description": log.action_description,
                    "success": log.success
                }
                for log in recent_activities
            ]
        }

    def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧的审计日志文件。

        Args:
            days: 保留最近几天的日志

        Returns:
            清理的文件数量
        """
        count = 0
        try:
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            # 找出过期的日志文件
            for file_path in self.storage_dir.glob("audit_*.json"):
                try:
                    # 从文件名提取日期
                    date_str = file_path.stem.replace("audit_", "")
                    file_date = datetime.strptime(date_str, "%Y%m%d")

                    # 计算天数差
                    days_diff = (cutoff_date - file_date).days

                    if days_diff > days:
                        file_path.unlink()
                        count += 1
                        logger.info(f"已删除过期审计日志: {file_path.name}")

                except Exception as e:
                    logger.error(f"处理审计日志文件失败 {file_path}: {str(e)}")

            if count > 0:
                logger.info(f"清理了 {count} 个过期审计日志文件")

        except Exception as e:
            logger.error(f"清理审计日志失败: {str(e)}")

        return count


# 创建全局审计服务实例
audit_service = AuditService()
