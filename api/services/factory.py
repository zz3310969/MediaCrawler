"""
服务工厂
根据配置创建服务实例
"""
import logging
from typing import Literal, Dict, Any, Optional

from api.services.task_manager import TaskManager
from api.services.queue.memory import MemoryTaskQueue
from api.services.storage.memory import MemoryTaskStorage
from api.services.session.memory import MemorySessionStore
from api.services.event.asyncio_bus import AsyncioEventBus

logger = logging.getLogger(__name__)


def create_services(
    backend: Literal["memory", "redis"] = "memory",
    redis_url: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    创建服务实例
    
    Args:
        backend: 后端类型 ("memory" 或 "redis")
        redis_url: Redis 连接 URL
        config: 额外配置
    
    Returns:
        {
            "queue": ITaskQueue,
            "storage": ITaskStorage,
            "session_store": ISessionStore,
            "event_bus": IEventBus,
            "task_manager": TaskManager
        }
    """
    config = config or {}
    
    if backend == "memory":
        queue = MemoryTaskQueue(
            max_size=config.get("queue_max_size", 1000),
            dead_letter_max=config.get("dead_letter_max", 100),
            default_lease_seconds=config.get("lease_timeout", 300),
            max_retries=config.get("max_retries", 3)
        )
        storage = MemoryTaskStorage(
            max_logs_per_task=config.get("max_logs_per_task", 2000),
            log_retention_days=config.get("log_retention_days", 7)
        )
        session_store = MemorySessionStore()
        event_bus = AsyncioEventBus(
            queue_size=config.get("event_queue_size", 1000)
        )
        
        logger.info("Created memory backend services")
    
    elif backend == "redis":
        redis_url = redis_url or config.get("redis_url", "redis://localhost:6379/0")
        key_prefix = config.get("redis_key_prefix", "mc:")
        
        from api.services.queue.redis import RedisTaskQueue
        from api.services.storage.redis import RedisTaskStorage
        from api.services.session.redis import RedisSessionStore
        from api.services.event.redis_bus import RedisEventBus
        
        queue = RedisTaskQueue(
            redis_url=redis_url,
            key_prefix=f"{key_prefix}queue:",
            max_retries=config.get("max_retries", 3),
            default_lease_seconds=config.get("lease_timeout", 300)
        )
        storage = RedisTaskStorage(
            redis_url=redis_url,
            key_prefix=f"{key_prefix}storage:",
            max_logs_per_task=config.get("max_logs_per_task", 2000)
        )
        session_store = RedisSessionStore(
            redis_url=redis_url,
            key_prefix=f"{key_prefix}session:",
            default_expire_hours=config.get("session_expire_hours", 24)
        )
        event_bus = RedisEventBus(
            redis_url=redis_url,
            channel_prefix=f"{key_prefix}events:"
        )
        
        logger.info(f"Created Redis backend services (url={redis_url})")
    
    else:
        raise ValueError(f"Unknown backend: {backend}")
    
    task_manager = TaskManager(
        queue=queue,
        storage=storage,
        session_store=session_store,
        event_bus=event_bus
    )
    
    return {
        "queue": queue,
        "storage": storage,
        "session_store": session_store,
        "event_bus": event_bus,
        "task_manager": task_manager
    }


# 全局服务实例（单例）
_services: Optional[Dict[str, Any]] = None


def get_services(
    backend: Literal["memory", "redis"] = "memory",
    redis_url: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """获取或创建服务实例（单例）"""
    global _services
    if _services is None:
        _services = create_services(backend, redis_url, config)
    return _services


def reset_services() -> None:
    """重置服务实例（用于测试）"""
    global _services
    _services = None


def get_task_manager() -> TaskManager:
    """获取任务管理器"""
    return get_services()["task_manager"]


def get_queue():
    """获取队列服务"""
    return get_services()["queue"]


def get_storage():
    """获取存储服务"""
    return get_services()["storage"]


def get_session_store():
    """获取会话存储"""
    return get_services()["session_store"]


def get_event_bus():
    """获取事件总线"""
    return get_services()["event_bus"]

