"""
事件相关数据模型
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    """事件类型"""
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
    """日志级别"""
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
    
    class Config:
        use_enum_values = True


class LogEntry(BaseModel):
    """日志条目"""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel = LogLevel.INFO
    message: str
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
    
    @classmethod
    def create(
        cls,
        task_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        **extra
    ) -> "LogEntry":
        """创建日志条目"""
        return cls(
            task_id=task_id,
            level=level,
            message=message,
            extra=extra
        )


class LogQueryRequest(BaseModel):
    """日志查询请求"""
    task_id: str
    level: Optional[LogLevel] = None
    limit: int = 100
    offset: int = 0
    since: Optional[datetime] = None


class LogQueryResponse(BaseModel):
    """日志查询响应"""
    logs: List[LogEntry]
    total: int
    has_more: bool

