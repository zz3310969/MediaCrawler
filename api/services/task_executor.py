"""
任务执行器
"""
import asyncio
import logging
from typing import Optional, Dict, Callable, Awaitable
from datetime import datetime

from api.interfaces.queue import ITaskQueue
from api.interfaces.storage import ITaskStorage
from api.interfaces.event import IEventBus

from api.schemas.task import Task, TaskStatus, TaskLease
from api.schemas.event import TaskEvent, EventType, LogEntry

logger = logging.getLogger(__name__)


# 爬虫执行器类型
CrawlerFunc = Callable[["Task", "TaskContext"], Awaitable[None]]


class TaskContext:
    """任务执行上下文（提供给爬虫的接口）"""
    
    def __init__(
        self,
        task: Task,
        storage: ITaskStorage,
        event_bus: IEventBus,
        cancel_event: asyncio.Event
    ):
        self._task = task
        self._storage = storage
        self._event_bus = event_bus
        self._cancel_event = cancel_event
    
    @property
    def task_id(self) -> str:
        return self._task.task_id
    
    @property
    def session_id(self) -> str:
        return self._task.session_id
    
    @property
    def config(self):
        return self._task.config
    
    @property
    def task(self) -> Task:
        return self._task
    
    def is_cancelled(self) -> bool:
        """检查任务是否被取消"""
        return self._cancel_event.is_set()
    
    def check_cancelled(self) -> None:
        """检查并抛出取消异常"""
        if self.is_cancelled():
            raise asyncio.CancelledError("Task cancelled by user")
    
    async def update_progress(
        self,
        current: int,
        total: int,
        **extra
    ) -> None:
        """更新进度"""
        self.check_cancelled()
        
        percentage = int(current / total * 100) if total > 0 else 0
        
        await self._storage.update(self._task.task_id, {
            "progress": {
                "current": current,
                "total": total,
                "percentage": percentage,
                **extra
            }
        })
        
        await self._event_bus.publish(TaskEvent(
            event_type=EventType.TASK_PROGRESS,
            task_id=self._task.task_id,
            session_id=self._task.session_id,
            payload={"current": current, "total": total, "percentage": percentage}
        ))
    
    async def log(self, level: str, message: str, **extra) -> None:
        """写日志"""
        log_entry = LogEntry(
            task_id=self._task.task_id,
            level=level,
            message=message,
            extra=extra
        )
        
        await self._storage.append_log(self._task.task_id, log_entry)
        
        await self._event_bus.publish(TaskEvent(
            event_type=EventType.TASK_LOG,
            task_id=self._task.task_id,
            session_id=self._task.session_id,
            payload={"level": level, "message": message}
        ))
    
    async def debug(self, message: str, **extra):
        await self.log("debug", message, **extra)
    
    async def info(self, message: str, **extra):
        await self.log("info", message, **extra)
    
    async def warn(self, message: str, **extra):
        await self.log("warn", message, **extra)
    
    async def error(self, message: str, **extra):
        await self.log("error", message, **extra)


class TaskExecutor:
    """任务执行器"""
    
    def __init__(
        self,
        worker_id: str,
        queue: ITaskQueue,
        storage: ITaskStorage,
        event_bus: IEventBus,
        crawlers: Dict[str, CrawlerFunc],
        # 并发控制
        global_semaphore: Optional[asyncio.Semaphore] = None,
        platform_semaphores: Optional[Dict[str, asyncio.Semaphore]] = None,
        # 配置
        heartbeat_interval: int = 60,
        lease_extend_seconds: int = 300,
        task_timeout: int = 3600
    ):
        self._worker_id = worker_id
        self._queue = queue
        self._storage = storage
        self._event_bus = event_bus
        self._crawlers = crawlers
        
        # 并发控制
        self._global_sem = global_semaphore or asyncio.Semaphore(10)
        self._platform_sems = platform_semaphores or {}
        
        # 配置
        self._heartbeat_interval = heartbeat_interval
        self._lease_extend = lease_extend_seconds
        self._task_timeout = task_timeout
        
        # 运行状态
        self._running = False
        self._current_tasks: Dict[str, asyncio.Task] = {}
    
    async def start(self, worker_count: int = 1) -> None:
        """启动 worker"""
        self._running = True
        
        tasks = []
        for i in range(worker_count):
            task = asyncio.create_task(
                self._worker_loop(f"{self._worker_id}-{i}")
            )
            tasks.append(task)
            self._current_tasks[f"worker-{i}"] = task
        
        logger.info(f"TaskExecutor started with {worker_count} workers")
    
    async def stop(self, graceful_timeout: float = 30.0) -> None:
        """停止 worker"""
        self._running = False
        
        # 等待当前任务完成
        if self._current_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._current_tasks.values(), return_exceptions=True),
                    timeout=graceful_timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Graceful shutdown timeout, cancelling tasks")
                for task in self._current_tasks.values():
                    task.cancel()
        
        self._current_tasks.clear()
        logger.info("TaskExecutor stopped")
    
    async def _worker_loop(self, name: str) -> None:
        """Worker 主循环"""
        logger.info(f"Worker {name} started")
        
        while self._running:
            try:
                # 获取全局信号量
                async with self._global_sem:
                    # 从队列获取任务
                    lease = await self._queue.reserve(
                        worker_id=self._worker_id,
                        timeout=30.0,
                        lease_seconds=self._lease_extend
                    )
                    
                    if lease is None:
                        continue
                    
                    # 执行任务
                    await self._execute_task(name, lease)
            
            except asyncio.CancelledError:
                logger.info(f"Worker {name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {name} error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"Worker {name} stopped")
    
    async def _execute_task(self, worker_name: str, lease: TaskLease) -> None:
        """执行单个任务"""
        task = await self._storage.get(lease.task_id)
        if not task:
            logger.warning(f"Task not found: {lease.task_id}")
            await self._queue.ack(lease.lease_id)
            return
        
        # 取消事件
        cancel_event = asyncio.Event()
        
        # 创建上下文
        context = TaskContext(
            task=task,
            storage=self._storage,
            event_bus=self._event_bus,
            cancel_event=cancel_event
        )
        
        # 启动心跳
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(lease, task, cancel_event)
        )
        
        try:
            # 更新状态为运行中
            await self._storage.update(task.task_id, {
                "status": TaskStatus.RUNNING,
                "started_at": datetime.utcnow(),
                "metadata": {"execution_node": self._worker_id}
            })
            
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_STARTED,
                task_id=task.task_id,
                session_id=task.session_id
            ))
            
            await context.info(f"Task started on worker {worker_name}")
            
            # 获取平台信号量
            platform = task.config.platform
            platform_sem = self._platform_sems.get(platform)
            
            if platform_sem:
                async with platform_sem:
                    await self._run_crawler(task, context)
            else:
                await self._run_crawler(task, context)
            
            # 执行成功
            await self._queue.ack(lease.lease_id)
            
            await self._storage.update(task.task_id, {
                "status": TaskStatus.COMPLETED,
                "finished_at": datetime.utcnow(),
                "result": {"success": True}
            })
            
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_COMPLETED,
                task_id=task.task_id,
                session_id=task.session_id
            ))
            
            await context.info("Task completed successfully")
            logger.info(f"Task {task.task_id} completed")
        
        except asyncio.CancelledError:
            # 任务被取消
            await self._queue.nack(lease.lease_id, "Cancelled by user", retry=False)
            
            await self._storage.update(task.task_id, {
                "status": TaskStatus.CANCELLED,
                "finished_at": datetime.utcnow()
            })
            
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_CANCELLED,
                task_id=task.task_id,
                session_id=task.session_id
            ))
            
            await context.info("Task cancelled")
            logger.info(f"Task {task.task_id} cancelled")
        
        except Exception as e:
            # 执行失败
            error_msg = str(e)
            should_retry = not isinstance(e, (ValueError, KeyError))  # 非致命错误才重试
            
            await self._queue.nack(lease.lease_id, error_msg, retry=should_retry)
            
            await self._storage.update(task.task_id, {
                "status": TaskStatus.FAILED,
                "finished_at": datetime.utcnow(),
                "result": {"success": False, "error_message": error_msg}
            })
            
            await self._event_bus.publish(TaskEvent(
                event_type=EventType.TASK_FAILED,
                task_id=task.task_id,
                session_id=task.session_id,
                payload={"error": error_msg}
            ))
            
            await context.error(f"Task failed: {error_msg}")
            logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)
        
        finally:
            # 停止心跳
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _run_crawler(self, task: Task, context: TaskContext) -> None:
        """运行爬虫"""
        platform = task.config.platform
        crawler = self._crawlers.get(platform)
        
        if not crawler:
            raise ValueError(f"Unknown platform: {platform}")
        
        # 带超时执行
        await asyncio.wait_for(
            crawler(task, context),
            timeout=self._task_timeout
        )
    
    async def _heartbeat_loop(
        self,
        lease: TaskLease,
        task: Task,
        cancel_event: asyncio.Event
    ) -> None:
        """心跳循环"""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            
            try:
                # 续租
                await self._queue.heartbeat(lease.lease_id, self._lease_extend)
                
                # 检查取消标记
                fresh_task = await self._storage.get(task.task_id)
                if fresh_task and fresh_task.cancel_requested:
                    cancel_event.set()
                    logger.info(f"Task {task.task_id} cancel requested")
                
                # 更新心跳时间
                await self._storage.update(task.task_id, {
                    "last_heartbeat_at": datetime.utcnow()
                })
            
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

