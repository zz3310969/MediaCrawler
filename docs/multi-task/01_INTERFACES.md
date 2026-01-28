# 01. 核心接口定义

> 模块: 抽象层  
> Phase: 1  
> 预估工期: 2 天  
> 产出文件:  
> - `api/interfaces/__init__.py`  
> - `api/interfaces/queue.py`  
> - `api/interfaces/storage.py`  
> - `api/interfaces/session.py`  
> - `api/interfaces/event.py`  
> - `api/schemas/task.py`  
> - `api/schemas/session.py`  
> - `api/schemas/event.py`

---

## 一、概述

本文档定义多任务系统的 **抽象接口** 与 **数据模型**。所有服务实现（Memory / Redis / DB）都必须遵循这些接口，以保证可替换性与可测试性。

---

## 二、数据模型（Schemas）

### 2.1 任务相关 (`api/schemas/task.py`)

```python
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"      # 执行完成
    FAILED = "failed"            # 执行失败
    CANCELLED = "cancelled"      # 已取消


class TaskPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


class TaskConfig(BaseModel):
    """任务配置"""
    platform: str                              # xhs/dy/bili/wb/wechat
    crawler_type: str                          # search/creator/detail
    keywords: Optional[str] = None
    creator_ids: Optional[str] = None
    max_notes: int = 100
    enable_comments: bool = False
    max_comments: int = 20
    save_option: str = "csv"                   # csv/json/db
    # 可扩展字段
    extra: Dict[str, Any] = Field(default_factory=dict)


class TaskProgress(BaseModel):
    """任务进度"""
    current: int = 0
    total: int = 0
    percentage: int = 0
    items_crawled: int = 0
    comments_crawled: int = 0


class TaskResult(BaseModel):
    """任务结果"""
    success: bool = False
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    statistics: Dict[str, Any] = Field(default_factory=dict)


class TaskMetadata(BaseModel):
    """任务元数据"""
    sign_server_used: bool = False
    execution_node: Optional[str] = None       # 分布式时的执行节点
    resource_usage: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """任务实体"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    task_name: Optional[str] = None
    
    # 状态
    status: TaskStatus = TaskStatus.PENDING
    priority: int = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    idempotency_key: Optional[str] = None      # 幂等键
    cancel_requested: bool = False             # 取消标记
    
    # 时间
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    
    # 详情
    config: TaskConfig
    progress: TaskProgress = Field(default_factory=TaskProgress)
    result: TaskResult = Field(default_factory=TaskResult)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    
    class Config:
        use_enum_values = True


class TaskLease(BaseModel):
    """任务租约（用于 reserve/ack/nack）"""
    lease_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    worker_id: str
    acquired_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


# ========== 请求/响应模型 ==========

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    task_name: Optional[str] = None
    config: TaskConfig
    priority: int = TaskPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class TaskListRequest(BaseModel):
    """任务列表查询"""
    status: Optional[TaskStatus] = None
    platform: Optional[str] = None
    page: int = 1
    page_size: int = 20


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[Task]
    total: int
    page: int
    page_size: int


class TaskStatsResponse(BaseModel):
    """任务统计响应"""
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0
```

### 2.2 会话相关 (`api/schemas/session.py`)

```python
from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import secrets


class SessionQuota(BaseModel):
    """用户配额"""
    max_concurrent_tasks: int = 3
    max_daily_tasks: int = 100
    used_daily_tasks: int = 0
    quota_reset_at: datetime = Field(default_factory=datetime.utcnow)


class SessionPreferences(BaseModel):
    """用户偏好"""
    default_platform: str = "xhs"
    default_save_option: str = "csv"
    # cookie 引用（实际 cookie 存储在 storage 中）
    cookie_refs: Dict[str, str] = Field(default_factory=dict)


class Session(BaseModel):
    """会话实体"""
    session_id: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    user_id: Optional[str] = None              # 可选，匿名时为空
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    preferences: SessionPreferences = Field(default_factory=SessionPreferences)
    quota: SessionQuota = Field(default_factory=SessionQuota)
    
    # 安全相关
    user_agent_hash: Optional[str] = None      # 绑定 UA 指纹
    ip_prefix: Optional[str] = None            # 绑定 IP 段（可选）
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    user_id: Optional[str] = None
    expire_hours: int = 24


class SessionResponse(BaseModel):
    """会话响应（不含敏感信息）"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    expires_at: datetime
    quota: SessionQuota
```

### 2.3 事件相关 (`api/schemas/event.py`)

```python
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_LOG = "task.log"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RETRYING = "task.retrying"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class TaskEvent(BaseModel):
    """任务事件"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    task_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)


class LogEntry(BaseModel):
    """日志条目"""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel = LogLevel.INFO
    message: str
    extra: Dict[str, Any] = Field(default_factory=dict)
```

---

## 三、抽象接口

### 3.1 队列接口 (`api/interfaces/queue.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from api.schemas.task import Task, TaskLease


class QueueStats(BaseModel):
    """队列统计"""
    ready_count: int = 0
    processing_count: int = 0
    delayed_count: int = 0
    dead_letter_count: int = 0


class ITaskQueue(ABC):
    """任务队列抽象接口"""
    
    # ========== 基础操作 ==========
    
    @abstractmethod
    async def enqueue(self, task: Task, priority: Optional[int] = None) -> bool:
        """入队"""
        pass
    
    @abstractmethod
    async def reserve(
        self, 
        worker_id: str,
        timeout: float = 30.0,
        lease_seconds: int = 300
    ) -> Optional[TaskLease]:
        """
        预留/取出任务（阻塞）
        
        Args:
            worker_id: 当前 worker 标识
            timeout: 等待超时时间（秒）
            lease_seconds: 租约有效期（秒）
        
        Returns:
            TaskLease 或 None（超时）
        """
        pass
    
    @abstractmethod
    async def peek(self) -> Optional[Task]:
        """查看队首（不取出）"""
        pass
    
    @abstractmethod
    async def remove(self, task_id: str) -> bool:
        """移除指定任务"""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """队列长度"""
        pass
    
    # ========== 确认与回收 ==========
    
    @abstractmethod
    async def ack(self, lease_id: str) -> bool:
        """确认执行成功"""
        pass
    
    @abstractmethod
    async def nack(
        self, 
        lease_id: str, 
        reason: str,
        retry: bool = True
    ) -> bool:
        """
        确认执行失败
        
        Args:
            lease_id: 租约 ID
            reason: 失败原因
            retry: 是否重试（False 则移入死信队列）
        """
        pass
    
    @abstractmethod
    async def heartbeat(self, lease_id: str, extend_seconds: int = 300) -> bool:
        """续租/心跳"""
        pass
    
    @abstractmethod
    async def reclaim_expired_leases(self) -> int:
        """回收过期租约，返回回收数量"""
        pass
    
    # ========== 优先级 ==========
    
    @abstractmethod
    async def reorder(self, task_id: str, new_priority: int) -> bool:
        """调整优先级"""
        pass
    
    # ========== 延迟任务 ==========
    
    @abstractmethod
    async def enqueue_delayed(self, task: Task, delay_seconds: int) -> bool:
        """延迟入队"""
        pass
    
    @abstractmethod
    async def get_delayed_count(self) -> int:
        """延迟任务数"""
        pass
    
    @abstractmethod
    async def promote_delayed(self) -> int:
        """将到期的延迟任务移入就绪队列，返回移动数量"""
        pass
    
    # ========== 死信队列 ==========
    
    @abstractmethod
    async def move_to_dead_letter(self, task_id: str, reason: str) -> bool:
        """移入死信队列"""
        pass
    
    @abstractmethod
    async def get_dead_letters(
        self, 
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        """获取死信任务"""
        pass
    
    @abstractmethod
    async def retry_dead_letter(self, task_id: str) -> bool:
        """重试死信任务"""
        pass
    
    # ========== 监控 ==========
    
    @abstractmethod
    async def get_stats(self) -> QueueStats:
        """队列统计"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
```

### 3.2 存储接口 (`api/interfaces/storage.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from api.schemas.task import Task, TaskStatus
from api.schemas.event import LogEntry


class ITaskStorage(ABC):
    """任务存储抽象接口"""
    
    # ========== 任务 CRUD ==========
    
    @abstractmethod
    async def create(self, task: Task) -> str:
        """创建任务，返回 task_id"""
        pass
    
    @abstractmethod
    async def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        pass
    
    @abstractmethod
    async def update(
        self, 
        task_id: str, 
        data: Dict,
        version: Optional[int] = None  # 乐观锁
    ) -> bool:
        """更新任务"""
        pass
    
    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        pass
    
    @abstractmethod
    async def exists(self, task_id: str) -> bool:
        """任务是否存在"""
        pass
    
    # ========== 批量操作 ==========
    
    @abstractmethod
    async def get_by_session(
        self, 
        session_id: str,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """获取用户任务"""
        pass
    
    @abstractmethod
    async def get_by_status(
        self, 
        status: TaskStatus,
        limit: int = 100
    ) -> List[Task]:
        """获取指定状态的任务"""
        pass
    
    @abstractmethod
    async def bulk_update_status(
        self, 
        task_ids: List[str], 
        status: TaskStatus
    ) -> int:
        """批量更新状态，返回更新数量"""
        pass
    
    @abstractmethod
    async def find_by_idempotency_key(
        self,
        session_id: str,
        idempotency_key: str
    ) -> Optional[Task]:
        """根据幂等键查找任务"""
        pass
    
    # ========== 日志存储 ==========
    
    @abstractmethod
    async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
        """追加日志"""
        pass
    
    @abstractmethod
    async def get_logs(
        self, 
        task_id: str, 
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        """获取日志"""
        pass
    
    @abstractmethod
    async def clear_logs(self, task_id: str) -> bool:
        """清空日志"""
        pass
    
    @abstractmethod
    async def trim_logs(self, task_id: str, max_count: int) -> int:
        """裁剪日志（保留最新 max_count 条），返回删除数量"""
        pass
    
    # ========== 统计查询 ==========
    
    @abstractmethod
    async def count_by_status(
        self, 
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """按状态统计"""
        pass
    
    @abstractmethod
    async def get_recent_tasks(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Task]:
        """获取最近任务"""
        pass
    
    # ========== 维护 ==========
    
    @abstractmethod
    async def cleanup_old_tasks(self, days: int) -> int:
        """清理旧任务，返回清理数量"""
        pass
    
    @abstractmethod
    async def archive_task(self, task_id: str) -> bool:
        """归档任务"""
        pass
```

### 3.3 会话接口 (`api/interfaces/session.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from api.schemas.session import Session


class ISessionStore(ABC):
    """会话存储抽象接口"""
    
    @abstractmethod
    async def create(
        self, 
        user_id: Optional[str] = None,
        expire_hours: int = 24,
        **kwargs
    ) -> Session:
        """创建会话"""
        pass
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        pass
    
    @abstractmethod
    async def update(self, session_id: str, data: dict) -> bool:
        """更新会话"""
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        pass
    
    @abstractmethod
    async def refresh(self, session_id: str, extend_hours: int = 24) -> bool:
        """刷新过期时间"""
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: str) -> List[Session]:
        """获取用户所有会话"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量"""
        pass
    
    @abstractmethod
    async def validate(self, session_id: str) -> bool:
        """验证会话有效性"""
        pass
    
    @abstractmethod
    async def increment_daily_tasks(self, session_id: str) -> bool:
        """增加今日任务计数"""
        pass
    
    @abstractmethod
    async def reset_daily_quota(self, session_id: str) -> bool:
        """重置每日配额"""
        pass
```

### 3.4 事件接口 (`api/interfaces/event.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Callable, Awaitable
from api.schemas.event import TaskEvent, EventType


EventHandler = Callable[[TaskEvent], Awaitable[None]]


class IEventBus(ABC):
    """事件总线抽象接口"""
    
    # ========== 发布 ==========
    
    @abstractmethod
    async def publish(self, event: TaskEvent) -> bool:
        """发布事件"""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[TaskEvent]) -> int:
        """批量发布，返回成功数量"""
        pass
    
    # ========== 订阅 ==========
    
    @abstractmethod
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: EventHandler
    ) -> str:
        """订阅事件类型，返回 subscription_id"""
        pass
    
    @abstractmethod
    async def subscribe_task(
        self, 
        task_id: str, 
        handler: EventHandler
    ) -> str:
        """订阅特定任务事件"""
        pass
    
    @abstractmethod
    async def subscribe_session(
        self, 
        session_id: str, 
        handler: EventHandler
    ) -> str:
        """订阅用户所有任务事件"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        pass
    
    # ========== 管理 ==========
    
    @abstractmethod
    async def get_subscribers_count(
        self, 
        event_type: Optional[EventType] = None
    ) -> int:
        """获取订阅者数量"""
        pass
    
    @abstractmethod
    async def clear_subscriptions(self, session_id: str) -> int:
        """清理用户所有订阅，返回清理数量"""
        pass
    
    # ========== 生命周期 ==========
    
    @abstractmethod
    async def start(self) -> None:
        """启动事件总线"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止事件总线"""
        pass
```

---

## 四、接口包导出 (`api/interfaces/__init__.py`)

```python
from .queue import ITaskQueue, QueueStats
from .storage import ITaskStorage
from .session import ISessionStore
from .event import IEventBus, EventHandler

__all__ = [
    "ITaskQueue",
    "QueueStats",
    "ITaskStorage",
    "ISessionStore",
    "IEventBus",
    "EventHandler",
]
```

---

## 五、验收标准

- [ ] 所有接口定义完整，方法签名清晰
- [ ] 数据模型支持 Pydantic 序列化/反序列化
- [ ] 单元测试覆盖数据模型的边界情况
- [ ] 接口文档（docstring）描述清晰

---

## 六、注意事项

1. **异步设计**：所有接口方法都是 `async`，支持高并发
2. **可选参数**：使用 `Optional` 明确可选性
3. **返回值一致性**：操作成功返回 `True/count`，失败返回 `False/0`
4. **版本兼容**：后续新增方法时使用默认参数保持兼容

---

*文档结束*

