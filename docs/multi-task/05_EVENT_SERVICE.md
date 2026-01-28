# 05. 事件服务开发文档

> 模块: 事件发布订阅  
> Phase: 2/6  
> 预估工期: 1 天  
> 产出文件:  
> - `api/services/event/asyncio_bus.py`  
> - `api/services/event/redis_bus.py`（Phase 6）

---

## 一、模块职责

事件服务负责：
1. **事件发布**：任务状态变更、进度更新、日志推送
2. **事件订阅**：按事件类型、任务、用户订阅
3. **背压控制**：防止慢消费者拖垮系统
4. **跨进程通信**（Redis 版）：API 与 Worker 之间的事件传递

---

## 二、事件流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              事件流                                          │
└─────────────────────────────────────────────────────────────────────────────┘

 Worker                           EventBus                          WebSocket Hub
    │                                │                                    │
    │  publish(TASK_STARTED)         │                                    │
    │ ─────────────────────────────► │                                    │
    │                                │                                    │
    │                                │  dispatch to subscribers           │
    │                                │ ─────────────────────────────────► │
    │                                │                                    │
    │                                │                                    │  push to clients
    │                                │                                    │ ──────────────►
    │                                │                                    │
    │  publish(TASK_PROGRESS) x N    │                                    │
    │ ─────────────────────────────► │  merge/throttle                    │
    │                                │ ─────────────────────────────────► │
    │                                │                                    │
    │  publish(TASK_LOG) x N         │                                    │
    │ ─────────────────────────────► │  sample if needed                  │
    │                                │ ─────────────────────────────────► │
    │                                │                                    │
    │  publish(TASK_COMPLETED)       │                                    │
    │ ─────────────────────────────► │                                    │
    │                                │ ─────────────────────────────────► │
    │                                │                                    │
```

---

## 三、Memory 版实现

### 3.1 核心代码 (`api/services/event/asyncio_bus.py`)

```python
import asyncio
from typing import Optional, List, Dict, Set, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import logging

from api.interfaces.event import IEventBus, EventHandler
from api.schemas.event import TaskEvent, EventType

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """订阅信息"""
    subscription_id: str
    handler: EventHandler
    event_type: Optional[EventType] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def matches(self, event: TaskEvent) -> bool:
        """判断事件是否匹配此订阅"""
        if self.event_type and event.event_type != self.event_type:
            return False
        if self.task_id and event.task_id != self.task_id:
            return False
        if self.session_id and event.session_id != self.session_id:
            return False
        return True


class AsyncioEventBus(IEventBus):
    """基于 asyncio 的内存事件总线"""
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        worker_count: int = 4,
        handler_timeout: float = 5.0,
        progress_throttle_ms: int = 500  # 进度事件节流
    ):
        # 事件队列
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # 订阅管理
        self._subscriptions: Dict[str, Subscription] = {}
        self._type_index: Dict[EventType, Set[str]] = {t: set() for t in EventType}
        self._task_index: Dict[str, Set[str]] = {}
        self._session_index: Dict[str, Set[str]] = {}
        
        # 配置
        self._worker_count = worker_count
        self._handler_timeout = handler_timeout
        self._progress_throttle_ms = progress_throttle_ms
        
        # 进度事件节流
        self._last_progress: Dict[str, datetime] = {}  # task_id -> last_time
        
        # 运行状态
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._lock = asyncio.Lock()
    
    # ========== 生命周期 ==========
    
    async def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return
        
        self._running = True
        for i in range(self._worker_count):
            worker = asyncio.create_task(
                self._dispatch_worker(f"worker-{i}")
            )
            self._workers.append(worker)
        
        logger.info(f"EventBus started with {self._worker_count} workers")
    
    async def stop(self) -> None:
        """停止事件总线"""
        self._running = False
        
        # 等待队列处理完
        await self._queue.join()
        
        # 取消 workers
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("EventBus stopped")
    
    async def _dispatch_worker(self, name: str) -> None:
        """事件分发 worker"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            try:
                await self._dispatch_event(event)
            except Exception as e:
                logger.error(f"{name} dispatch error: {e}")
            finally:
                self._queue.task_done()
    
    async def _dispatch_event(self, event: TaskEvent) -> None:
        """分发事件到匹配的订阅者"""
        # 收集匹配的订阅
        matching_subs = set()
        
        # 按类型索引
        if event.event_type in self._type_index:
            matching_subs.update(self._type_index[event.event_type])
        
        # 按任务索引
        if event.task_id in self._task_index:
            matching_subs.update(self._task_index[event.task_id])
        
        # 按会话索引
        if event.session_id in self._session_index:
            matching_subs.update(self._session_index[event.session_id])
        
        # 分发到每个订阅者
        for sub_id in matching_subs:
            sub = self._subscriptions.get(sub_id)
            if not sub or not sub.matches(event):
                continue
            
            try:
                await asyncio.wait_for(
                    sub.handler(event),
                    timeout=self._handler_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Handler timeout for subscription {sub_id}")
            except Exception as e:
                logger.error(f"Handler error for subscription {sub_id}: {e}")
    
    # ========== 发布 ==========
    
    async def publish(self, event: TaskEvent) -> bool:
        # 进度事件节流
        if event.event_type == EventType.TASK_PROGRESS:
            if not self._should_publish_progress(event.task_id):
                return True  # 跳过但返回成功
        
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
            return False
    
    async def publish_batch(self, events: List[TaskEvent]) -> int:
        count = 0
        for event in events:
            if await self.publish(event):
                count += 1
        return count
    
    def _should_publish_progress(self, task_id: str) -> bool:
        """进度事件节流判断"""
        now = datetime.utcnow()
        last = self._last_progress.get(task_id)
        
        if last is None:
            self._last_progress[task_id] = now
            return True
        
        delta_ms = (now - last).total_seconds() * 1000
        if delta_ms >= self._progress_throttle_ms:
            self._last_progress[task_id] = now
            return True
        
        return False
    
    # ========== 订阅 ==========
    
    async def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> str:
        async with self._lock:
            sub = Subscription(
                subscription_id=str(uuid.uuid4()),
                handler=handler,
                event_type=event_type
            )
            
            self._subscriptions[sub.subscription_id] = sub
            self._type_index[event_type].add(sub.subscription_id)
            
            return sub.subscription_id
    
    async def subscribe_task(
        self,
        task_id: str,
        handler: EventHandler
    ) -> str:
        async with self._lock:
            sub = Subscription(
                subscription_id=str(uuid.uuid4()),
                handler=handler,
                task_id=task_id
            )
            
            self._subscriptions[sub.subscription_id] = sub
            
            if task_id not in self._task_index:
                self._task_index[task_id] = set()
            self._task_index[task_id].add(sub.subscription_id)
            
            return sub.subscription_id
    
    async def subscribe_session(
        self,
        session_id: str,
        handler: EventHandler
    ) -> str:
        async with self._lock:
            sub = Subscription(
                subscription_id=str(uuid.uuid4()),
                handler=handler,
                session_id=session_id
            )
            
            self._subscriptions[sub.subscription_id] = sub
            
            if session_id not in self._session_index:
                self._session_index[session_id] = set()
            self._session_index[session_id].add(sub.subscription_id)
            
            return sub.subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        async with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if not sub:
                return False
            
            # 从索引移除
            if sub.event_type:
                self._type_index[sub.event_type].discard(subscription_id)
            if sub.task_id and sub.task_id in self._task_index:
                self._task_index[sub.task_id].discard(subscription_id)
            if sub.session_id and sub.session_id in self._session_index:
                self._session_index[sub.session_id].discard(subscription_id)
            
            return True
    
    # ========== 管理 ==========
    
    async def get_subscribers_count(
        self,
        event_type: Optional[EventType] = None
    ) -> int:
        if event_type:
            return len(self._type_index.get(event_type, set()))
        return len(self._subscriptions)
    
    async def clear_subscriptions(self, session_id: str) -> int:
        async with self._lock:
            sub_ids = list(self._session_index.get(session_id, set()))
            
            count = 0
            for sub_id in sub_ids:
                if await self.unsubscribe(sub_id):
                    count += 1
            
            return count
```

---

## 四、背压与限流策略

### 4.1 发送队列背压

```python
class BackpressuredHandler:
    """带背压的事件处理器（用于 WebSocket）"""
    
    def __init__(
        self,
        send_func: Callable[[TaskEvent], Awaitable[None]],
        max_queue_size: int = 256,
        drop_policy: str = "drop_oldest"  # drop_oldest / drop_newest
    ):
        self._send = send_func
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._drop_policy = drop_policy
        self._dropped_count = 0
        self._running = False
    
    async def start(self):
        self._running = True
        asyncio.create_task(self._send_loop())
    
    async def stop(self):
        self._running = False
    
    async def __call__(self, event: TaskEvent) -> None:
        """作为 EventHandler 调用"""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped_count += 1
            
            if self._drop_policy == "drop_oldest":
                # 丢弃队首
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(event)
                except asyncio.QueueEmpty:
                    pass
            # drop_newest: 直接丢弃当前事件
    
    async def _send_loop(self):
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                await self._send(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Send error: {e}")
```

### 4.2 事件合并（进度更新）

```python
class ProgressMerger:
    """进度事件合并器"""
    
    def __init__(self, flush_interval: float = 0.5):
        self._pending: Dict[str, TaskEvent] = {}  # task_id -> latest event
        self._flush_interval = flush_interval
        self._handler: Optional[EventHandler] = None
    
    def set_handler(self, handler: EventHandler):
        self._handler = handler
    
    async def handle(self, event: TaskEvent) -> None:
        if event.event_type != EventType.TASK_PROGRESS:
            # 非进度事件直接转发
            if self._handler:
                await self._handler(event)
            return
        
        # 进度事件：只保留最新
        self._pending[event.task_id] = event
    
    async def flush(self) -> None:
        """定期刷新待发送的进度"""
        if not self._handler:
            return
        
        events = list(self._pending.values())
        self._pending.clear()
        
        for event in events:
            await self._handler(event)
    
    async def run_flusher(self):
        """后台刷新任务"""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self.flush()
```

---

## 五、Redis 版实现要点（Phase 6）

### 5.1 Pub/Sub 模式

```python
class RedisEventBus(IEventBus):
    """基于 Redis Pub/Sub 的事件总线"""
    
    CHANNEL_PREFIX = "mc:events:"
    
    def __init__(self, redis: Redis):
        self._redis = redis
        self._pubsub = None
        self._handlers: Dict[str, List[EventHandler]] = {}
    
    async def start(self) -> None:
        self._pubsub = self._redis.pubsub()
        asyncio.create_task(self._listen_loop())
    
    async def publish(self, event: TaskEvent) -> bool:
        # 发布到多个频道
        channels = [
            f"{self.CHANNEL_PREFIX}type:{event.event_type.value}",
            f"{self.CHANNEL_PREFIX}task:{event.task_id}",
            f"{self.CHANNEL_PREFIX}session:{event.session_id}",
        ]
        
        data = event.json()
        async with self._redis.pipeline() as pipe:
            for channel in channels:
                pipe.publish(channel, data)
            await pipe.execute()
        
        return True
    
    async def subscribe_task(self, task_id: str, handler: EventHandler) -> str:
        channel = f"{self.CHANNEL_PREFIX}task:{task_id}"
        await self._pubsub.subscribe(channel)
        
        sub_id = str(uuid.uuid4())
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append((sub_id, handler))
        
        return sub_id
    
    async def _listen_loop(self):
        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue
            
            channel = message["channel"].decode()
            data = message["data"].decode()
            event = TaskEvent.parse_raw(data)
            
            handlers = self._handlers.get(channel, [])
            for sub_id, handler in handlers:
                await handler(event)
```

### 5.2 Streams 模式（更可靠）

```python
async def publish_to_stream(self, event: TaskEvent) -> bool:
    """使用 Streams 实现持久化事件"""
    stream_key = f"{self.CHANNEL_PREFIX}stream:{event.session_id}"
    
    await self._redis.xadd(
        stream_key,
        {"data": event.json()},
        maxlen=10000,  # 限制长度
        approximate=True
    )
    
    return True
```

---

## 六、单元测试用例

```python
import pytest
import asyncio
from api.services.event.asyncio_bus import AsyncioEventBus
from api.schemas.event import TaskEvent, EventType


@pytest.fixture
async def event_bus():
    bus = AsyncioEventBus(progress_throttle_ms=100)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.mark.asyncio
async def test_publish_subscribe(event_bus):
    received = []
    
    async def handler(event: TaskEvent):
        received.append(event)
    
    await event_bus.subscribe(EventType.TASK_STARTED, handler)
    
    event = TaskEvent(
        event_type=EventType.TASK_STARTED,
        task_id="t1",
        session_id="s1"
    )
    
    await event_bus.publish(event)
    await asyncio.sleep(0.1)  # 等待分发
    
    assert len(received) == 1
    assert received[0].task_id == "t1"


@pytest.mark.asyncio
async def test_task_subscription(event_bus):
    received = []
    
    async def handler(event: TaskEvent):
        received.append(event)
    
    await event_bus.subscribe_task("task-123", handler)
    
    # 匹配的事件
    await event_bus.publish(TaskEvent(
        event_type=EventType.TASK_PROGRESS,
        task_id="task-123",
        session_id="s1"
    ))
    
    # 不匹配的事件
    await event_bus.publish(TaskEvent(
        event_type=EventType.TASK_PROGRESS,
        task_id="other-task",
        session_id="s1"
    ))
    
    await asyncio.sleep(0.1)
    
    assert len(received) == 1


@pytest.mark.asyncio
async def test_progress_throttle(event_bus):
    received = []
    
    async def handler(event: TaskEvent):
        received.append(event)
    
    await event_bus.subscribe(EventType.TASK_PROGRESS, handler)
    
    # 快速发送多个进度事件
    for i in range(10):
        await event_bus.publish(TaskEvent(
            event_type=EventType.TASK_PROGRESS,
            task_id="t1",
            session_id="s1",
            payload={"progress": i}
        ))
    
    await asyncio.sleep(0.2)
    
    # 应该被节流
    assert len(received) < 10


@pytest.mark.asyncio
async def test_unsubscribe(event_bus):
    received = []
    
    async def handler(event: TaskEvent):
        received.append(event)
    
    sub_id = await event_bus.subscribe(EventType.TASK_COMPLETED, handler)
    
    await event_bus.publish(TaskEvent(
        event_type=EventType.TASK_COMPLETED,
        task_id="t1",
        session_id="s1"
    ))
    await asyncio.sleep(0.1)
    assert len(received) == 1
    
    # 取消订阅
    await event_bus.unsubscribe(sub_id)
    
    await event_bus.publish(TaskEvent(
        event_type=EventType.TASK_COMPLETED,
        task_id="t2",
        session_id="s1"
    ))
    await asyncio.sleep(0.1)
    assert len(received) == 1  # 不再收到
```

---

## 七、验收标准

- [ ] Memory 版所有接口实现完整
- [ ] 事件分发正确（类型/任务/会话订阅）
- [ ] 进度事件节流工作正常
- [ ] 背压处理器防止慢消费者
- [ ] 单元测试覆盖率 > 80%

---

*文档结束*

