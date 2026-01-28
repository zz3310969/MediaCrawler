# 07. Worker 执行器开发文档

> 模块: 任务执行/并发控制  
> Phase: 2/3.5  
> 预估工期: 2 天  
> 产出文件:  
> - `api/services/task_executor.py`  
> - `api/worker_main.py`

---

## 一、模块职责

Worker 执行器负责：
1. **任务拉取**：从队列 reserve 任务
2. **任务执行**：调用对应平台的爬虫
3. **状态同步**：更新进度、写日志、发事件
4. **生命周期管理**：心跳续租、取消响应、超时处理
5. **并发控制**：全局/用户/平台限流

---

## 二、执行流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Worker 执行流程                                    │
└─────────────────────────────────────────────────────────────────────────────┘

            ┌──────────────────────────────────────────────────────────────┐
            │                      Worker Loop                              │
            │                                                              │
            │   ┌─────────────────────────────────────────────────────┐   │
            │   │  1. queue.reserve(timeout=30s, lease=300s)          │   │
            │   └─────────────────────────────────────────────────────┘   │
            │                              │                               │
            │                              ▼                               │
            │   ┌─────────────────────────────────────────────────────┐   │
            │   │  2. storage.update(status=RUNNING, started_at=now)  │   │
            │   └─────────────────────────────────────────────────────┘   │
            │                              │                               │
            │                              ▼                               │
            │   ┌─────────────────────────────────────────────────────┐   │
            │   │  3. 启动 heartbeat 协程                              │   │
            │   │     - 每 60s 调用 queue.heartbeat(lease_id)          │   │
            │   │     - 检查 task.cancel_requested                     │   │
            │   └─────────────────────────────────────────────────────┘   │
            │                              │                               │
            │                              ▼                               │
            │   ┌─────────────────────────────────────────────────────┐   │
            │   │  4. 执行爬虫任务                                     │   │
            │   │     - 获取平台 semaphore                             │   │
            │   │     - 调用 crawler.run()                             │   │
            │   │     - 定期更新 progress                              │   │
            │   │     - 响应取消信号                                    │   │
            │   └─────────────────────────────────────────────────────┘   │
            │                              │                               │
            │              ┌───────────────┴───────────────┐               │
            │              │                               │               │
            │              ▼                               ▼               │
            │   ┌─────────────────┐             ┌─────────────────┐       │
            │   │  成功            │             │  失败            │       │
            │   │  queue.ack()    │             │  queue.nack()   │       │
            │   │  status=DONE    │             │  status=FAILED  │       │
            │   └─────────────────┘             └─────────────────┘       │
            │                                                              │
            └──────────────────────────────────────────────────────────────┘
```

---

## 三、核心实现

### 3.1 任务执行器 (`api/services/task_executor.py`)

```python
import asyncio
import logging
import signal
from typing import Optional, Dict, Callable, Awaitable
from datetime import datetime
from contextlib import asynccontextmanager

from api.interfaces.queue import ITaskQueue
from api.interfaces.storage import ITaskStorage
from api.interfaces.event import IEventBus

from api.schemas.task import Task, TaskStatus, TaskLease
from api.schemas.event import TaskEvent, EventType, LogLevel

logger = logging.getLogger(__name__)


# 爬虫执行器类型
CrawlerFunc = Callable[[Task, "TaskContext"], Awaitable[None]]


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
        from api.schemas.event import LogEntry
        
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
        global_semaphore: asyncio.Semaphore = None,
        platform_semaphores: Dict[str, asyncio.Semaphore] = None,
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
```

### 3.2 Worker 入口 (`api/worker_main.py`)

```python
import asyncio
import signal
import logging
from typing import Dict

from api.services.factory import get_services
from api.services.task_executor import TaskExecutor, CrawlerFunc, TaskContext
from api.schemas.task import Task

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ========== 爬虫注册 ==========

async def xhs_crawler(task: Task, ctx: TaskContext) -> None:
    """小红书爬虫"""
    from media_platform.xhs import XhsCrawler
    
    await ctx.info("Starting XHS crawler...")
    
    # 创建爬虫实例
    crawler = XhsCrawler(
        keywords=task.config.keywords,
        # ... 其他配置
    )
    
    # 执行爬取
    total = task.config.max_notes
    for i, item in enumerate(crawler.crawl()):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        # 处理数据...
    
    await ctx.info("XHS crawler finished")


async def douyin_crawler(task: Task, ctx: TaskContext) -> None:
    """抖音爬虫"""
    await ctx.info("Starting Douyin crawler...")
    # ... 实现
    await ctx.info("Douyin crawler finished")


async def bilibili_crawler(task: Task, ctx: TaskContext) -> None:
    """B站爬虫"""
    await ctx.info("Starting Bilibili crawler...")
    # ... 实现
    await ctx.info("Bilibili crawler finished")


async def weibo_crawler(task: Task, ctx: TaskContext) -> None:
    """微博爬虫"""
    await ctx.info("Starting Weibo crawler...")
    # ... 实现
    await ctx.info("Weibo crawler finished")


async def wechat_crawler(task: Task, ctx: TaskContext) -> None:
    """微信爬虫"""
    await ctx.info("Starting WeChat crawler...")
    # ... 实现
    await ctx.info("WeChat crawler finished")


CRAWLERS: Dict[str, CrawlerFunc] = {
    "xhs": xhs_crawler,
    "dy": douyin_crawler,
    "bili": bilibili_crawler,
    "wb": weibo_crawler,
    "wechat": wechat_crawler,
}


# ========== 主函数 ==========

async def main():
    # 获取服务
    services = get_services()
    
    # 启动事件总线
    await services["event_bus"].start()
    
    # 创建并发控制
    global_sem = asyncio.Semaphore(10)
    platform_sems = {
        "xhs": asyncio.Semaphore(2),
        "dy": asyncio.Semaphore(2),
        "bili": asyncio.Semaphore(3),
        "wb": asyncio.Semaphore(2),
        "wechat": asyncio.Semaphore(3),
    }
    
    # 创建执行器
    executor = TaskExecutor(
        worker_id="worker-main",
        queue=services["queue"],
        storage=services["storage"],
        event_bus=services["event_bus"],
        crawlers=CRAWLERS,
        global_semaphore=global_sem,
        platform_semaphores=platform_sems
    )
    
    # 设置信号处理
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # 启动执行器
    await executor.start(worker_count=4)
    
    # 启动后台任务
    asyncio.create_task(
        lease_reclaim_task(services["queue"])
    )
    asyncio.create_task(
        delayed_promote_task(services["queue"])
    )
    
    logger.info("Worker started, waiting for tasks...")
    
    # 等待停止信号
    await stop_event.wait()
    
    # 优雅关闭
    logger.info("Shutting down...")
    await executor.stop(graceful_timeout=30)
    await services["event_bus"].stop()
    
    logger.info("Worker stopped")


async def lease_reclaim_task(queue, interval: int = 60):
    """租约回收后台任务"""
    while True:
        try:
            count = await queue.reclaim_expired_leases()
            if count > 0:
                logger.info(f"Reclaimed {count} expired leases")
        except Exception as e:
            logger.error(f"Lease reclaim error: {e}")
        await asyncio.sleep(interval)


async def delayed_promote_task(queue, interval: int = 10):
    """延迟任务提升后台任务"""
    while True:
        try:
            count = await queue.promote_delayed()
            if count > 0:
                logger.debug(f"Promoted {count} delayed tasks")
        except Exception as e:
            logger.error(f"Delayed promote error: {e}")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 四、运行方式

### 4.1 命令行启动

```bash
# 方式 1：直接运行 worker
python -m api.worker_main

# 方式 2：通过 main.py 参数
python main.py --mode worker --workers 4

# 方式 3：Docker Compose
docker-compose up worker
```

### 4.2 与 API Server 分离运行

```bash
# 终端 1：启动 API Server
python -m api.main

# 终端 2：启动 Worker
python -m api.worker_main
```

---

## 五、并发控制配置

```yaml
# config/worker.yaml

worker:
  id_prefix: "mc-worker"
  count: 4                    # 每个进程的协程数
  
  # 任务执行
  task_timeout: 3600          # 单任务超时（秒）
  heartbeat_interval: 60      # 心跳间隔（秒）
  lease_extend_seconds: 300   # 续租时长（秒）
  
  # 并发控制
  concurrency:
    global_max: 10            # 全局最大并发
    platform:
      xhs: 2
      dy: 2
      bili: 3
      wb: 2
      wechat: 3
```

---

## 六、验收标准

- [ ] Worker 可独立运行
- [ ] 任务状态正确流转
- [ ] 心跳续租工作正常
- [ ] 取消响应及时（< 心跳间隔）
- [ ] 并发控制生效
- [ ] 优雅关闭（等待当前任务完成）
- [ ] 日志/进度实时推送

---

*文档结束*

