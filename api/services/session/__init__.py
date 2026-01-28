"""
Session 服务
"""
from .memory import MemorySessionStore

try:
    from .redis import RedisSessionStore
except ImportError:
    RedisSessionStore = None

__all__ = ["MemorySessionStore", "RedisSessionStore"]

