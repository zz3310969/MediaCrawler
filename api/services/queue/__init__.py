"""
队列服务
"""
from .memory import MemoryTaskQueue

try:
    from .redis import RedisTaskQueue
except ImportError:
    RedisTaskQueue = None

__all__ = ["MemoryTaskQueue", "RedisTaskQueue"]

