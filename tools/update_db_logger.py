import re
import os

db_file = "src/database/optimized_db.py"
with open(db_file, "r") as f:
    text = f.read()

new_methods = """
    async def get_events_by_time_range(
        self,
        start_time: float = None,
        end_time: float = None,
        detection_type: str = None,
        severity: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        conditions = []
        params = []
        
        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)
            
        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)
            
        if detection_type:
            conditions.append("detection_type = ?")
            params.append(detection_type)
            
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM security_events WHERE {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = await self.pool.execute_query(query, tuple(params), QueryType.SELECT)
        
        columns = [
            'id', 'event_id', 'timestamp', 'detection_type', 'severity', 
            'reason', 'details', 'content', 'rule_id', 'rule_name',
            'matched_pattern', 'matched_text', 'matched_keyword', 
            'created_at', 'indexed_at'
        ]
        
        events = []
        import json
        for row in rows:
            event_dict = dict(zip(columns, row))
            if event_dict['details']:
                try:
                    event_dict['details'] = json.loads(event_dict['details'])
                except:
                    pass
            events.append(event_dict)
        return events

    async def get_events_count_by_time_range(
        self,
        start_time: float = None,
        end_time: float = None,
        detection_type: str = None,
        severity: str = None
    ) -> int:
        conditions = []
        params = []
        
        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)
            
        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)
            
        if detection_type:
            conditions.append("detection_type = ?")
            params.append(detection_type)
            
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT COUNT(*) FROM security_events WHERE {where_clause}"
        
        rows = await self.pool.execute_query(query, tuple(params), QueryType.SELECT)
        return rows[0][0] if rows else 0

    async def get_events_stats_by_time_range(
        self,
        start_time: float = None,
        end_time: float = None
    ) -> Dict[str, int]:
        conditions = []
        params = []
        
        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)
            
        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT detection_type, COUNT(*) FROM security_events WHERE {where_clause} GROUP BY detection_type"
        
        rows = await self.pool.execute_query(query, tuple(params), QueryType.SELECT)
        
        stats = {
            "prompt_injection": 0,
            "jailbreak": 0,
            "role_play": 0,
            "sensitive_info": 0,
            "harmful_content": 0,
            "compliance_violation": 0,
            "custom": 0,
            "total": 0,
        }
        
        for row in rows:
            dtype = row[0]
            count = row[1]
            if dtype in stats:
                stats[dtype] += count
            else:
                stats["custom"] += count
            stats["total"] += count
            
        return stats
"""

if "get_events_by_time_range" not in text:
    text = text.replace("    async def cleanup_old_events(self, days: int = 30):", new_methods + "\n    async def cleanup_old_events(self, days: int = 30):")
    with open(db_file, "w") as f:
        f.write(text)
    print("Updated " + db_file)
else:
    print("Already updated " + db_file)

logger_file = "src/audit/event_logger.py"
with open(logger_file, "r") as f:
    text = f.read()

new_async_methods = """
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
                return [self.from_dict(d) for d in db_events]
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
"""

if "async def get_events_async" not in text:
    text = text.replace("    def get_events(", new_async_methods + "\n    def get_events(")
    with open(logger_file, "w") as f:
        f.write(text)
    print("Updated " + logger_file)
else:
    print("Already updated " + logger_file)
