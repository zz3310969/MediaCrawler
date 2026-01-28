"""
Redis 版任务队列实现
"""
import asyncio
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

import redis.asyncio as redis

from api.interfaces.queue import ITaskQueue, QueueStats
from api.schemas.task import Task, TaskLease, TaskStatus

logger = logging.getLogger(__name__)


class RedisTaskQueue(ITaskQueue):
    """Redis 版任务队列"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "mc:queue:",
        max_retries: int = 3,
        default_lease_seconds: int = 300
    ):
        self._redis_url = redis_url
        self._prefix = key_prefix
        self._max_retries = max_retries
        self._default_lease_seconds = default_lease_seconds
        
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _key(self, name: str) -> str:
        return f"{self._prefix}{name}"
    
    # ========== 基础操作 ==========
    
    async def enqueue(self, task: Task, priority: Optional[int] = None) -> bool:
        """入队（使用 ZSET 实现优先级队列）"""
        r = await self._get_redis()
        prio = priority if priority is not None else task.priority
        
        # 分数 = 优先级 * -1 + 时间戳小数部分（确保同优先级 FIFO）
        score = -prio + (datetime.utcnow().timestamp() / 1e10)
        
        # 存储任务数据
        task_key = self._key(f"task:{task.task_id}")
        task_data = task.model_dump_json()
        
        await r.set(task_key, task_data)
        await r.zadd(self._key("ready"), {task.task_id: score})
        
        logger.debug(f"Task {task.task_id[:8]} enqueued with priority {prio}")
        return True
    
    async def reserve(
        self, 
        worker_id: str,
        timeout: float = 30.0,
        lease_seconds: int = 300
    ) -> Optional[TaskLease]:
        """预留任务"""
        r = await self._get_redis()
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        
        while datetime.utcnow() < deadline:
            # 使用 Lua 脚本原子性地移动任务
            script = """
            local task_id = redis.call('ZPOPMIN', KEYS[1])
            if task_id and #task_id > 0 then
                return task_id[1]
            end
            return nil
            """
            
            result = await r.eval(script, 1, self._key("ready"))
            
            if result:
                task_id = result
                
                # 创建租约
                lease = TaskLease.create(
                    task_id=task_id,
                    worker_id=worker_id,
                    lease_seconds=lease_seconds or self._default_lease_seconds
                )
                
                # 存储租约信息
                lease_key = self._key(f"lease:{lease.lease_id}")
                lease_data = lease.model_dump_json()
                await r.setex(lease_key, lease_seconds, lease_data)
                
                # 记录处理中的任务
                await r.hset(
                    self._key("processing"), 
                    task_id, 
                    json.dumps({
                        "lease_id": lease.lease_id,
                        "worker_id": worker_id,
                        "expires_at": lease.expires_at.isoformat()
                    })
                )
                
                logger.debug(f"Task {task_id[:8]} reserved by {worker_id}")
                return lease
            
            # 等待
            await asyncio.sleep(min(1.0, (deadline - datetime.utcnow()).total_seconds()))
        
        return None
    
    async def peek(self) -> Optional[Task]:
        """查看队首"""
        r = await self._get_redis()
        result = await r.zrange(self._key("ready"), 0, 0)
        
        if result:
            task_id = result[0]
            return await self.get_task(task_id)
        
        return None
    
    async def remove(self, task_id: str) -> bool:
        """移除任务"""
        r = await self._get_redis()
        
        # 从就绪队列移除
        removed = await r.zrem(self._key("ready"), task_id)
        
        # 从延迟队列移除
        if not removed:
            removed = await r.zrem(self._key("delayed"), task_id)
        
        if removed:
            await r.delete(self._key(f"task:{task_id}"))
            logger.debug(f"Task {task_id[:8]} removed")
            return True
        
        return False
    
    async def size(self) -> int:
        """队列长度"""
        r = await self._get_redis()
        return await r.zcard(self._key("ready"))
    
    # ========== 确认与回收 ==========
    
    async def ack(self, lease_id: str) -> bool:
        """确认成功"""
        r = await self._get_redis()
        
        lease_key = self._key(f"lease:{lease_id}")
        lease_data = await r.get(lease_key)
        
        if lease_data:
            lease = TaskLease.model_validate_json(lease_data)
            
            # 清理租约和处理中记录
            await r.delete(lease_key)
            await r.hdel(self._key("processing"), lease.task_id)
            
            logger.debug(f"Lease {lease_id[:8]} acknowledged")
            return True
        
        return False
    
    async def nack(
        self, 
        lease_id: str, 
        reason: str,
        retry: bool = True
    ) -> bool:
        """确认失败"""
        r = await self._get_redis()
        
        lease_key = self._key(f"lease:{lease_id}")
        lease_data = await r.get(lease_key)
        
        if not lease_data:
            return False
        
        lease = TaskLease.model_validate_json(lease_data)
        task = await self.get_task(lease.task_id)
        
        if not task:
            return False
        
        # 清理租约
        await r.delete(lease_key)
        await r.hdel(self._key("processing"), lease.task_id)
        
        task.retry_count += 1
        
        if retry and task.retry_count < task.max_retries:
            # 重新入队
            await self.enqueue(task)
            logger.info(f"Task {task.task_id[:8]} re-queued, retry {task.retry_count}")
        else:
            # 移入死信队列
            await self.move_to_dead_letter(task.task_id, reason)
        
        return True
    
    async def heartbeat(self, lease_id: str, extend_seconds: int = 300) -> bool:
        """续租"""
        r = await self._get_redis()
        
        lease_key = self._key(f"lease:{lease_id}")
        lease_data = await r.get(lease_key)
        
        if lease_data:
            lease = TaskLease.model_validate_json(lease_data)
            lease.expires_at = datetime.utcnow() + timedelta(seconds=extend_seconds)
            
            await r.setex(lease_key, extend_seconds, lease.model_dump_json())
            
            # 更新处理中记录
            await r.hset(
                self._key("processing"),
                lease.task_id,
                json.dumps({
                    "lease_id": lease.lease_id,
                    "worker_id": lease.worker_id,
                    "expires_at": lease.expires_at.isoformat()
                })
            )
            
            return True
        
        return False
    
    async def reclaim_expired_leases(self) -> int:
        """回收过期租约"""
        r = await self._get_redis()
        now = datetime.utcnow()
        count = 0
        
        # 获取所有处理中的任务
        processing = await r.hgetall(self._key("processing"))
        
        for task_id, info_str in processing.items():
            info = json.loads(info_str)
            expires_at = datetime.fromisoformat(info["expires_at"])
            
            if now > expires_at:
                # 租约过期
                lease_id = info["lease_id"]
                await r.delete(self._key(f"lease:{lease_id}"))
                await r.hdel(self._key("processing"), task_id)
                
                # 获取任务并重新入队
                task = await self.get_task(task_id)
                if task:
                    task.retry_count += 1
                    if task.retry_count < task.max_retries:
                        await self.enqueue(task)
                        logger.info(f"Reclaimed expired lease, task {task_id[:8]} re-queued")
                    else:
                        await self.move_to_dead_letter(task_id, "Max retries exceeded")
                
                count += 1
        
        return count
    
    # ========== 优先级 ==========
    
    async def reorder(self, task_id: str, new_priority: int) -> bool:
        """调整优先级"""
        r = await self._get_redis()
        
        # 检查是否在就绪队列
        score = await r.zscore(self._key("ready"), task_id)
        if score is None:
            return False
        
        # 计算新分数
        new_score = -new_priority + (datetime.utcnow().timestamp() / 1e10)
        await r.zadd(self._key("ready"), {task_id: new_score})
        
        # 更新任务数据
        task = await self.get_task(task_id)
        if task:
            task.priority = new_priority
            await r.set(self._key(f"task:{task_id}"), task.model_dump_json())
        
        logger.debug(f"Task {task_id[:8]} priority changed to {new_priority}")
        return True
    
    # ========== 延迟任务 ==========
    
    async def enqueue_delayed(self, task: Task, delay_seconds: int) -> bool:
        """延迟入队"""
        r = await self._get_redis()
        
        ready_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
        score = ready_time.timestamp()
        
        # 存储任务数据
        await r.set(self._key(f"task:{task.task_id}"), task.model_dump_json())
        await r.zadd(self._key("delayed"), {task.task_id: score})
        
        logger.debug(f"Task {task.task_id[:8]} delayed for {delay_seconds}s")
        return True
    
    async def get_delayed_count(self) -> int:
        """延迟任务数"""
        r = await self._get_redis()
        return await r.zcard(self._key("delayed"))
    
    async def promote_delayed(self) -> int:
        """提升延迟任务"""
        r = await self._get_redis()
        now = datetime.utcnow().timestamp()
        
        # 获取到期的延迟任务
        task_ids = await r.zrangebyscore(self._key("delayed"), 0, now)
        
        count = 0
        for task_id in task_ids:
            task = await self.get_task(task_id)
            if task:
                await r.zrem(self._key("delayed"), task_id)
                await self.enqueue(task)
                count += 1
        
        return count
    
    # ========== 死信队列 ==========
    
    async def move_to_dead_letter(self, task_id: str, reason: str) -> bool:
        """移入死信队列"""
        r = await self._get_redis()
        
        task = await self.get_task(task_id)
        if not task:
            return False
        
        task.result.error_message = reason
        task.status = TaskStatus.FAILED
        
        # 移入死信队列
        await r.lpush(self._key("dead_letter"), task.model_dump_json())
        
        # 从其他队列移除
        await r.zrem(self._key("ready"), task_id)
        await r.zrem(self._key("delayed"), task_id)
        
        logger.info(f"Task {task_id[:8]} moved to dead letter: {reason}")
        return True
    
    async def get_dead_letters(
        self, 
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        """获取死信任务"""
        r = await self._get_redis()
        
        items = await r.lrange(self._key("dead_letter"), 0, limit - 1)
        
        tasks = []
        for item in items:
            task = Task.model_validate_json(item)
            if session_id is None or task.session_id == session_id:
                tasks.append(task)
        
        return tasks[:limit]
    
    async def retry_dead_letter(self, task_id: str) -> bool:
        """重试死信任务"""
        r = await self._get_redis()
        
        # 查找并移除
        items = await r.lrange(self._key("dead_letter"), 0, -1)
        
        for i, item in enumerate(items):
            task = Task.model_validate_json(item)
            if task.task_id == task_id:
                # 移除
                await r.lrem(self._key("dead_letter"), 1, item)
                
                # 重置并重新入队
                task.retry_count = 0
                task.status = TaskStatus.PENDING
                task.result = type(task.result)()
                
                await self.enqueue(task)
                logger.info(f"Dead letter task {task_id[:8]} retried")
                return True
        
        return False
    
    # ========== 监控 ==========
    
    async def get_stats(self) -> QueueStats:
        """队列统计"""
        r = await self._get_redis()
        
        return QueueStats(
            ready_count=await r.zcard(self._key("ready")),
            processing_count=await r.hlen(self._key("processing")),
            delayed_count=await r.zcard(self._key("delayed")),
            dead_letter_count=await r.llen(self._key("dead_letter"))
        )
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            r = await self._get_redis()
            await r.ping()
            return True
        except Exception:
            return False
    
    # ========== 任务查询 ==========
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        r = await self._get_redis()
        
        task_data = await r.get(self._key(f"task:{task_id}"))
        if task_data:
            return Task.model_validate_json(task_data)
        
        return None
    
    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

