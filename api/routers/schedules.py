"""
定时调度管理路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from api.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    ScheduleResponse,
    ScheduleListResponse,
)
from api.middleware.session import require_session_id
from api.services.scheduler import get_scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreateRequest,
    session_id: str = Depends(require_session_id),
):
    """创建定时调度计划"""
    svc = get_scheduler_service()
    try:
        return await svc.create_schedule(request, created_by=session_id)
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=ScheduleListResponse)
async def list_schedules(
    platform: Optional[str] = Query(None),
    enabled_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: str = Depends(require_session_id),
):
    """获取定时调度列表"""
    svc = get_scheduler_service()
    schedules, total = await svc.list_schedules(
        platform=platform,
        enabled_only=enabled_only,
        page=page,
        page_size=page_size,
    )
    return ScheduleListResponse(schedules=schedules, total=total)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    session_id: str = Depends(require_session_id),
):
    """获取调度详情"""
    svc = get_scheduler_service()
    try:
        return await svc.get_schedule(schedule_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdateRequest,
    session_id: str = Depends(require_session_id),
):
    """更新定时调度"""
    svc = get_scheduler_service()
    try:
        return await svc.update_schedule(schedule_id, request)
    except ValueError:
        raise HTTPException(status_code=404, detail="Schedule not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    session_id: str = Depends(require_session_id),
):
    """删除定时调度"""
    svc = get_scheduler_service()
    success = await svc.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted"}


@router.post("/{schedule_id}/pause", response_model=ScheduleResponse)
async def pause_schedule(
    schedule_id: str,
    session_id: str = Depends(require_session_id),
):
    """暂停定时调度"""
    svc = get_scheduler_service()
    try:
        return await svc.pause_schedule(schedule_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/{schedule_id}/resume", response_model=ScheduleResponse)
async def resume_schedule(
    schedule_id: str,
    session_id: str = Depends(require_session_id),
):
    """恢复定时调度"""
    svc = get_scheduler_service()
    try:
        return await svc.resume_schedule(schedule_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    session_id: str = Depends(require_session_id),
):
    """立即触发一次调度"""
    svc = get_scheduler_service()
    task_id = await svc.trigger_now(schedule_id)
    if not task_id:
        raise HTTPException(status_code=400, detail="Failed to trigger schedule")
    return {"message": "Schedule triggered", "task_id": task_id}
