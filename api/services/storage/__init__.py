"""
存储服务
"""
from .memory import MemoryTaskStorage

try:
    from .redis import RedisTaskStorage
except ImportError:
    RedisTaskStorage = None

__all__ = ["MemoryTaskStorage", "RedisTaskStorage"]

