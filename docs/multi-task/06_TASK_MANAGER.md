# 06. 任务管理器开发文档

> 模块: 任务创建/查询/协调  
> Phase: 2  
> 预估工期: 1 天  
> 产出文件:  
> - `api/services/task_manager.py`

---

## 一、模块职责

TaskManager 是任务系统的**门面（Facade）**，负责：
1. **任务创建**：幂等校验、配额检查、入队
2. **状态查询**：任务列表、详情、统计
3. **生命周期操作**：取消、重试、优先级调整
4. **协调各服务**：Queue + Storage + EventBus

---

## 二、类图

```
┌─────────────────────────────────────────────────────────────────┐
│                        TaskManager                               │
├─────────────────────────────────────────────────────────────────┤
│ - queue: ITaskQueue                                             │
│ - storage: ITaskStorage                                         │
│ - session_store: ISessionStore                                  │
│ - event_bus: IEventBus                                          │
├─────────────────────────────────────────────────────────────────┤
│ + create_task(session_id, request) -> Task                      │
│ + get_task(session_id, task_id) -> Task                         │
│ + list_tasks(session_id, filters) -> List[Task]                 │
│ + get_stats(session_id) -> TaskStats                            │
│ + cancel_task(session_id, task_id) -> bool                      │
│ + retry_task(session_id, task_id) -> Task                       │
│ + update_priority(session_id, task_id, priority) -> bool        │
│ + get_logs(session_id, task_id, ...) -> List[LogEntry]          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
        ┌─────────────────────────────────────────┐
        │                                         │
   ITaskQueue    ITaskStorage    ISessionStore   IEventBus
```

---

## 三、核心实现

### 3.1 完整代码 (`api/services/task_manager.py`)

```python
import logging
from typing import Optional, List
from datetime import datetime

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
        """
        # 1. 验证会话
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
        
        # 3. 配额检查：每日任务数
        if not await self._session_store.increment_daily_tasks(session_id):
            raise QuotaExceededError("Daily task limit exceeded")
        
        # 4. 配额检查：并发任务数
        running_count = await self._get_running_count(session_id)
        if running_count >= session.quota.max_concurrent_tasks:
            # 回滚每日计数
            # 注：实际应该用事务，这里简化处理
            raise QuotaExceededError("Concurrent task limit exceeded")
        
        # 5. 创建任务对象
        task = Task(
            session_id=session_id,
            task_name=request.task_name,
            config=request.config,
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            idempotency_key=request.idempotency_key
        )
        
        # 6. 持久化
        try:
            await self._storage.create(task)
        except ValueError as e:
            raise DuplicateTaskError(str(e))
        
        # 7. 入队
        if request.scheduled_at and request.scheduled_at > datetime.utcnow():
            # 延迟任务
            delay = (request.scheduled_at - datetime.utcnow()).total_seconds()
            await self._queue.enqueue_delayed(task, int(delay))
        else:
            await self._queue.enqueue(task, task.priority)
        
        # 8. 发布事件
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
    
    async def _get_running_count(self, session_id: str) -> int:
        """获取用户运行中的任务数"""
        tasks = await self._storage.get_by_session(
            session_id, status=TaskStatus.RUNNING
        )
        return len(tasks)
    
    # ========== 查询任务 ==========
    
    async def get_task(self, session_id: str, task_id: str) -> Task:
        """
        获取任务详情
        
        Raises:
            TaskNotFoundError: 任务不存在
            PermissionDeniedError: 无权访问
        """
        task = await self._storage.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        
        if task.session_id != session_id:
            raise PermissionDeniedError("Permission denied")
        
        return task
    
    async def list_tasks(
        self,
        session_id: str,
        request: TaskListRequest
    ) -> List[Task]:
        """获取任务列表"""
        offset = (request.page - 1) * request.page_size
        
        return await self._storage.get_by_session(
            session_id,
            status=request.status,
            platform=request.platform,
            limit=request.page_size,
            offset=offset
        )
    
    async def count_tasks(self, session_id: str) -> int:
        """获取任务总数"""
        counts = await self._storage.count_by_status(session_id)
        return sum(counts.values())
    
    async def get_stats(self, session_id: str) -> TaskStatsResponse:
        """获取任务统计"""
        counts = await self._storage.count_by_status(session_id)
        
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
                "finished_at": datetime.utcnow()
            })
            
            # 发布事件
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_CANCELLED,
                task_id=task_id,
                session_id=session_id
            ))
            
            return True
        
        elif task.status == TaskStatus.RUNNING:
            # 设置取消标记
            await self._storage.update(task_id, {
                "cancel_requested": True
            })
            
            # 从队列移除（会触发 worker 的取消逻辑）
            await self._queue.remove(task_id)
            
            return True
        
        else:
            # 已完成/已失败/已取消，无法取消
            return False
    
    async def retry_task(self, session_id: str, task_id: str) -> Task:
        """
        重试失败的任务
        
        - 创建一个新任务（保留原配置）
        - 或者将死信任务重新入队
        """
        task = await self.get_task(session_id, task_id)
        
        if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise TaskManagerError("Can only retry failed or cancelled tasks")
        
        # 方案1：从死信队列恢复
        if await self._queue.retry_dead_letter(task_id):
            await self._storage.update(task_id, {
                "status": TaskStatus.PENDING,
                "retry_count": 0,
                "result": {}
            })
            
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_RETRYING,
                task_id=task_id,
                session_id=session_id
            ))
            
            return await self._storage.get(task_id)
        
        # 方案2：创建新任务
        new_task = Task(
            session_id=session_id,
            task_name=f"{task.task_name} (retry)",
            config=task.config,
            priority=task.priority
        )
        
        await self._storage.create(new_task)
        await self._queue.enqueue(new_task, new_task.priority)
        
        return new_task
    
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
            return True
        
        return False
    
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
            data["started_at"] = datetime.utcnow()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            data["finished_at"] = datetime.utcnow()
        
        result = await self._storage.update(task_id, data)
        
        if result:
            task = await self._storage.get(task_id)
            if task:
                event_type = {
                    TaskStatus.RUNNING: EventType.TASK_STARTED,
                    TaskStatus.COMPLETED: EventType.TASK_COMPLETED,
                    TaskStatus.FAILED: EventType.TASK_FAILED,
                    TaskStatus.CANCELLED: EventType.TASK_CANCELLED,
                }.get(status)
                
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
            "last_heartbeat_at": datetime.utcnow()
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
```

---

## 四、工厂函数

### 4.1 服务创建 (`api/services/factory.py`)

```python
from typing import Literal
from api.services.task_manager import TaskManager
from api.services.queue.memory import MemoryTaskQueue
from api.services.storage.memory import MemoryTaskStorage
from api.services.session.memory import MemorySessionStore
from api.services.event.asyncio_bus import AsyncioEventBus

# Redis 版（Phase 6）
# from api.services.queue.redis import RedisTaskQueue
# from api.services.storage.redis import RedisTaskStorage
# from api.services.session.redis import RedisSessionStore
# from api.services.event.redis_bus import RedisEventBus


def create_services(
    backend: Literal["memory", "redis"] = "memory",
    redis_url: str = None
) -> dict:
    """
    创建服务实例
    
    Returns:
        {
            "queue": ITaskQueue,
            "storage": ITaskStorage,
            "session_store": ISessionStore,
            "event_bus": IEventBus,
            "task_manager": TaskManager
        }
    """
    if backend == "memory":
        queue = MemoryTaskQueue()
        storage = MemoryTaskStorage()
        session_store = MemorySessionStore()
        event_bus = AsyncioEventBus()
    
    elif backend == "redis":
        # Phase 6 实现
        raise NotImplementedError("Redis backend not implemented yet")
    
    else:
        raise ValueError(f"Unknown backend: {backend}")
    
    task_manager = TaskManager(
        queue=queue,
        storage=storage,
        session_store=session_store,
        event_bus=event_bus
    )
    
    return {
        "queue": queue,
        "storage": storage,
        "session_store": session_store,
        "event_bus": event_bus,
        "task_manager": task_manager
    }


# 全局服务实例（单例）
_services = None


def get_services():
    global _services
    if _services is None:
        _services = create_services()
    return _services


def get_task_manager() -> TaskManager:
    return get_services()["task_manager"]
```

---

## 五、单元测试用例

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from api.services.task_manager import (
    TaskManager, QuotaExceededError, TaskNotFoundError
)
from api.schemas.task import TaskCreateRequest, TaskConfig
from api.schemas.session import Session, SessionQuota


@pytest.fixture
def mock_services():
    return {
        "queue": AsyncMock(),
        "storage": AsyncMock(),
        "session_store": AsyncMock(),
        "event_bus": AsyncMock()
    }


@pytest.fixture
def task_manager(mock_services):
    return TaskManager(**mock_services)


@pytest.fixture
def sample_session():
    return Session(
        session_id="test-session",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        quota=SessionQuota(max_concurrent_tasks=3, max_daily_tasks=10)
    )


@pytest.mark.asyncio
async def test_create_task_success(task_manager, mock_services, sample_session):
    mock_services["session_store"].get.return_value = sample_session
    mock_services["session_store"].increment_daily_tasks.return_value = True
    mock_services["storage"].find_by_idempotency_key.return_value = None
    mock_services["storage"].get_by_session.return_value = []
    
    request = TaskCreateRequest(
        config=TaskConfig(platform="xhs", crawler_type="search")
    )
    
    task = await task_manager.create_task("test-session", request)
    
    assert task.session_id == "test-session"
    mock_services["storage"].create.assert_called_once()
    mock_services["queue"].enqueue.assert_called_once()


@pytest.mark.asyncio
async def test_create_task_quota_exceeded(task_manager, mock_services, sample_session):
    sample_session.quota.max_concurrent_tasks = 1
    mock_services["session_store"].get.return_value = sample_session
    mock_services["session_store"].increment_daily_tasks.return_value = True
    mock_services["storage"].find_by_idempotency_key.return_value = None
    mock_services["storage"].get_by_session.return_value = [MagicMock()]  # 1 个运行中
    
    request = TaskCreateRequest(
        config=TaskConfig(platform="xhs", crawler_type="search")
    )
    
    with pytest.raises(QuotaExceededError):
        await task_manager.create_task("test-session", request)


@pytest.mark.asyncio
async def test_idempotency_key(task_manager, mock_services, sample_session):
    existing_task = MagicMock()
    mock_services["session_store"].get.return_value = sample_session
    mock_services["storage"].find_by_idempotency_key.return_value = existing_task
    
    request = TaskCreateRequest(
        config=TaskConfig(platform="xhs", crawler_type="search"),
        idempotency_key="unique-key"
    )
    
    task = await task_manager.create_task("test-session", request)
    
    assert task == existing_task
    mock_services["storage"].create.assert_not_called()


@pytest.mark.asyncio
async def test_get_task_permission_denied(task_manager, mock_services):
    task = MagicMock()
    task.session_id = "other-session"
    mock_services["storage"].get.return_value = task
    
    with pytest.raises(PermissionDeniedError):
        await task_manager.get_task("my-session", "task-123")
```

---

## 六、验收标准

- [ ] 所有公开方法实现完整
- [ ] 幂等键去重功能正常
- [ ] 配额检查正确（每日/并发）
- [ ] 权限校验完整（task.session_id 校验）
- [ ] 事件发布正确
- [ ] 单元测试覆盖率 > 85%

---

*文档结束*

