"""安全事件API。"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel

from src.audit.event_logger import SecurityEvent, event_logger
from src.logger import logger
from src.models_interceptor import DetectionType, Severity


router = APIRouter()


class EventResponse(BaseModel):
    """安全事件响应。"""

    event_id: str
    timestamp: float
    detection_type: Optional[str] = None
    severity: Optional[str] = None
    reason: str
    details: Dict
    content: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    matched_pattern: Optional[str] = None
    matched_text: Optional[str] = None
    matched_keyword: Optional[str] = None


class EventsResponse(BaseModel):
    """安全事件列表响应。"""

    events: List[EventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EventsStatsResponse(BaseModel):
    """安全事件统计响应。"""

    prompt_injection: int
    jailbreak: int
    role_play: int
    sensitive_info: int
    harmful_content: int
    compliance_violation: int
    custom: int
    total: int


@router.get("/api/v1/events", response_model=EventsResponse)
async def get_events(
    start_time: Optional[float] = Query(None, description="开始时间戳"),
    end_time: Optional[float] = Query(None, description="结束时间戳"),
    detection_type: Optional[str] = Query(None, description="检测类型"),
    severity: Optional[str] = Query(None, description="严重程度"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
):
    """获取安全事件列表。

    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳
        detection_type: 检测类型
        severity: 严重程度
        page: 页码
        page_size: 每页数量

    Returns:
        安全事件列表
    """
    try:
        # 转换检测类型
        detection_type_enum = None
        if detection_type:
            try:
                detection_type_enum = DetectionType(detection_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的检测类型: {detection_type}"
                )

        # 转换严重程度
        severity_enum = None
        if severity:
            try:
                severity_enum = Severity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的严重程度: {severity}"
                )

        # 计算偏移量
        offset = (page - 1) * page_size

        # 获取事件
        events = event_logger.get_events(
            start_time=start_time,
            end_time=end_time,
            detection_type=detection_type_enum,
            severity=severity_enum,
            limit=page_size,
            offset=offset,
        )

        # 获取总数
        total = event_logger.get_events_count(
            start_time=start_time,
            end_time=end_time,
            detection_type=detection_type_enum,
            severity=severity_enum,
        )

        # 计算总页数
        total_pages = (total + page_size - 1) // page_size

        # 转换为响应模型
        event_responses = []
        for event in events:
            event_responses.append(EventResponse(
                event_id=event.event_id,
                timestamp=event.timestamp,
                detection_type=event.detection_type.value if event.detection_type else None,
                severity=event.severity.value if event.severity else None,
                reason=event.reason,
                details=event.details,
                content=event.content,
                rule_id=event.rule_id,
                rule_name=event.rule_name,
                matched_pattern=event.matched_pattern,
                matched_text=event.matched_text,
                matched_keyword=event.matched_keyword,
            ))

        return EventsResponse(
            events=event_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"获取安全事件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取安全事件列表失败: {str(e)}"
        )


@router.get("/api/v1/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str = Path(..., description="事件ID")):
    """获取特定安全事件。

    Args:
        event_id: 事件ID

    Returns:
        安全事件
    """
    try:
        event = event_logger.get_event(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"事件 {event_id} 不存在"
            )

        return EventResponse(
            event_id=event.event_id,
            timestamp=event.timestamp,
            detection_type=event.detection_type.value if event.detection_type else None,
            severity=event.severity.value if event.severity else None,
            reason=event.reason,
            details=event.details,
            content=event.content,
            rule_id=event.rule_id,
            rule_name=event.rule_name,
            matched_pattern=event.matched_pattern,
            matched_text=event.matched_text,
            matched_keyword=event.matched_keyword,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取安全事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取安全事件失败: {str(e)}"
        )


@router.get("/api/v1/events/stats", response_model=EventsStatsResponse)
async def get_events_stats(
    start_time: Optional[float] = Query(None, description="开始时间戳"),
    end_time: Optional[float] = Query(None, description="结束时间戳"),
):
    """获取安全事件统计。

    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳

    Returns:
        安全事件统计
    """
    try:
        stats = event_logger.get_events_stats(
            start_time=start_time,
            end_time=end_time,
        )

        return EventsStatsResponse(
            prompt_injection=stats["prompt_injection"],
            jailbreak=stats["jailbreak"],
            role_play=stats["role_play"],
            sensitive_info=stats["sensitive_info"],
            harmful_content=stats["harmful_content"],
            compliance_violation=stats["compliance_violation"],
            custom=stats["custom"],
            total=stats["total"],
        )
    except Exception as e:
        logger.error(f"获取安全事件统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取安全事件统计失败: {str(e)}"
        )
