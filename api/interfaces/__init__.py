"""
多任务系统抽象接口
"""
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

