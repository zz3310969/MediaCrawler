"""
可靠性服务
提供后台任务：租约回收、延迟任务提升、日志清理
"""
import asyncio
import logging
from typing import Optional

from api.interfaces.queue import ITaskQueue
from api.interfaces.storage import ITaskStorage
from api.interfaces.session import ISessionStore

logger = logging.getLogger(__name__)


class ReliabilityService:
    """可靠性服务"""
    
    def __init__(
        self,
        queue: ITaskQueue,
        storage: ITaskStorage,
        session_store: ISessionStore,
        # 配置
        lease_reclaim_interval: int = 60,
        delayed_promote_interval: int = 10,
        session_cleanup_interval: int = 300,
        task_cleanup_interval: int = 3600,
        task_retention_days: int = 7
    ):
        self._queue = queue
        self._storage = storage
        self._session_store = session_store
        
        self._lease_reclaim_interval = lease_reclaim_interval
        self._delayed_promote_interval = delayed_promote_interval
        self._session_cleanup_interval = session_cleanup_interval
        self._task_cleanup_interval = task_cleanup_interval
        self._task_retention_days = task_retention_days
        
        self._running = False
        self._tasks = []
    
    async def start(self) -> None:
        """启动可靠性服务"""
        if self._running:
            return
        
        self._running = True
        
        self._tasks = [
            asyncio.create_task(self._lease_reclaim_loop()),
            asyncio.create_task(self._delayed_promote_loop()),
            asyncio.create_task(self._session_cleanup_loop()),
            asyncio.create_task(self._task_cleanup_loop()),
        ]
        
        logger.info("Reliability service started")
    
    async def stop(self) -> None:
        """停止可靠性服务"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("Reliability service stopped")
    
    async def _lease_reclaim_loop(self) -> None:
        """租约回收循环"""
        while self._running:
            try:
                count = await self._queue.reclaim_expired_leases()
                if count > 0:
                    logger.info(f"Reclaimed {count} expired leases")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Lease reclaim error: {e}")
            
            await asyncio.sleep(self._lease_reclaim_interval)
    
    async def _delayed_promote_loop(self) -> None:
        """延迟任务提升循环"""
        while self._running:
            try:
                count = await self._queue.promote_delayed()
                if count > 0:
                    logger.debug(f"Promoted {count} delayed tasks")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Delayed promote error: {e}")
            
            await asyncio.sleep(self._delayed_promote_interval)
    
    async def _session_cleanup_loop(self) -> None:
        """会话清理循环"""
        while self._running:
            try:
                count = await self._session_store.cleanup_expired()
                if count > 0:
                    logger.info(f"Cleaned up {count} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
            
            await asyncio.sleep(self._session_cleanup_interval)
    
    async def _task_cleanup_loop(self) -> None:
        """任务清理循环"""
        while self._running:
            try:
                count = await self._storage.cleanup_old_tasks(self._task_retention_days)
                if count > 0:
                    logger.info(f"Cleaned up {count} old tasks")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task cleanup error: {e}")
            
            await asyncio.sleep(self._task_cleanup_interval)


# 全局可靠性服务实例
_reliability_service: Optional[ReliabilityService] = None


def get_reliability_service(
    queue: ITaskQueue = None,
    storage: ITaskStorage = None,
    session_store: ISessionStore = None
) -> ReliabilityService:
    """获取或创建可靠性服务实例"""
    global _reliability_service
    
    if _reliability_service is None:
        if queue is None or storage is None or session_store is None:
            from api.services.factory import get_services
            services = get_services()
            queue = queue or services["queue"]
            storage = storage or services["storage"]
            session_store = session_store or services["session_store"]
        
        _reliability_service = ReliabilityService(
            queue=queue,
            storage=storage,
            session_store=session_store
        )
    
    return _reliability_service

