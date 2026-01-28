"""
任务管理路由
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends

from api.services.factory import get_task_manager
from api.services.task_manager import (
    TaskManagerError, QuotaExceededError, 
    TaskNotFoundError, PermissionDeniedError
)
from api.schemas.task import (
    Task, TaskStatus, TaskCreateRequest, 
    TaskListRequest, TaskListResponse, TaskStatsResponse
)
from api.schemas.event import LogEntry
from api.middleware.session import require_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/", response_model=Task)
async def create_task(
    request: TaskCreateRequest,
    session_id: str = Depends(require_session_id)
):
    """创建任务"""
    task_manager = get_task_manager()
    
    try:
        task = await task_manager.create_task(session_id, request)
        logger.info(f"Task created: {task.task_id} by session {session_id[:8]}")
        return task
    except QuotaExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except TaskManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    session_id: str = Depends(require_session_id)
):
    """获取任务列表"""
    task_manager = get_task_manager()
    
    request = TaskListRequest(
        status=status,
        platform=platform,
        page=page,
        page_size=page_size
    )
    
    tasks = await task_manager.list_tasks(session_id, request)
    total = await task_manager.count_tasks(session_id)
    
    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    session_id: str = Depends(require_session_id)
):
    """获取任务统计"""
    task_manager = get_task_manager()
    return await task_manager.get_stats(session_id)


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    session_id: str = Depends(require_session_id)
):
    """获取任务详情"""
    task_manager = get_task_manager()
    
    try:
        return await task_manager.get_task(session_id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")


@router.get("/{task_id}/logs", response_model=List[LogEntry])
async def get_task_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None, description="Filter by log level"),
    session_id: str = Depends(require_session_id)
):
    """获取任务日志"""
    task_manager = get_task_manager()
    
    try:
        return await task_manager.get_logs(
            session_id, task_id,
            limit=limit, offset=offset, level=level
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    session_id: str = Depends(require_session_id)
):
    """取消任务"""
    task_manager = get_task_manager()
    
    try:
        success = await task_manager.cancel_task(session_id, task_id)
        if success:
            return {"message": "Task cancelled"}
        else:
            return {"message": "Task cannot be cancelled"}
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")


@router.post("/{task_id}/retry", response_model=Task)
async def retry_task(
    task_id: str,
    session_id: str = Depends(require_session_id)
):
    """重试任务"""
    task_manager = get_task_manager()
    
    try:
        return await task_manager.retry_task(session_id, task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except TaskManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{task_id}/priority")
async def update_task_priority(
    task_id: str,
    priority: int = Query(..., ge=1, le=10, description="New priority"),
    session_id: str = Depends(require_session_id)
):
    """调整任务优先级"""
    task_manager = get_task_manager()
    
    try:
        success = await task_manager.update_priority(session_id, task_id, priority)
        if success:
            return {"message": f"Priority updated to {priority}"}
        else:
            return {"message": "Priority cannot be updated"}
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session_id: str = Depends(require_session_id)
):
    """删除任务"""
    task_manager = get_task_manager()
    
    try:
        success = await task_manager.delete_task(session_id, task_id)
        return {"message": "Task deleted"}
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except TaskManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))

