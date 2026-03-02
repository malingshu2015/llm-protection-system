"""Elasticsearch adapter for centralized audit logging (M3.1)."""
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime

from elasticsearch import AsyncElasticsearch
from src.config import settings
from src.logger import logger
from src.models_interceptor import DetectionResult


class ElasticsearchAdapter:
    """Adapter for sending security events to Elasticsearch."""

    def __init__(self):
        self.es: AsyncElasticsearch = None
        self.is_connected = False
        self._batch_queue: List[Dict[str, Any]] = []
        self._batch_size = 50
        self._flush_interval = 5.0
        self._lock = asyncio.Lock()
        self._flush_task = None
        
        self.index_prefix = settings.audit.es_index_prefix
        
    async def connect(self):
        """Connect to Elasticsearch cluster."""
        if not settings.audit.enable_elasticsearch:
            return
            
        try:
            hosts = [h.strip() for h in settings.audit.es_hosts.split(',')]
            
            es_kwargs = {"hosts": hosts}
            if settings.audit.es_username and settings.audit.es_password:
                es_kwargs["basic_auth"] = (settings.audit.es_username, settings.audit.es_password)
                
            self.es = AsyncElasticsearch(**es_kwargs)
            
            # Test connection
            if await self.es.ping():
                self.is_connected = True
                logger.info(f"成功连接至 Elasticsearch 集群: {hosts}")
                
                # Start background flush task
                self._flush_task = asyncio.create_task(self._periodic_flush())
            else:
                logger.error("连接 Elasticsearch 失败: ping=False")
        except Exception as e:
            logger.error(f"初始化 Elasticsearch 客户端失败: {e}")
            
    async def close(self):
        """Close connection."""
        if self._flush_task:
            self._flush_task.cancel()
            
        # Flush remaining events
        await self._flush()
        
        if self.es:
            await self.es.close()
            self.is_connected = False
            
    async def log_event(self, result: DetectionResult, sanitized_content: str, event_id: str):
        """Queue event for batch push to ES.
        
        Args:
            result: The detection result
            sanitized_content: Checked content with sensitive bits masked
            event_id: Unique event ID
        """
        if not self.is_connected:
            return
            
        doc = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": event_id,
            "detection_type": result.detection_type.value if result.detection_type else "unknown",
            "severity": result.severity.value if result.severity else "unknown",
            "reason": result.reason,
            "is_allowed": result.is_allowed,
            "matched_snippet": sanitized_content[:1500],  # store snippets for Kibana reading
            "details": result.details or {}
        }
        
        async with self._lock:
            self._batch_queue.append(doc)
            
        if len(self._batch_queue) >= self._batch_size:
            # Kick off async flush
            asyncio.create_task(self._flush())
            
    async def _periodic_flush(self):
        """Background task to regularly flush queue."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush()
            
    async def _flush(self):
        """Flush batched queue to Elasticsearch Bulk API."""
        async with self._lock:
            if not self._batch_queue:
                return
            batch_to_send = self._batch_queue[:]
            self._batch_queue.clear()
            
        if not batch_to_send or not self.is_connected:
            return
            
        try:
            # Build bulk payload
            today = datetime.utcnow().strftime("%Y.%m.%d")
            index_name = f"{self.index_prefix}-{today}"
            
            # Format according to ES bulk API requirements
            bulk_data = []
            for doc in batch_to_send:
                bulk_data.append({"index": {"_index": index_name}})
                bulk_data.append(doc)
            
            # Execute bulk insertion
            res = await self.es.bulk(operations=bulk_data)
            
            if res.get("errors"):
                logger.error(f"Elasticsearch 批量写入检测到错误 (Errors=True)")
            else:
                logger.debug(f"已向 Elasticsearch 写入 {len(batch_to_send)} 条安全审计日志")
                
        except Exception as e:
            logger.error(f"Elasticsearch 批量写入失败: {e}")
            
# Singleton
es_adapter = ElasticsearchAdapter()
