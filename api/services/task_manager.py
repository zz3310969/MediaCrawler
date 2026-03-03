"""
任务管理器
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from api.interfaces.queue import ITaskQueue
from api.interfaces.storage import ITaskStorage
from api.interfaces.session import ISessionStore
from api.interfaces.event import IEventBus

from api.schemas.task import (
    Task, TaskStatus, TaskCreateRequest, 
    TaskListRequest, TaskStatsResponse
)
from api.schemas.event import TaskEvent, EventType, LogEntry

logger = logging.getLogger(__name__)


class TaskManagerError(Exception):
    """任务管理器错误基类"""
    pass


class QuotaExceededError(TaskManagerError):
    """配额超限"""
    pass


class TaskNotFoundError(TaskManagerError):
    """任务不存在"""
    pass


class PermissionDeniedError(TaskManagerError):
    """权限不足"""
    pass


class DuplicateTaskError(TaskManagerError):
    """重复任务"""
    pass


class TaskManager:
    """任务管理器"""
    
    def __init__(
        self,
        queue: ITaskQueue,
        storage: ITaskStorage,
        session_store: ISessionStore,
        event_bus: IEventBus
    ):
        self._queue = queue
        self._storage = storage
        self._session_store = session_store
        self._event_bus = event_bus
    
    # ========== 创建任务 ==========
    
    async def create_task(
        self,
        session_id: str,
        request: TaskCreateRequest
    ) -> Task:
        """
        创建任务
        
        Args:
            session_id: 会话 ID
            request: 创建请求
        
        Returns:
            创建的任务
        
        Raises:
            QuotaExceededError: 配额超限
            DuplicateTaskError: 幂等键重复
            PermissionDeniedError: 会话无效
        """
        # 1. 验证会话（API Key 认证使用合成 session_id: "apikey:xxx"）
        is_api_key = session_id.startswith("apikey:")
        if not is_api_key:
            session = await self._session_store.get(session_id)
            if not session:
                raise PermissionDeniedError("Invalid session")
        
        # 2. 幂等键检查
        if request.idempotency_key:
            existing = await self._storage.find_by_idempotency_key(
                session_id, request.idempotency_key
            )
            if existing:
                logger.info(f"Duplicate task with idempotency key: {request.idempotency_key}")
                return existing
        
        # 3. 配额检查：每日任务数（API Key 跳过配额检查）
        if not is_api_key:
            if not await self._session_store.increment_daily_tasks(session_id):
                raise QuotaExceededError("Daily task limit exceeded")
        
        # 4. 配额检查：并发任务数
        if not is_api_key:
            running_count = await self._get_running_count(session.user_id, session_id)
            if running_count >= session.quota.max_concurrent_tasks:
                raise QuotaExceededError("Concurrent task limit exceeded")
        
        # 5. 如果指定了 account_id，从数据库查询 Cookie 写入配置
        if request.config.account_id and not request.config.cookies:
            try:
                from database.db_session import get_session as get_db_session
                from api.services.crud.account import account_crud

                async with get_db_session() as db_session:
                    account = await account_crud.get_by_account_id(
                        db_session, request.config.account_id
                    )
                    if not account:
                        raise TaskManagerError(
                            f"账号不存在: {request.config.account_id}"
                        )
                    if account.platform != request.config.platform:
                        raise TaskManagerError(
                            f"账号平台({account.platform})与任务平台({request.config.platform})不匹配"
                        )
                    if not account.cookies:
                        raise TaskManagerError(
                            f"账号 {account.nickname or account.username or account.account_id} 没有可用的 Cookie"
                        )
                    request.config.cookies = account.cookies
                    request.config.login_type = "cookie"
            except TaskManagerError:
                raise
            except Exception as e:
                logger.warning(f"查询账号 Cookie 失败: {e}，任务将尝试使用本地登录态")

        # 6. 创建任务对象（写入 user_id 实现持久化关联）
        user_id = session.user_id if not is_api_key and session else None
        task = Task(
            session_id=session_id,
            user_id=user_id,
            task_name=request.task_name,
            platform=request.config.platform,
            crawler_type=request.config.crawler_type,
            config=request.config,
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            idempotency_key=request.idempotency_key
        )
        
        # 7. 持久化
        try:
            await self._storage.create(task)
        except ValueError as e:
            raise DuplicateTaskError(str(e))
        
        # 8. 入队
        if request.scheduled_at and request.scheduled_at > datetime.now(timezone.utc):
            delay = (request.scheduled_at - datetime.now(timezone.utc)).total_seconds()
            await self._queue.enqueue_delayed(task, int(delay))
        else:
            await self._queue.enqueue(task, task.priority)
        
        # 9. 发布事件
        await self._event_bus.publish(TaskEvent(
            event_type=EventType.TASK_CREATED,
            task_id=task.task_id,
            session_id=session_id,
            payload={"task_name": task.task_name, "platform": task.config.platform}
        ))
        
        await self._event_bus.publish(TaskEvent(
            event_type=EventType.TASK_QUEUED,
            task_id=task.task_id,
            session_id=session_id
        ))
        
        logger.info(f"Task created: {task.task_id}")
        return task
    
    async def _get_running_count(self, user_id: Optional[str], session_id: str) -> int:
        """获取用户运行中的任务数"""
        tasks = await self._storage.get_by_user(
            user_id=user_id, session_id=session_id, status=TaskStatus.RUNNING
        )
        return len(tasks)
    
    # ========== 查询任务 ==========
    
    async def get_task(self, session_id: str, task_id: str) -> Task:
        """
        获取任务详情
        
        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = await self._storage.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        
        return task
    
    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        获取任务（不检查权限，供内部使用）
        """
        return await self._storage.get(task_id)
    
    async def list_tasks(
        self,
        session_id: str,
        request: TaskListRequest,
        user_id: Optional[str] = None
    ) -> List[Task]:
        """获取任务列表（按 user_id 过滤，无 user_id 时全量）"""
        offset = (request.page - 1) * request.page_size
        
        return await self._storage.get_by_user(
            user_id=user_id,
            session_id=session_id,
            status=request.status,
            platform=request.platform,
            limit=request.page_size,
            offset=offset
        )
    
    async def count_tasks(self, session_id: str, user_id: Optional[str] = None) -> int:
        """获取任务总数"""
        return await self._storage.count_by_user(user_id=user_id, session_id=session_id)
    
    async def get_stats(self, session_id: str, user_id: Optional[str] = None) -> TaskStatsResponse:
        """获取任务统计"""
        counts = await self._storage.count_by_status(user_id=user_id)
        
        return TaskStatsResponse(
            pending=counts.get("pending", 0),
            running=counts.get("running", 0),
            completed=counts.get("completed", 0),
            failed=counts.get("failed", 0),
            cancelled=counts.get("cancelled", 0),
            total=sum(counts.values())
        )
    
    # ========== 任务操作 ==========
    
    async def cancel_task(self, session_id: str, task_id: str) -> bool:
        """
        取消任务
        
        - pending 状态：直接移除
        - running 状态：设置取消标记，由 worker 处理
        """
        task = await self.get_task(session_id, task_id)
        
        if task.status == TaskStatus.PENDING:
            # 从队列移除
            await self._queue.remove(task_id)
            
            # 更新状态
            await self._storage.update(task_id, {
                "status": TaskStatus.CANCELLED,
                "finished_at": datetime.now(timezone.utc)
            })
            
            # 发布事件
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_CANCELLED,
                task_id=task_id,
                session_id=session_id
            ))
            
            logger.info(f"Task {task_id} cancelled (was pending)")
            return True
        
        elif task.status == TaskStatus.RUNNING:
            # 设置取消标记
            await self._storage.update(task_id, {
                "cancel_requested": True
            })
            
            logger.info(f"Task {task_id} cancel requested (was running)")
            return True
        
        else:
            # 已完成/已失败/已取消，无法取消
            logger.warning(f"Cannot cancel task {task_id} in status {task.status}")
            return False
    
    async def start_task(self, session_id: str, task_id: str) -> Task:
        """
        手动启动等待中的任务（重新入队）
        """
        task = await self.get_task(session_id, task_id)

        if task.status != TaskStatus.PENDING:
            raise TaskManagerError("Only pending tasks can be started")

        await self._queue.enqueue(task, task.priority)

        await self._event_bus.publish(TaskEvent(
            event_type=EventType.TASK_QUEUED,
            task_id=task_id,
            session_id=session_id
        ))

        logger.info(f"Task {task_id} manually started (re-enqueued)")
        return await self._storage.get(task_id)

    async def retry_task(self, session_id: str, task_id: str) -> Task:
        """
        重跑任务（原地重试，不创建新任务）：
        1. 重置 task 状态为 pending，清空旧结果
        2. 尝试从死信队列恢复；若不在死信队列则直接重新入队
        """
        task = await self.get_task(session_id, task_id)
        
        if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.COMPLETED):
            raise TaskManagerError("Can only rerun failed, cancelled or completed tasks")
        
        # 重置 storage 中的状态，清空旧结果
        await self._storage.update(task_id, {
            "status": TaskStatus.PENDING,
            "retry_count": 0,
            "cancel_requested": False,
            "result": {},
            "error_message": None,
            "started_at": None,
            "finished_at": None,
        })

        # 先尝试从死信队列恢复（失败重试场景）
        recovered = await self._queue.retry_dead_letter(task_id)

        if not recovered:
            # 直接重新入队（completed / cancelled 场景，任务不在死信队列）
            fresh_task = await self._storage.get(task_id)
            await self._queue.enqueue(fresh_task, fresh_task.priority)

        await self._event_bus.publish(TaskEvent(
            event_type=EventType.TASK_RETRYING,
            task_id=task_id,
            session_id=session_id
        ))

        logger.info(f"Task {task_id} requeued for rerun (recovered_from_dead_letter={recovered})")
        return await self._storage.get(task_id)
    
    async def update_priority(
        self,
        session_id: str,
        task_id: str,
        priority: int
    ) -> bool:
        """调整任务优先级"""
        task = await self.get_task(session_id, task_id)
        
        if task.status != TaskStatus.PENDING:
            return False
        
        # 更新队列
        if await self._queue.reorder(task_id, priority):
            # 更新存储
            await self._storage.update(task_id, {"priority": priority})
            logger.info(f"Task {task_id} priority changed to {priority}")
            return True
        
        return False
    
    async def delete_task(self, session_id: str, task_id: str) -> bool:
        """删除任务"""
        task = await self.get_task(session_id, task_id)
        
        if task.status == TaskStatus.RUNNING:
            raise TaskManagerError("无法删除运行中的任务，请先取消任务")
        
        if task.status == TaskStatus.PENDING:
            await self._queue.remove(task_id)
        
        await self._storage.delete(task_id)
        logger.info(f"Task {task_id} deleted")
        return True
    
    # ========== 日志操作 ==========
    
    async def get_logs(
        self,
        session_id: str,
        task_id: str,
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        """获取任务日志"""
        # 权限检查
        await self.get_task(session_id, task_id)
        
        return await self._storage.get_logs(
            task_id, limit=limit, offset=offset, level=level
        )
    
    # ========== 内部方法（Worker 调用） ==========
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        **kwargs
    ) -> bool:
        """
        更新任务状态（Worker 调用）
        
        注：此方法不做 session 权限校验
        """
        data = {"status": status, **kwargs}
        
        if status == TaskStatus.RUNNING:
            data["started_at"] = datetime.now(timezone.utc)
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            data["finished_at"] = datetime.now(timezone.utc)
        
        result = await self._storage.update(task_id, data)
        
        if result:
            task = await self._storage.get(task_id)
            if task:
                event_type_map = {
                    TaskStatus.RUNNING: EventType.TASK_STARTED,
                    TaskStatus.COMPLETED: EventType.TASK_COMPLETED,
                    TaskStatus.FAILED: EventType.TASK_FAILED,
                    TaskStatus.CANCELLED: EventType.TASK_CANCELLED,
                }
                event_type = event_type_map.get(status)
                
                if event_type:
                    await self._event_bus.publish(TaskEvent(
                        event_type=event_type,
                        task_id=task_id,
                        session_id=task.session_id,
                        payload=kwargs
                    ))
        
        return result
    
    async def update_task_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        **extra
    ) -> bool:
        """更新任务进度（Worker 调用）"""
        percentage = int(current / total * 100) if total > 0 else 0
        
        result = await self._storage.update(task_id, {
            "progress": {
                "current": current,
                "total": total,
                "percentage": percentage,
                **extra
            },
            "last_heartbeat_at": datetime.now(timezone.utc)
        })
        
        if result:
            task = await self._storage.get(task_id)
            if task:
                await self._event_bus.publish(TaskEvent(
                    event_type=EventType.TASK_PROGRESS,
                    task_id=task_id,
                    session_id=task.session_id,
                    payload={"current": current, "total": total, "percentage": percentage}
                ))
        
        return result
    
    async def append_task_log(
        self,
        task_id: str,
        level: str,
        message: str,
        **extra
    ) -> bool:
        """追加任务日志（Worker 调用）"""
        log_entry = LogEntry(
            task_id=task_id,
            level=level,
            message=message,
            extra=extra
        )
        
        result = await self._storage.append_log(task_id, log_entry)
        
        if result:
            task = await self._storage.get(task_id)
            if task:
                await self._event_bus.publish(TaskEvent(
                    event_type=EventType.TASK_LOG,
                    task_id=task_id,
                    session_id=task.session_id,
                    payload={"level": level, "message": message}
                ))
        
        return result

