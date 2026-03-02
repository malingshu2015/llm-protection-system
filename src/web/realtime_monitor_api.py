"""实时客户端输入监控API模块。"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.audit.event_logger import event_logger, SecurityEvent, ContentSanitizer
from src.models_interceptor import DetectionType, Severity
from src.logger import logger

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])

# WebSocket连接管理器
class ConnectionManager:
    """WebSocket连接管理器。"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_info: Dict = None):
        """建立WebSocket连接。"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_info[websocket] = client_info or {"client_id": "unknown", "type": "monitor"}
        logger.info(f"实时监控连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接。"""
        self.active_connections.discard(websocket)
        self.client_info.pop(websocket, None)
        logger.info(f"实时监控连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """向所有连接的客户端广播消息。"""
        if not self.active_connections:
            return
            
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"WebSocket广播失败: {e}")
                dead_connections.add(connection)
        
        # 清理失效连接
        for conn in dead_connections:
            self.disconnect(conn)

# 全局连接管理器
manager = ConnectionManager()

# 数据模型
class RealtimeEvent(BaseModel):
    """实时事件模型。"""
    event_id: str
    timestamp: float
    client_type: str
    client_id: str
    original_content: str
    sanitized_content: str
    detection_type: Optional[str]
    severity: Optional[str]
    reason: str
    rule_name: Optional[str] = None
    matched_text: Optional[str] = None
    is_blocked: bool = False
    response_time_ms: float = 0.0

class RealtimeStats(BaseModel):
    """实时统计模型。"""
    total_events: int
    blocked_events: int
    allowed_events: int
    events_last_minute: int
    events_last_hour: int
    top_detection_types: Dict[str, int]
    client_types: Dict[str, int]

class LiveInputTracker:
    """实时输入追踪器。"""
    
    def __init__(self):
        self.recent_events: List[RealtimeEvent] = []
        self.max_events = 1000  # 最多保留1000条记录
        
    def add_event(
        self,
        content: str,
        client_type: str = "web",
        client_id: str = "unknown",
        detection_result=None,
        response_time_ms: float = 0.0
    ) -> RealtimeEvent:
        """添加实时事件。"""
        
        # 脱敏处理
        sanitized_content = ContentSanitizer.sanitize_content(content, max_length=200)
        
        # 创建实时事件
        event = RealtimeEvent(
            event_id=f"rt_{int(time.time() * 1000)}_{len(self.recent_events)}",
            timestamp=time.time(),
            client_type=client_type,
            client_id=client_id,
            original_content=content[:500],  # 限制长度
            sanitized_content=sanitized_content,
            detection_type=detection_result.detection_type.value if detection_result and detection_result.detection_type else None,
            severity=detection_result.severity.value if detection_result and detection_result.severity else None,
            reason=detection_result.reason if detection_result else "No detection",
            rule_name=detection_result.details.get("rule_name") if detection_result and detection_result.details else None,
            matched_text=detection_result.details.get("matched_text") if detection_result and detection_result.details else None,
            is_blocked=not detection_result.is_allowed if detection_result else False,
            response_time_ms=response_time_ms
        )
        
        # 添加到实时列表
        self.recent_events.insert(0, event)
        
        # 限制列表大小
        if len(self.recent_events) > self.max_events:
            self.recent_events = self.recent_events[:self.max_events]
        
        return event
    
    def get_recent_events(self, limit: int = 50) -> List[RealtimeEvent]:
        """获取最近的事件。"""
        return self.recent_events[:limit]
    
    def get_stats(self) -> RealtimeStats:
        """获取实时统计。"""
        now = time.time()
        
        # 统计最近的事件
        last_minute = [e for e in self.recent_events if now - e.timestamp <= 60]
        last_hour = [e for e in self.recent_events if now - e.timestamp <= 3600]
        
        # 按检测类型统计
        detection_types = {}
        client_types = {}
        
        for event in self.recent_events:
            if event.detection_type:
                detection_types[event.detection_type] = detection_types.get(event.detection_type, 0) + 1
            client_types[event.client_type] = client_types.get(event.client_type, 0) + 1
        
        return RealtimeStats(
            total_events=len(self.recent_events),
            blocked_events=sum(1 for e in self.recent_events if e.is_blocked),
            allowed_events=sum(1 for e in self.recent_events if not e.is_blocked),
            events_last_minute=len(last_minute),
            events_last_hour=len(last_hour),
            top_detection_types=detection_types,
            client_types=client_types
        )

# 全局实时追踪器
live_tracker = LiveInputTracker()

# WebSocket路由
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点。"""
    await manager.connect(websocket, {"client_type": "monitor", "client_id": "monitor_client"})
    
    try:
        # 发送初始数据
        initial_data = {
            "type": "initial_data",
            "events": [event.dict() for event in live_tracker.get_recent_events(limit=20)],
            "stats": live_tracker.get_stats().dict()
        }
        await websocket.send_json(initial_data)
        
        # 保持连接并发送心跳
        while True:
            # 每30秒发送一次心跳
            await asyncio.sleep(30)
            await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

# REST API路由
@router.get("/events", response_model=List[RealtimeEvent])
async def get_realtime_events(
    limit: int = Query(default=50, ge=1, le=100),
    client_type: Optional[str] = None,
    detection_type: Optional[str] = None
):
    """获取实时事件列表。"""
    events = live_tracker.get_recent_events(limit)
    
    # 应用筛选条件
    if client_type:
        events = [e for e in events if e.client_type == client_type]
    if detection_type:
        events = [e for e in events if e.detection_type == detection_type]
    
    return events

@router.get("/rule-stats", response_model=List[Dict])
async def get_rule_hit_stats(limit: int = Query(default=10, ge=1, le=50)):
    """获取规则命中数统计排名 (M3.2)。"""
    return await event_logger.get_rule_hit_ranking(limit)

@router.get("/stats", response_model=RealtimeStats)
async def get_realtime_stats():
    """获取实时统计信息。"""
    return live_tracker.get_stats()

@router.get("/dashboard")
async def get_monitor_dashboard():
    """获取实时监控仪表板页面。"""
    return HTMLResponse(content=get_monitor_html())

# 辅助函数：供其他模块调用的实时事件接口
async def broadcast_realtime_event(
    content: str,
    client_type: str = "web",
    client_id: str = "unknown",
    detection_result=None,
    response_time_ms: float = 0.0
):
    """广播实时事件到所有连接的客户端。"""
    event = live_tracker.add_event(
        content=content,
        client_type=client_type,
        client_id=client_id,
        detection_result=detection_result,
        response_time_ms=response_time_ms
    )
    
    # 广播到所有WebSocket连接
    await manager.broadcast({
        "type": "new_event",
        "event": event.dict(),
        "stats": live_tracker.get_stats().dict()
    })

def get_monitor_html() -> str:
    """获取实时监控仪表板HTML - 与系统风格完全一致的设计。"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>实时客户端输入监控 - 大模型防火墙</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #007AFF;
            --primary-light: #5AC8FA;
            --secondary: #5856D6;
            --success: #34C759;
            --warning: #FF9500;
            --danger: #FF3B30;
            --gray-50: #F2F2F7;
            --gray-100: #E5E5EA;
            --gray-200: #D1D1D6;
            --gray-300: #C7C7CC;
            --gray-400: #AEAEB2;
            --gray-500: #8E8E93;
            --gray-600: #636366;
            --gray-700: #48484A;
            --gray-800: #3A3A3C;
            --gray-900: #1C1C1E;
            --background: #F2F2F7;
            --surface: #FFFFFF;
            --surface-elevated: #FFFFFF;
            --text-primary: #000000;
            --text-secondary: #3A3A3C;
            --text-tertiary: #8E8E93;
            --border: #C7C7CC;
            --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
            --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05);
            --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.1), 0 10px 10px rgba(0, 0, 0, 0.04);
            --border-radius: 12px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
            background-color: var(--background);
            color: var(--text-primary);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }

        .header {
            background: var(--surface-elevated);
            border-radius: var(--border-radius);
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border);
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .header-title h1 {
            font-size: 32px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .header-title p {
            font-size: 16px;
            color: var(--text-secondary);
        }

        .connection-status {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse 2s infinite;
        }

        .status-dot.disconnected {
            background: var(--danger);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--surface-elevated);
            border-radius: var(--border-radius);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border);
            transition: var(--transition);
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        .stat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .stat-icon.total { background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: white; }
        .stat-icon.blocked { background: linear-gradient(135deg, var(--danger), #FF6B6B); color: white; }
        .stat-icon.allowed { background: linear-gradient(135deg, var(--success), #4ECDC4); color: white; }
        .stat-icon.recent { background: linear-gradient(135deg, var(--warning), #FFA726); color: white; }

        .stat-content h3 {
            font-size: 14px;
            color: var(--text-tertiary);
            margin-bottom: 4px;
            font-weight: 500;
        }

        .stat-content .value {
            font-size: 28px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .filters-section {
            background: var(--surface-elevated);
            border-radius: var(--border-radius);
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border);
        }

        .filters-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .filter-group {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }

        .filter-select {
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface);
            color: var(--text-primary);
            font-size: 14px;
            min-width: 120px;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-secondary {
            background: var(--gray-100);
            color: var(--text-secondary);
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
            margin-top: 16px;
        }

        .chart-container {
            background: var(--surface);
            border-radius: var(--border-radius);
            padding: 20px;
            border: 1px solid var(--border);
        }

        .chart-header {
            margin-bottom: 16px;
        }

        .chart-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .events-section {
            background: var(--surface-elevated);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border);
            overflow: hidden;
        }

        .events-header {
            padding: 24px;
            border-bottom: 1px solid var(--border);
            background: var(--surface);
        }

        .events-title {
            font-size: 20px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .events-container {
            max-height: 600px;
            overflow-y: auto;
            background: var(--surface);
        }

        .event-item {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            transition: var(--transition);
            position: relative;
        }

        .event-item:last-child {
            border-bottom: none;
        }

        .event-item:hover {
            background: var(--gray-50);
        }

        .event-item.new {
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .event-status-bar {
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            border-radius: 0 2px 2px 0;
        }

        .event-status-bar.blocked { background: var(--danger); }
        .event-status-bar.allowed { background: var(--success); }
        .event-status-bar.warning { background: var(--warning); }

        .event-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }

        .event-meta {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        .event-badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }

        .badge-client { background: var(--primary); color: white; }
        .badge-type { background: var(--gray-100); color: var(--text-secondary); }
        .badge-severity-high { background: var(--danger); color: white; }
        .badge-severity-medium { background: var(--warning); color: white; }
        .badge-severity-low { background: var(--success); color: white; }

        .event-status {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }

        .status-blocked { background: var(--danger); color: white; }
        .status-allowed { background: var(--success); color: white; }

        .event-content {
            margin-left: 20px;
        }

        .event-input {
            font-size: 14px;
            color: var(--text-primary);
            margin-bottom: 8px;
            line-height: 1.5;
        }

        .event-reason {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .event-rule {
            font-size: 12px;
            color: var(--text-tertiary);
            background: var(--gray-100);
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
        }

        .event-matched {
            font-size: 12px;
            color: var(--danger);
            margin-top: 4px;
        }

        .empty-state {
            text-align: center;
            padding: 48px;
            color: var(--text-tertiary);
        }

        .empty-state i {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }

        @media (max-width: 768px) {
            .container {
                padding: 16px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header-title h1 {
                font-size: 24px;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
                gap: 16px;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .filter-group {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-content">
                <div class="header-title">
                    <h1>实时客户端输入监控</h1>
                    <p>监控所有客户端的实时输入内容和安全检测情况</p>
                </div>
                <div class="connection-status">
                    <div class="status-indicator">
                        <div class="status-dot" id="status-dot"></div>
                        <span id="connection-status">连接中...</span>
                    </div>
                    <div class="status-indicator">
                        <i class="fas fa-stream"></i>
                        <span id="event-count">0</span>
                    </div>
                    <button onclick="toggleAutoScroll()" class="btn btn-primary">
                        <i class="fas fa-arrow-down" id="auto-scroll-icon"></i>
                        <span id="auto-scroll-text">自动滚动</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon total">
                        <i class="fas fa-chart-line"></i>
                    </div>
                </div>
                <div class="stat-content">
                    <h3>总事件</h3>
                    <div class="value" id="total-events">0</div>
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon blocked">
                        <i class="fas fa-shield-alt"></i>
                    </div>
                </div>
                <div class="stat-content">
                    <h3>已阻止</h3>
                    <div class="value" id="blocked-events">0</div>
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon allowed">
                        <i class="fas fa-check-circle"></i>
                    </div>
                </div>
                <div class="stat-content">
                    <h3>已允许</h3>
                    <div class="value" id="allowed-events">0</div>
                </div>
            </div>

            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon recent">
                        <i class="fas fa-clock"></i>
                    </div>
                </div>
                <div class="stat-content">
                    <h3>最近1分钟</h3>
                    <div class="value" id="recent-events">0</div>
                </div>
            </div>
        </div>

        <!-- Filters and Charts -->
        <div class="filters-section">
            <div class="filters-header">
                <h2 class="chart-title">筛选器</h2>
                <div class="filter-group">
                    <select id="client-filter" class="filter-select">
                        <option value="">所有客户端</option>
                        <option value="web">Web端</option>
                        <option value="mobile">移动端</option>
                        <option value="desktop">桌面端</option>
                        <option value="api">API调用</option>
                    </select>
                    
                    <select id="detection-filter" class="filter-select">
                        <option value="">所有类型</option>
                        <option value="prompt_injection">提示注入</option>
                        <option value="jailbreak">越狱</option>
                        <option value="sensitive_info">敏感信息</option>
                        <option value="harmful_content">有害内容</option>
                    </select>
                    
                    <button onclick="clearFilters()" class="btn btn-secondary">
                        <i class="fas fa-eraser"></i>
                        清除筛选
                    </button>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-header">
                        <h3 class="chart-title">检测类型分布</h3>
                    </div>
                    <canvas id="detection-chart" width="400" height="200"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-header">
                        <h3 class="chart-title">客户端类型分布</h3>
                    </div>
                    <canvas id="client-chart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>

        <!-- Events List -->
        <div class="events-section">
            <div class="events-header">
                <h2 class="events-title">实时事件流</h2>
            </div>
            <div class="events-container" id="events-container">
                <div id="events-list">
                    <div class="empty-state">
                        <i class="fas fa-stream"></i>
                        <p>等待实时事件...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let autoScroll = true;
        let charts = {};

        // Initialize WebSocket
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/v1/realtime/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
                updateConnectionStatus('已连接', true);
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected');
                updateConnectionStatus('断开连接', false);
                setTimeout(initWebSocket, 5000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus('连接错误', false);
            };
        }

        function updateConnectionStatus(text, connected) {
            const statusElement = document.getElementById('connection-status');
            const dotElement = document.getElementById('status-dot');
            
            statusElement.textContent = text;
            dotElement.className = connected ? 'status-dot' : 'status-dot disconnected';
        }

        function handleWebSocketMessage(data) {
            switch(data.type) {
                case 'initial_data':
                    updateStats(data.stats);
                    updateCharts(data.stats);
                    renderEvents(data.events);
                    break;
                case 'new_event':
                    addNewEvent(data.event);
                    updateStats(data.stats);
                    updateCharts(data.stats);
                    break;
                case 'heartbeat':
                    break;
            }
        }

        function renderEvents(events) {
            const container = document.getElementById('events-list');
            
            if (events.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-stream"></i>
                        <p>暂无事件数据</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = '';
            events.forEach(event => {
                const eventElement = createEventElement(event);
                container.appendChild(eventElement);
            });
        }

        function addNewEvent(event) {
            const container = document.getElementById('events-list');
            const emptyState = container.querySelector('.empty-state');
            
            if (emptyState) {
                container.innerHTML = '';
            }

            const eventElement = createEventElement(event);
            eventElement.classList.add('new');
            
            container.insertBefore(eventElement, container.firstChild);
            
            // Limit displayed events
            const maxEvents = 100;
            while (container.children.length > maxEvents) {
                container.removeChild(container.lastChild);
            }
            
            if (autoScroll) {
                const container = document.getElementById('events-container');
                container.scrollTop = 0;
            }
        }

        function createEventElement(event) {
            const div = document.createElement('div');
            div.className = 'event-item';
            
            const statusClass = event.is_blocked ? 'blocked' : event.severity === 'high' ? 'warning' : 'allowed';
            const statusText = event.is_blocked ? '已阻止' : '已允许';
            const statusClassText = event.is_blocked ? 'status-blocked' : 'status-allowed';
            
            const timestamp = new Date(event.timestamp * 1000).toLocaleString();
            
            div.innerHTML = `
                <div class="event-status-bar ${statusClass}"></div>
                <div class="event-header">
                    <div class="event-meta">
                        <span class="event-badge badge-client">${event.client_type}</span>
                        ${event.detection_type ? `<span class="event-badge badge-type">${event.detection_type}</span>` : ''}
                        ${event.severity ? `<span class="event-badge badge-severity-${event.severity}">${event.severity}</span>` : ''}
                    </div>
                    <span class="event-status ${statusClassText}">${statusText}</span>
                </div>
                <div class="event-content">
                    <div class="event-input">${event.sanitized_content}</div>
                    <div class="event-reason">${event.reason}</div>
                    ${event.rule_name ? `<span class="event-rule">${event.rule_name}</span>` : ''}
                    ${event.matched_text ? `<div class="event-matched">匹配: ${event.matched_text}</div>` : ''}
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px;">${timestamp}</div>
                </div>
            `;
            
            return div;
        }

        function updateStats(stats) {
            document.getElementById('total-events').textContent = stats.total_events || 0;
            document.getElementById('blocked-events').textContent = stats.blocked_events || 0;
            document.getElementById('allowed-events').textContent = stats.allowed_events || 0;
            document.getElementById('recent-events').textContent = stats.events_last_minute || 0;
            document.getElementById('event-count').textContent = stats.total_events || 0;
        }

        function updateCharts(stats) {
            updateDetectionChart(stats.top_detection_types || {});
            updateClientChart(stats.client_types || {});
        }

        function updateDetectionChart(detectionTypes) {
            const ctx = document.getElementById('detection-chart').getContext('2d');
            
            if (charts.detection) {
                charts.detection.destroy();
            }
            
            const labels = Object.keys(detectionTypes);
            const data = Object.values(detectionTypes);
            
            if (labels.length === 0) {
                charts.detection = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['暂无数据'],
                        datasets: [{
                            data: [1],
                            backgroundColor: ['#E5E5EA'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        }
                    }
                });
                return;
            }
            
            charts.detection = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: [
                            'var(--danger)',
                            'var(--warning)',
                            'var(--success)',
                            'var(--primary)',
                            'var(--secondary)'
                        ],
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                font: {
                                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI"',
                                    size: 12
                                }
                            }
                        }
                    }
                }
            });
        }

        function updateClientChart(clientTypes) {
            const ctx = document.getElementById('client-chart').getContext('2d');
            
            if (charts.client) {
                charts.client.destroy();
            }
            
            const labels = Object.keys(clientTypes);
            const data = Object.values(clientTypes);
            
            if (labels.length === 0) {
                charts.client = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['暂无数据'],
                        datasets: [{
                            data: [0],
                            backgroundColor: ['#E5E5EA']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
                return;
            }
            
            charts.client = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '事件数量',
                        data: data,
                        backgroundColor: 'var(--primary)',
                        borderRadius: 4,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                font: {
                                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI"',
                                    size: 12
                                }
                            }
                        },
                        x: {
                            ticks: {
                                font: {
                                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI"',
                                    size: 12
                                }
                            }
                        }
                    }
                }
            });
        }

        function toggleAutoScroll() {
            autoScroll = !autoScroll;
            const icon = document.getElementById('auto-scroll-icon');
            const text = document.getElementById('auto-scroll-text');
            
            if (autoScroll) {
                icon.className = 'fas fa-arrow-down';
                text.textContent = '自动滚动';
            } else {
                icon.className = 'fas fa-pause';
                text.textContent = '暂停滚动';
            }
        }

        function clearFilters() {
            document.getElementById('client-filter').value = '';
            document.getElementById('detection-filter').value = '';
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            initWebSocket();
        });
    </script>
</body>
</html>
    """

# 导出接口供其他模块使用
__all__ = ['broadcast_realtime_event', 'live_tracker', 'manager']