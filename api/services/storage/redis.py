"""
Redis 版任务存储实现
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone
from collections import deque

import redis.asyncio as redis

from api.interfaces.storage import ITaskStorage
from api.schemas.task import Task, TaskStatus
from api.schemas.event import LogEntry

logger = logging.getLogger(__name__)


class RedisTaskStorage(ITaskStorage):
    """Redis 版任务存储"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "mc:storage:",
        max_logs_per_task: int = 2000
    ):
        self._redis_url = redis_url
        self._prefix = key_prefix
        self._max_logs_per_task = max_logs_per_task
        
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _key(self, name: str) -> str:
        return f"{self._prefix}{name}"
    
    # ========== 任务 CRUD ==========
    
    async def create(self, task: Task) -> str:
        """创建任务"""
        r = await self._get_redis()
        
        task_key = self._key(f"task:{task.task_id}")
        
        # 检查是否存在
        if await r.exists(task_key):
            raise ValueError(f"Task {task.task_id} already exists")
        
        # 存储任务
        await r.set(task_key, task.model_dump_json())
        
        # 添加到会话索引
        await r.sadd(self._key(f"session:{task.session_id}:tasks"), task.task_id)
        
        # 添加幂等键索引
        if task.idempotency_key:
            await r.set(
                self._key(f"idempotency:{task.session_id}:{task.idempotency_key}"),
                task.task_id
            )
        
        # 添加到状态索引
        await r.sadd(self._key(f"status:{task.status}"), task.task_id)
        
        logger.debug(f"Task {task.task_id[:8]} created")
        return task.task_id
    
    async def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        r = await self._get_redis()
        
        task_data = await r.get(self._key(f"task:{task_id}"))
        if task_data:
            return Task.model_validate_json(task_data)
        
        return None
    
    async def update(
        self, 
        task_id: str, 
        data: Dict,
        version: Optional[int] = None
    ) -> bool:
        """更新任务"""
        r = await self._get_redis()
        
        task = await self.get(task_id)
        if not task:
            return False
        
        # 乐观锁检查
        if version is not None and task.version != version:
            return False
        
        old_status = task.status
        
        # 更新字段
        for key, value in data.items():
            if hasattr(task, key):
                if key == "progress" and isinstance(value, dict):
                    for pk, pv in value.items():
                        setattr(task.progress, pk, pv)
                elif key == "result" and isinstance(value, dict):
                    for rk, rv in value.items():
                        setattr(task.result, rk, rv)
                elif key == "metadata" and isinstance(value, dict):
                    for mk, mv in value.items():
                        setattr(task.metadata, mk, mv)
                else:
                    setattr(task, key, value)
        
        task.version += 1
        
        # 存储
        await r.set(self._key(f"task:{task_id}"), task.model_dump_json())
        
        # 更新状态索引
        if task.status != old_status:
            await r.srem(self._key(f"status:{old_status}"), task_id)
            await r.sadd(self._key(f"status:{task.status}"), task_id)
        
        return True
    
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        r = await self._get_redis()
        
        task = await self.get(task_id)
        if not task:
            return False
        
        # 删除任务数据
        await r.delete(self._key(f"task:{task_id}"))
        
        # 删除索引
        await r.srem(self._key(f"session:{task.session_id}:tasks"), task_id)
        await r.srem(self._key(f"status:{task.status}"), task_id)
        
        if task.idempotency_key:
            await r.delete(
                self._key(f"idempotency:{task.session_id}:{task.idempotency_key}")
            )
        
        # 删除日志
        await r.delete(self._key(f"logs:{task_id}"))
        
        logger.debug(f"Task {task_id[:8]} deleted")
        return True
    
    async def exists(self, task_id: str) -> bool:
        """任务是否存在"""
        r = await self._get_redis()
        return await r.exists(self._key(f"task:{task_id}"))
    
    # ========== 批量操作 ==========
    
    async def get_by_session(
        self, 
        session_id: str,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """获取用户任务"""
        r = await self._get_redis()
        
        task_ids = await r.smembers(self._key(f"session:{session_id}:tasks"))
        
        tasks = []
        for task_id in task_ids:
            task = await self.get(task_id)
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
        """获取指定状态的任务"""
        r = await self._get_redis()
        
        task_ids = await r.smembers(self._key(f"status:{status}"))
        
        tasks = []
        for task_id in list(task_ids)[:limit]:
            task = await self.get(task_id)
            if task:
                tasks.append(task)
        
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks
    
    async def bulk_update_status(
        self, 
        task_ids: List[str], 
        status: TaskStatus
    ) -> int:
        """批量更新状态"""
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
        """根据幂等键查找"""
        r = await self._get_redis()
        
        task_id = await r.get(
            self._key(f"idempotency:{session_id}:{idempotency_key}")
        )
        
        if task_id:
            return await self.get(task_id)
        
        return None
    
    # ========== 日志存储 ==========
    
    async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
        """追加日志"""
        r = await self._get_redis()
        
        log_key = self._key(f"logs:{task_id}")
        await r.rpush(log_key, log_entry.model_dump_json())
        
        # 裁剪日志
        await r.ltrim(log_key, -self._max_logs_per_task, -1)
        
        return True
    
    async def get_logs(
        self, 
        task_id: str, 
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        """获取日志"""
        r = await self._get_redis()
        
        log_key = self._key(f"logs:{task_id}")
        
        # 从尾部获取（最新的日志在后面）
        total = await r.llen(log_key)
        start = max(0, total - offset - limit)
        end = total - offset - 1
        
        items = await r.lrange(log_key, start, end)
        
        logs = []
        for item in items:
            log = LogEntry.model_validate_json(item)
            if level is None or log.level == level:
                logs.append(log)
        
        # 倒序（最新的在前面）
        logs.reverse()
        return logs
    
    async def clear_logs(self, task_id: str) -> bool:
        """清空日志"""
        r = await self._get_redis()
        await r.delete(self._key(f"logs:{task_id}"))
        return True
    
    async def trim_logs(self, task_id: str, max_count: int) -> int:
        """裁剪日志"""
        r = await self._get_redis()
        
        log_key = self._key(f"logs:{task_id}")
        current = await r.llen(log_key)
        
        if current <= max_count:
            return 0
        
        await r.ltrim(log_key, -max_count, -1)
        return current - max_count
    
    # ========== 统计查询 ==========
    
    async def count_by_status(
        self, 
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """按状态统计"""
        r = await self._get_redis()
        
        counts = {status.value: 0 for status in TaskStatus}
        
        if session_id:
            task_ids = await r.smembers(self._key(f"session:{session_id}:tasks"))
            for task_id in task_ids:
                task = await self.get(task_id)
                if task:
                    counts[task.status] += 1
        else:
            for status in TaskStatus:
                count = await r.scard(self._key(f"status:{status.value}"))
                counts[status.value] = count
        
        return counts
    
    async def get_recent_tasks(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Task]:
        """获取最近任务"""
        return await self.get_by_session(session_id, limit=limit)
    
    async def count_by_session(self, session_id: str) -> int:
        """获取用户任务总数"""
        r = await self._get_redis()
        return await r.scard(self._key(f"session:{session_id}:tasks"))
    
    # ========== 维护 ==========
    
    async def cleanup_old_tasks(self, days: int) -> int:
        """清理旧任务"""
        r = await self._get_redis()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        count = 0
        
        for status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task_ids = await r.smembers(self._key(f"status:{status.value}"))
            
            for task_id in task_ids:
                task = await self.get(task_id)
                if task and task.created_at < cutoff:
                    await self.delete(task_id)
                    count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} old tasks")
        
        return count
    
    async def archive_task(self, task_id: str) -> bool:
        """归档任务"""
        # Redis 版暂不实现归档
        return False
    
    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

