# 04. 存储服务开发文档

> 模块: 任务状态/日志持久化  
> Phase: 2/6  
> 预估工期: 1.5 天  
> 产出文件:  
> - `api/services/storage/memory.py`  
> - `api/services/storage/redis.py`（Phase 6）

---

## 一、模块职责

存储服务负责：
1. **任务 CRUD**：任务的创建、查询、更新、删除
2. **状态管理**：任务状态流转、乐观锁更新
3. **日志存储**：任务执行日志的追加与查询
4. **统计查询**：按状态、用户统计任务数

---

## 二、类图

```
┌─────────────────────────────────────────────────────────────────┐
│                    ITaskStorage (接口)                          │
├─────────────────────────────────────────────────────────────────┤
│ + create(task) -> task_id                                       │
│ + get(task_id) -> Task?                                         │
│ + update(task_id, data, version?) -> bool                       │
│ + delete(task_id) -> bool                                       │
│ + get_by_session(session_id, ...) -> List[Task]                 │
│ + append_log(task_id, log_entry) -> bool                        │
│ + get_logs(task_id, ...) -> List[LogEntry]                      │
│ + count_by_status(session_id?) -> Dict[str, int]                │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
           ┌──────────────────┴──────────────────┐
           │                                     │
┌──────────────────────┐              ┌──────────────────────┐
│  MemoryTaskStorage   │              │  RedisTaskStorage    │
├──────────────────────┤              ├──────────────────────┤
│ - tasks: Dict        │              │ - redis: Redis       │
│ - logs: Dict         │              │ - key_prefix: str    │
│ - version: Dict      │              │ - log_max_size: int  │
└──────────────────────┘              └──────────────────────┘
```

---

## 三、Memory 版实现

### 3.1 核心代码 (`api/services/storage/memory.py`)

```python
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from collections import deque

from api.interfaces.storage import ITaskStorage
from api.schemas.task import Task, TaskStatus
from api.schemas.event import LogEntry, LogLevel


class MemoryTaskStorage(ITaskStorage):
    """内存版任务存储"""
    
    def __init__(
        self,
        max_tasks: int = 10000,
        max_logs_per_task: int = 2000,    # 每任务最大日志条数
        log_retention_hours: int = 24      # 日志保留时间
    ):
        # 任务存储
        self._tasks: Dict[str, Task] = {}
        self._versions: Dict[str, int] = {}  # 乐观锁版本号
        
        # 日志存储（ring buffer）
        self._logs: Dict[str, deque] = {}
        
        # 索引
        self._session_index: Dict[str, set] = {}      # session_id -> {task_ids}
        self._status_index: Dict[TaskStatus, set] = {
            status: set() for status in TaskStatus
        }
        self._idempotency_index: Dict[str, str] = {}  # (session_id, key) -> task_id
        
        # 配置
        self._max_tasks = max_tasks
        self._max_logs_per_task = max_logs_per_task
        self._log_retention_hours = log_retention_hours
        
        # 锁
        self._lock = asyncio.Lock()
    
    # ========== 任务 CRUD ==========
    
    async def create(self, task: Task) -> str:
        async with self._lock:
            if len(self._tasks) >= self._max_tasks:
                # 清理已完成的旧任务
                await self._evict_old_completed()
            
            # 检查幂等键
            if task.idempotency_key:
                idx_key = f"{task.session_id}:{task.idempotency_key}"
                if idx_key in self._idempotency_index:
                    raise ValueError(f"Duplicate idempotency key: {task.idempotency_key}")
                self._idempotency_index[idx_key] = task.task_id
            
            self._tasks[task.task_id] = task
            self._versions[task.task_id] = 1
            
            # 更新索引
            if task.session_id not in self._session_index:
                self._session_index[task.session_id] = set()
            self._session_index[task.session_id].add(task.task_id)
            
            self._status_index[task.status].add(task.task_id)
            
            # 初始化日志队列
            self._logs[task.task_id] = deque(maxlen=self._max_logs_per_task)
            
            return task.task_id
    
    async def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
    
    async def update(
        self,
        task_id: str,
        data: Dict,
        version: Optional[int] = None
    ) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            # 乐观锁检查
            if version is not None:
                current_version = self._versions.get(task_id, 0)
                if current_version != version:
                    return False  # 版本冲突
            
            # 状态变更时更新索引
            old_status = task.status
            new_status = data.get("status")
            
            # 更新字段
            for key, value in data.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # 更新状态索引
            if new_status and old_status != new_status:
                self._status_index[old_status].discard(task_id)
                self._status_index[new_status].add(task_id)
            
            # 版本号递增
            self._versions[task_id] = self._versions.get(task_id, 0) + 1
            
            return True
    
    async def delete(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.pop(task_id, None)
            if not task:
                return False
            
            # 清理索引
            if task.session_id in self._session_index:
                self._session_index[task.session_id].discard(task_id)
            
            self._status_index[task.status].discard(task_id)
            
            if task.idempotency_key:
                idx_key = f"{task.session_id}:{task.idempotency_key}"
                self._idempotency_index.pop(idx_key, None)
            
            # 清理日志
            self._logs.pop(task_id, None)
            self._versions.pop(task_id, None)
            
            return True
    
    async def exists(self, task_id: str) -> bool:
        return task_id in self._tasks
    
    # ========== 批量操作 ==========
    
    async def get_by_session(
        self,
        session_id: str,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        task_ids = self._session_index.get(session_id, set())
        
        tasks = []
        for task_id in task_ids:
            task = self._tasks.get(task_id)
            if not task:
                continue
            
            if status and task.status != status:
                continue
            
            if platform and task.config.platform != platform:
                continue
            
            tasks.append(task)
        
        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[offset:offset + limit]
    
    async def get_by_status(
        self,
        status: TaskStatus,
        limit: int = 100
    ) -> List[Task]:
        task_ids = list(self._status_index.get(status, set()))[:limit]
        return [self._tasks[tid] for tid in task_ids if tid in self._tasks]
    
    async def bulk_update_status(
        self,
        task_ids: List[str],
        status: TaskStatus
    ) -> int:
        count = 0
        for task_id in task_ids:
            if await self.update(task_id, {"status": status}):
                count += 1
        return count
    
    async def find_by_idempotency_key(
        self,
        session_id: str,
        idempotency_key: str
    ) -> Optional[Task]:
        idx_key = f"{session_id}:{idempotency_key}"
        task_id = self._idempotency_index.get(idx_key)
        if task_id:
            return self._tasks.get(task_id)
        return None
    
    # ========== 日志存储 ==========
    
    async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
        log_queue = self._logs.get(task_id)
        if log_queue is None:
            return False
        
        # deque 会自动淘汰旧日志（ring buffer）
        log_queue.append(log_entry)
        return True
    
    async def get_logs(
        self,
        task_id: str,
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        log_queue = self._logs.get(task_id)
        if log_queue is None:
            return []
        
        logs = list(log_queue)
        
        if level:
            logs = [log for log in logs if log.level == level]
        
        return logs[offset:offset + limit]
    
    async def clear_logs(self, task_id: str) -> bool:
        log_queue = self._logs.get(task_id)
        if log_queue is None:
            return False
        
        log_queue.clear()
        return True
    
    async def trim_logs(self, task_id: str, max_count: int) -> int:
        log_queue = self._logs.get(task_id)
        if log_queue is None:
            return 0
        
        original_len = len(log_queue)
        while len(log_queue) > max_count:
            log_queue.popleft()
        
        return original_len - len(log_queue)
    
    # ========== 统计查询 ==========
    
    async def count_by_status(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        result = {}
        
        for status in TaskStatus:
            if session_id:
                session_tasks = self._session_index.get(session_id, set())
                status_tasks = self._status_index.get(status, set())
                count = len(session_tasks & status_tasks)
            else:
                count = len(self._status_index.get(status, set()))
            
            result[status.value] = count
        
        return result
    
    async def get_recent_tasks(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Task]:
        return await self.get_by_session(session_id, limit=limit)
    
    # ========== 维护 ==========
    
    async def cleanup_old_tasks(self, days: int) -> int:
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            to_delete = []
            for task_id, task in self._tasks.items():
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if task.finished_at and task.finished_at < cutoff:
                        to_delete.append(task_id)
            
            for task_id in to_delete:
                await self.delete(task_id)
            
            return len(to_delete)
    
    async def archive_task(self, task_id: str) -> bool:
        # Memory 版暂不支持归档，直接返回 True
        return True
    
    async def _evict_old_completed(self) -> None:
        """淘汰最旧的已完成任务"""
        completed = [
            (tid, task) for tid, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        
        if not completed:
            return
        
        # 按完成时间排序，删除最旧的
        completed.sort(key=lambda x: x[1].finished_at or x[1].created_at)
        oldest_id = completed[0][0]
        await self.delete(oldest_id)
    
    # ========== 辅助方法 ==========
    
    async def get_version(self, task_id: str) -> Optional[int]:
        """获取任务版本号（用于乐观锁）"""
        return self._versions.get(task_id)
```

---

## 四、日志管理最佳实践

### 4.1 日志分级策略

```python
from api.schemas.event import LogLevel

# 日志保留策略
LOG_RETENTION = {
    LogLevel.DEBUG: 100,    # 只保留最新 100 条
    LogLevel.INFO: 500,     # 保留 500 条
    LogLevel.WARN: 1000,    # 保留 1000 条
    LogLevel.ERROR: 2000,   # 全部保留
}

async def append_log_with_policy(
    storage: ITaskStorage,
    task_id: str,
    log_entry: LogEntry
) -> bool:
    """带策略的日志追加"""
    # 追加日志
    result = await storage.append_log(task_id, log_entry)
    
    # 按级别裁剪
    if log_entry.level == LogLevel.DEBUG:
        await storage.trim_logs(task_id, LOG_RETENTION[LogLevel.DEBUG])
    
    return result
```

### 4.2 日志采样（高频任务）

```python
import random

class LogSampler:
    """日志采样器"""
    
    def __init__(self, sample_rate: float = 0.1):
        self._rate = sample_rate
        self._counter = 0
    
    def should_log(self, level: LogLevel) -> bool:
        """判断是否应该记录"""
        # ERROR/WARN 总是记录
        if level in (LogLevel.ERROR, LogLevel.WARN):
            return True
        
        # INFO/DEBUG 按采样率
        self._counter += 1
        return random.random() < self._rate
```

---

## 五、Redis 版实现要点（Phase 6）

### 5.1 Key 设计

```
task:{task_id}                      # HASH - 任务数据
task:{task_id}:version              # STRING - 版本号
task:{task_id}:logs                 # LIST - 日志（LPUSH + LTRIM）

idx:session:{session_id}            # SET - 用户任务索引
idx:status:{status}                 # SET - 状态索引
idx:idem:{session_id}:{key}         # STRING - 幂等键索引
```

### 5.2 日志 Ring Buffer 实现

```python
async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
    key = f"task:{task_id}:logs"
    
    async with self._redis.pipeline() as pipe:
        # 从左侧推入
        pipe.lpush(key, log_entry.json())
        # 保留最新 N 条
        pipe.ltrim(key, 0, self._max_logs_per_task - 1)
        await pipe.execute()
    
    return True

async def get_logs(self, task_id: str, limit: int = 100, offset: int = 0, **kwargs) -> List[LogEntry]:
    key = f"task:{task_id}:logs"
    
    # LRANGE 获取指定范围
    data = await self._redis.lrange(key, offset, offset + limit - 1)
    
    return [LogEntry.parse_raw(item) for item in data]
```

### 5.3 乐观锁实现（WATCH/MULTI）

```python
async def update(self, task_id: str, data: Dict, version: Optional[int] = None) -> bool:
    task_key = f"task:{task_id}"
    version_key = f"task:{task_id}:version"
    
    async with self._redis.pipeline(transaction=True) as pipe:
        try:
            # WATCH 版本号
            await pipe.watch(version_key)
            
            current_version = await self._redis.get(version_key)
            if version is not None and int(current_version or 0) != version:
                return False
            
            pipe.multi()
            pipe.hset(task_key, mapping=data)
            pipe.incr(version_key)
            await pipe.execute()
            
            return True
        except redis.WatchError:
            return False  # 并发冲突
```

---

## 六、单元测试用例

```python
import pytest
from api.services.storage.memory import MemoryTaskStorage
from api.schemas.task import Task, TaskConfig, TaskStatus
from api.schemas.event import LogEntry, LogLevel


@pytest.fixture
def storage():
    return MemoryTaskStorage(max_logs_per_task=100)


@pytest.fixture
def sample_task():
    return Task(
        session_id="test-session",
        config=TaskConfig(platform="xhs", crawler_type="search")
    )


@pytest.mark.asyncio
async def test_create_and_get(storage, sample_task):
    task_id = await storage.create(sample_task)
    
    task = await storage.get(task_id)
    assert task is not None
    assert task.session_id == "test-session"


@pytest.mark.asyncio
async def test_update_with_version(storage, sample_task):
    await storage.create(sample_task)
    
    # 正确版本
    result = await storage.update(
        sample_task.task_id,
        {"status": TaskStatus.RUNNING},
        version=1
    )
    assert result == True
    
    # 错误版本
    result = await storage.update(
        sample_task.task_id,
        {"status": TaskStatus.COMPLETED},
        version=1  # 已经是 2 了
    )
    assert result == False


@pytest.mark.asyncio
async def test_idempotency_key(storage):
    task1 = Task(
        session_id="s1",
        config=TaskConfig(platform="xhs", crawler_type="search"),
        idempotency_key="key1"
    )
    task2 = Task(
        session_id="s1",
        config=TaskConfig(platform="xhs", crawler_type="search"),
        idempotency_key="key1"
    )
    
    await storage.create(task1)
    
    with pytest.raises(ValueError):
        await storage.create(task2)


@pytest.mark.asyncio
async def test_find_by_idempotency(storage):
    task = Task(
        session_id="s1",
        config=TaskConfig(platform="xhs", crawler_type="search"),
        idempotency_key="unique-key"
    )
    await storage.create(task)
    
    found = await storage.find_by_idempotency_key("s1", "unique-key")
    assert found is not None
    assert found.task_id == task.task_id


@pytest.mark.asyncio
async def test_logs_ring_buffer(storage, sample_task):
    storage._max_logs_per_task = 10
    await storage.create(sample_task)
    
    # 写入 20 条日志
    for i in range(20):
        await storage.append_log(
            sample_task.task_id,
            LogEntry(task_id=sample_task.task_id, message=f"Log {i}")
        )
    
    # 应该只保留最新 10 条
    logs = await storage.get_logs(sample_task.task_id, limit=100)
    assert len(logs) == 10
    assert logs[-1].message == "Log 19"


@pytest.mark.asyncio
async def test_count_by_status(storage):
    for i in range(5):
        t = Task(session_id="s1", config=TaskConfig(platform="xhs", crawler_type="search"))
        await storage.create(t)
    
    for i in range(3):
        t = Task(
            session_id="s1",
            config=TaskConfig(platform="xhs", crawler_type="search"),
            status=TaskStatus.RUNNING
        )
        await storage.create(t)
    
    counts = await storage.count_by_status("s1")
    assert counts["pending"] == 5
    assert counts["running"] == 3
```

---

## 七、验收标准

- [ ] Memory 版所有接口实现完整
- [ ] 乐观锁机制工作正常
- [ ] 幂等键去重功能正常
- [ ] 日志 ring buffer 自动淘汰
- [ ] 索引一致性（增删改时同步更新）
- [ ] 单元测试覆盖率 > 85%

---

*文档结束*

