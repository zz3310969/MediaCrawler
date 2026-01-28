# 03. 队列服务开发文档

> 模块: 任务排队/调度  
> Phase: 2/6  
> 预估工期: 1.5 天  
> 产出文件:  
> - `api/services/queue/memory.py`  
> - `api/services/queue/redis.py`（Phase 6）

---

## 一、模块职责

队列服务负责：
1. **任务入队**：按优先级排序入队
2. **任务出队**：reserve/lease 语义，支持超时回收
3. **确认机制**：ack/nack/heartbeat 保证可靠投递
4. **延迟任务**：定时执行支持
5. **死信队列**：失败任务隔离与重试

---

## 二、核心概念

### 2.1 任务生命周期

```
                    ┌─────────────────────────────────────────┐
                    │              Queue 内部状态              │
                    └─────────────────────────────────────────┘
                    
  enqueue()                                                    ack()
    │                                                           │
    ▼                                                           ▼
┌─────────┐    reserve()    ┌─────────────┐    执行完成    ┌─────────┐
│  READY  │ ──────────────► │ PROCESSING  │ ─────────────► │ REMOVED │
└─────────┘                 └─────────────┘                └─────────┘
    ▲                              │
    │                              │ nack(retry=true)
    │         lease 过期           │
    │  ◄───────────────────────────┤
    │                              │
    │                              │ nack(retry=false)
    │                              ▼
    │                       ┌─────────────┐
    └────── retry ◄──────── │ DEAD_LETTER │
                            └─────────────┘
```

### 2.2 Lease（租约）机制

```
Worker-1: reserve() ──► 获得 lease (task_id=T1, expires_at=10:05:00)
                        │
                        │ 执行任务...
                        │
                        │ 10:03:00 heartbeat() ──► 续租到 10:08:00
                        │
                        │ 10:06:00 执行完成
                        │
Worker-1: ack(lease_id) ──► 确认完成，从 processing 移除


Worker-2: reserve() ──► 获得 lease (task_id=T2, expires_at=10:05:00)
                        │
                        │ 执行任务...
                        │
                        X 10:04:00 Worker-2 崩溃
                        
Scheduler: reclaim_expired_leases() @ 10:06:00
                        │
                        ▼
                    T2 回到 READY 队列，等待其他 Worker 接手
```

---

## 三、Memory 版实现

### 3.1 核心代码 (`api/services/queue/memory.py`)

```python
import asyncio
import heapq
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

from api.interfaces.queue import ITaskQueue, QueueStats
from api.schemas.task import Task, TaskLease


@dataclass(order=True)
class PriorityItem:
    """优先级队列项"""
    priority_score: float  # 越小越优先：-priority * 1000000 + timestamp
    task_id: str = field(compare=False)
    task: Task = field(compare=False)


class MemoryTaskQueue(ITaskQueue):
    """内存版任务队列"""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_lease_seconds: int = 300,
        max_retries: int = 3
    ):
        # 就绪队列（优先级堆）
        self._ready: List[PriorityItem] = []
        self._ready_index: Dict[str, PriorityItem] = {}
        
        # 处理中（租约）
        self._processing: Dict[str, TaskLease] = {}  # lease_id -> lease
        self._task_to_lease: Dict[str, str] = {}     # task_id -> lease_id
        
        # 延迟队列
        self._delayed: Dict[str, Tuple[datetime, Task]] = {}
        
        # 死信队列
        self._dead_letters: List[Task] = []
        
        # 任务详情
        self._tasks: Dict[str, Task] = {}
        
        # 配置
        self._max_size = max_size
        self._default_lease_seconds = default_lease_seconds
        self._max_retries = max_retries
        
        # 锁
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
    
    def _priority_score(self, task: Task) -> float:
        """计算优先级分数（越小越优先）"""
        # priority 越大越优先，所以取负数
        # 同优先级按创建时间排序
        return -task.priority * 1000000 + task.created_at.timestamp()
    
    # ========== 基础操作 ==========
    
    async def enqueue(self, task: Task, priority: Optional[int] = None) -> bool:
        async with self._lock:
            if len(self._ready) >= self._max_size:
                return False
            
            if priority is not None:
                task.priority = priority
            
            # 存储任务
            self._tasks[task.task_id] = task
            
            # 入队
            item = PriorityItem(
                priority_score=self._priority_score(task),
                task_id=task.task_id,
                task=task
            )
            heapq.heappush(self._ready, item)
            self._ready_index[task.task_id] = item
            
            # 通知等待的 worker
            self._not_empty.notify()
            
            return True
    
    async def reserve(
        self,
        worker_id: str,
        timeout: float = 30.0,
        lease_seconds: int = None
    ) -> Optional[TaskLease]:
        lease_seconds = lease_seconds or self._default_lease_seconds
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        
        async with self._not_empty:
            while True:
                # 先处理到期的延迟任务
                await self._promote_delayed_locked()
                
                # 尝试获取任务
                if self._ready:
                    item = heapq.heappop(self._ready)
                    del self._ready_index[item.task_id]
                    
                    # 创建租约
                    lease = TaskLease(
                        lease_id=str(uuid.uuid4()),
                        task_id=item.task_id,
                        worker_id=worker_id,
                        expires_at=datetime.utcnow() + timedelta(seconds=lease_seconds)
                    )
                    
                    self._processing[lease.lease_id] = lease
                    self._task_to_lease[item.task_id] = lease.lease_id
                    
                    return lease
                
                # 计算剩余等待时间
                now = datetime.utcnow()
                if now >= deadline:
                    return None
                
                remaining = (deadline - now).total_seconds()
                try:
                    await asyncio.wait_for(
                        self._not_empty.wait(),
                        timeout=remaining
                    )
                except asyncio.TimeoutError:
                    return None
    
    async def peek(self) -> Optional[Task]:
        async with self._lock:
            if self._ready:
                return self._ready[0].task
            return None
    
    async def remove(self, task_id: str) -> bool:
        async with self._lock:
            # 从就绪队列移除
            if task_id in self._ready_index:
                item = self._ready_index.pop(task_id)
                self._ready.remove(item)
                heapq.heapify(self._ready)
                self._tasks.pop(task_id, None)
                return True
            
            # 从处理中移除（设置取消标记）
            if task_id in self._task_to_lease:
                task = self._tasks.get(task_id)
                if task:
                    task.cancel_requested = True
                return True
            
            # 从延迟队列移除
            if task_id in self._delayed:
                del self._delayed[task_id]
                self._tasks.pop(task_id, None)
                return True
            
            return False
    
    async def size(self) -> int:
        return len(self._ready)
    
    # ========== 确认与回收 ==========
    
    async def ack(self, lease_id: str) -> bool:
        async with self._lock:
            lease = self._processing.pop(lease_id, None)
            if not lease:
                return False
            
            self._task_to_lease.pop(lease.task_id, None)
            self._tasks.pop(lease.task_id, None)
            return True
    
    async def nack(self, lease_id: str, reason: str, retry: bool = True) -> bool:
        async with self._lock:
            lease = self._processing.pop(lease_id, None)
            if not lease:
                return False
            
            self._task_to_lease.pop(lease.task_id, None)
            task = self._tasks.get(lease.task_id)
            
            if not task:
                return False
            
            if retry and task.retry_count < self._max_retries:
                # 重试：增加重试计数，重新入队
                task.retry_count += 1
                item = PriorityItem(
                    priority_score=self._priority_score(task),
                    task_id=task.task_id,
                    task=task
                )
                heapq.heappush(self._ready, item)
                self._ready_index[task.task_id] = item
                self._not_empty.notify()
            else:
                # 移入死信队列
                task.result.error_message = reason
                self._dead_letters.append(task)
                self._tasks.pop(lease.task_id, None)
            
            return True
    
    async def heartbeat(self, lease_id: str, extend_seconds: int = 300) -> bool:
        async with self._lock:
            lease = self._processing.get(lease_id)
            if not lease:
                return False
            
            lease.expires_at = datetime.utcnow() + timedelta(seconds=extend_seconds)
            return True
    
    async def reclaim_expired_leases(self) -> int:
        async with self._lock:
            now = datetime.utcnow()
            expired = [
                (lid, lease) for lid, lease in self._processing.items()
                if lease.expires_at < now
            ]
            
            count = 0
            for lease_id, lease in expired:
                del self._processing[lease_id]
                self._task_to_lease.pop(lease.task_id, None)
                
                task = self._tasks.get(lease.task_id)
                if task and task.retry_count < self._max_retries:
                    task.retry_count += 1
                    item = PriorityItem(
                        priority_score=self._priority_score(task),
                        task_id=task.task_id,
                        task=task
                    )
                    heapq.heappush(self._ready, item)
                    self._ready_index[task.task_id] = item
                    count += 1
                elif task:
                    task.result.error_message = "Lease expired (worker crashed or timeout)"
                    self._dead_letters.append(task)
                    self._tasks.pop(task.task_id, None)
            
            if count > 0:
                self._not_empty.notify_all()
            
            return count
    
    # ========== 优先级 ==========
    
    async def reorder(self, task_id: str, new_priority: int) -> bool:
        async with self._lock:
            if task_id not in self._ready_index:
                return False
            
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            # 移除旧项
            old_item = self._ready_index.pop(task_id)
            self._ready.remove(old_item)
            
            # 更新优先级
            task.priority = new_priority
            
            # 重新入队
            item = PriorityItem(
                priority_score=self._priority_score(task),
                task_id=task_id,
                task=task
            )
            heapq.heappush(self._ready, item)
            self._ready_index[task_id] = item
            heapq.heapify(self._ready)
            
            return True
    
    # ========== 延迟任务 ==========
    
    async def enqueue_delayed(self, task: Task, delay_seconds: int) -> bool:
        async with self._lock:
            ready_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
            self._delayed[task.task_id] = (ready_time, task)
            self._tasks[task.task_id] = task
            return True
    
    async def get_delayed_count(self) -> int:
        return len(self._delayed)
    
    async def promote_delayed(self) -> int:
        async with self._lock:
            return await self._promote_delayed_locked()
    
    async def _promote_delayed_locked(self) -> int:
        """内部方法：提升到期的延迟任务（已持有锁）"""
        now = datetime.utcnow()
        promoted = []
        
        for task_id, (ready_time, task) in list(self._delayed.items()):
            if ready_time <= now:
                promoted.append(task_id)
                item = PriorityItem(
                    priority_score=self._priority_score(task),
                    task_id=task_id,
                    task=task
                )
                heapq.heappush(self._ready, item)
                self._ready_index[task_id] = item
        
        for task_id in promoted:
            del self._delayed[task_id]
        
        if promoted:
            self._not_empty.notify_all()
        
        return len(promoted)
    
    # ========== 死信队列 ==========
    
    async def move_to_dead_letter(self, task_id: str, reason: str) -> bool:
        async with self._lock:
            task = self._tasks.pop(task_id, None)
            if not task:
                return False
            
            # 从各队列移除
            if task_id in self._ready_index:
                item = self._ready_index.pop(task_id)
                self._ready.remove(item)
                heapq.heapify(self._ready)
            
            if task_id in self._task_to_lease:
                lease_id = self._task_to_lease.pop(task_id)
                self._processing.pop(lease_id, None)
            
            if task_id in self._delayed:
                del self._delayed[task_id]
            
            task.result.error_message = reason
            self._dead_letters.append(task)
            return True
    
    async def get_dead_letters(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        async with self._lock:
            tasks = self._dead_letters
            if session_id:
                tasks = [t for t in tasks if t.session_id == session_id]
            return tasks[:limit]
    
    async def retry_dead_letter(self, task_id: str) -> bool:
        async with self._lock:
            for i, task in enumerate(self._dead_letters):
                if task.task_id == task_id:
                    self._dead_letters.pop(i)
                    task.retry_count = 0
                    task.result.error_message = None
                    
                    self._tasks[task_id] = task
                    item = PriorityItem(
                        priority_score=self._priority_score(task),
                        task_id=task_id,
                        task=task
                    )
                    heapq.heappush(self._ready, item)
                    self._ready_index[task_id] = item
                    self._not_empty.notify()
                    return True
            return False
    
    # ========== 监控 ==========
    
    async def get_stats(self) -> QueueStats:
        async with self._lock:
            return QueueStats(
                ready_count=len(self._ready),
                processing_count=len(self._processing),
                delayed_count=len(self._delayed),
                dead_letter_count=len(self._dead_letters)
            )
    
    async def health_check(self) -> bool:
        return True
```

---

## 四、Redis 版实现要点（Phase 6）

### 4.1 方案 A：Redis Streams（推荐）

```python
class RedisTaskQueue(ITaskQueue):
    """Redis Streams 版任务队列"""
    
    STREAM_KEY = "task_stream"
    GROUP_NAME = "workers"
    
    async def enqueue(self, task: Task, priority: Optional[int] = None) -> bool:
        # XADD task_stream * task_id xxx data xxx
        await self._redis.xadd(
            self.STREAM_KEY,
            {"task_id": task.task_id, "data": task.json()}
        )
        return True
    
    async def reserve(self, worker_id: str, timeout: float = 30.0, **kwargs) -> Optional[TaskLease]:
        # XREADGROUP GROUP workers worker_id COUNT 1 BLOCK 30000 STREAMS task_stream >
        messages = await self._redis.xreadgroup(
            self.GROUP_NAME,
            worker_id,
            {self.STREAM_KEY: ">"},
            count=1,
            block=int(timeout * 1000)
        )
        
        if not messages:
            return None
        
        # 解析消息，创建租约
        stream_id = messages[0][1][0][0]
        data = messages[0][1][0][1]
        
        return TaskLease(
            lease_id=stream_id,  # 使用 stream ID 作为 lease ID
            task_id=data["task_id"],
            worker_id=worker_id,
            expires_at=datetime.utcnow() + timedelta(seconds=300)
        )
    
    async def ack(self, lease_id: str) -> bool:
        # XACK task_stream workers {stream_id}
        await self._redis.xack(self.STREAM_KEY, self.GROUP_NAME, lease_id)
        return True
    
    async def reclaim_expired_leases(self) -> int:
        # XPENDING + XCLAIM
        pending = await self._redis.xpending(self.STREAM_KEY, self.GROUP_NAME)
        # 找出超时的消息，使用 XCLAIM 重新分配
        # ...
```

### 4.2 方案 B：ZSET + Processing（Lua 原子）

```lua
-- reserve.lua
-- KEYS[1]: ready queue (ZSET)
-- KEYS[2]: processing queue (ZSET)
-- KEYS[3]: task hash prefix
-- ARGV[1]: worker_id
-- ARGV[2]: lease_seconds
-- ARGV[3]: current_time

local task_id = redis.call('ZPOPMIN', KEYS[1])
if not task_id[1] then
    return nil
end

local lease_id = redis.call('INCR', 'lease_counter')
local expire_at = ARGV[3] + ARGV[2]

-- 移入 processing
redis.call('ZADD', KEYS[2], expire_at, task_id[1])

-- 存储租约信息
redis.call('HSET', 'lease:' .. lease_id,
    'task_id', task_id[1],
    'worker_id', ARGV[1],
    'expires_at', expire_at
)

return {lease_id, task_id[1]}
```

---

## 五、后台调度任务

### 5.1 租约回收

```python
async def lease_reclaim_task(queue: ITaskQueue, interval: int = 60):
    """后台回收过期租约"""
    while True:
        try:
            count = await queue.reclaim_expired_leases()
            if count > 0:
                logger.info(f"Reclaimed {count} expired leases")
        except Exception as e:
            logger.error(f"Lease reclaim error: {e}")
        
        await asyncio.sleep(interval)
```

### 5.2 延迟任务提升

```python
async def delayed_promote_task(queue: ITaskQueue, interval: int = 10):
    """后台提升到期的延迟任务"""
    while True:
        try:
            count = await queue.promote_delayed()
            if count > 0:
                logger.debug(f"Promoted {count} delayed tasks")
        except Exception as e:
            logger.error(f"Delayed promote error: {e}")
        
        await asyncio.sleep(interval)
```

---

## 六、单元测试用例

```python
import pytest
import asyncio
from api.services.queue.memory import MemoryTaskQueue
from api.schemas.task import Task, TaskConfig, TaskPriority


@pytest.fixture
def queue():
    return MemoryTaskQueue(max_retries=2)


@pytest.fixture
def sample_task():
    return Task(
        session_id="test-session",
        config=TaskConfig(platform="xhs", crawler_type="search")
    )


@pytest.mark.asyncio
async def test_enqueue_dequeue(queue, sample_task):
    await queue.enqueue(sample_task)
    assert await queue.size() == 1
    
    lease = await queue.reserve("worker-1", timeout=1.0)
    assert lease is not None
    assert lease.task_id == sample_task.task_id


@pytest.mark.asyncio
async def test_priority_order(queue):
    low = Task(session_id="s", config=TaskConfig(platform="xhs", crawler_type="search"), priority=TaskPriority.LOW)
    high = Task(session_id="s", config=TaskConfig(platform="xhs", crawler_type="search"), priority=TaskPriority.HIGH)
    
    await queue.enqueue(low)
    await queue.enqueue(high)
    
    lease = await queue.reserve("w", timeout=1.0)
    assert lease.task_id == high.task_id  # 高优先级先出


@pytest.mark.asyncio
async def test_ack_removes_task(queue, sample_task):
    await queue.enqueue(sample_task)
    lease = await queue.reserve("w", timeout=1.0)
    
    await queue.ack(lease.lease_id)
    
    stats = await queue.get_stats()
    assert stats.processing_count == 0


@pytest.mark.asyncio
async def test_nack_retry(queue, sample_task):
    await queue.enqueue(sample_task)
    
    lease = await queue.reserve("w", timeout=1.0)
    await queue.nack(lease.lease_id, "error", retry=True)
    
    # 任务应该回到就绪队列
    assert await queue.size() == 1


@pytest.mark.asyncio
async def test_nack_dead_letter(queue, sample_task):
    sample_task.retry_count = 2  # 已达最大重试
    await queue.enqueue(sample_task)
    
    lease = await queue.reserve("w", timeout=1.0)
    await queue.nack(lease.lease_id, "error", retry=True)
    
    # 任务应该进入死信队列
    assert await queue.size() == 0
    dead = await queue.get_dead_letters()
    assert len(dead) == 1


@pytest.mark.asyncio
async def test_lease_expiry(queue, sample_task):
    await queue.enqueue(sample_task)
    
    # 获取短租约
    lease = await queue.reserve("w", timeout=1.0, lease_seconds=1)
    
    # 等待过期
    await asyncio.sleep(1.5)
    
    # 回收
    count = await queue.reclaim_expired_leases()
    assert count == 1
    assert await queue.size() == 1  # 任务回到就绪队列


@pytest.mark.asyncio
async def test_heartbeat_extends_lease(queue, sample_task):
    await queue.enqueue(sample_task)
    
    lease = await queue.reserve("w", timeout=1.0, lease_seconds=1)
    
    # 续租
    await queue.heartbeat(lease.lease_id, extend_seconds=60)
    
    # 等待原过期时间
    await asyncio.sleep(1.5)
    
    # 不应该被回收
    count = await queue.reclaim_expired_leases()
    assert count == 0
```

---

## 七、验收标准

- [ ] Memory 版所有接口实现完整
- [ ] reserve 阻塞语义正确（超时返回 None）
- [ ] 优先级排序正确
- [ ] lease/ack/nack/heartbeat 流程闭环
- [ ] 死信队列功能正常
- [ ] 单元测试覆盖率 > 85%
- [ ] 并发测试：100 worker 争抢无死锁

---

*文档结束*

