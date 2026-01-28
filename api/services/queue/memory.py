"""
内存版任务队列实现
"""
import asyncio
import logging
import heapq
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from api.interfaces.queue import ITaskQueue, QueueStats
from api.schemas.task import Task, TaskLease, TaskStatus

logger = logging.getLogger(__name__)


@dataclass(order=True)
class PriorityItem:
    """优先级队列项"""
    priority: int  # 负数，因为 heapq 是最小堆
    timestamp: float
    task: Task = field(compare=False)


@dataclass
class LeaseInfo:
    """租约信息"""
    lease: TaskLease
    task: Task


class MemoryTaskQueue(ITaskQueue):
    """内存版任务队列"""
    
    def __init__(
        self,
        max_size: int = 1000,
        dead_letter_max: int = 100,
        default_lease_seconds: int = 300,
        max_retries: int = 3
    ):
        self._max_size = max_size
        self._dead_letter_max = dead_letter_max
        self._default_lease_seconds = default_lease_seconds
        self._max_retries = max_retries
        
        # 就绪队列（优先级堆）
        self._ready_queue: List[PriorityItem] = []
        # 任务索引
        self._task_index: Dict[str, Task] = {}
        # 延迟任务 {task_id: (ready_time, task)}
        self._delayed_tasks: Dict[str, Tuple[datetime, Task]] = {}
        # 处理中的租约 {lease_id: LeaseInfo}
        self._processing: Dict[str, LeaseInfo] = {}
        # 死信队列
        self._dead_letters: List[Task] = []
        
        # 等待队列（用于阻塞等待）
        self._wait_event = asyncio.Event()
        
        # 锁
        self._lock = asyncio.Lock()
    
    # ========== 基础操作 ==========
    
    async def enqueue(self, task: Task, priority: Optional[int] = None) -> bool:
        """入队"""
        async with self._lock:
            if len(self._ready_queue) >= self._max_size:
                logger.warning(f"Queue is full, max_size={self._max_size}")
                return False
            
            if task.task_id in self._task_index:
                logger.warning(f"Task {task.task_id} already in queue")
                return False
            
            # 使用指定优先级或任务自身优先级
            prio = priority if priority is not None else task.priority
            
            # 添加到队列（优先级取负，因为 heapq 是最小堆）
            item = PriorityItem(
                priority=-prio,
                timestamp=datetime.utcnow().timestamp(),
                task=task
            )
            heapq.heappush(self._ready_queue, item)
            self._task_index[task.task_id] = task
            
            # 通知等待者
            self._wait_event.set()
            
            logger.debug(f"Task {task.task_id[:8]} enqueued with priority {prio}")
            return True
    
    async def reserve(
        self, 
        worker_id: str,
        timeout: float = 30.0,
        lease_seconds: int = 300
    ) -> Optional[TaskLease]:
        """预留/取出任务（阻塞）"""
        deadline = datetime.utcnow() + timedelta(seconds=timeout)
        
        while datetime.utcnow() < deadline:
            async with self._lock:
                # 先提升延迟任务
                await self._promote_delayed_internal()
                
                if self._ready_queue:
                    item = heapq.heappop(self._ready_queue)
                    task = item.task
                    
                    # 从索引中移除
                    self._task_index.pop(task.task_id, None)
                    
                    # 创建租约
                    lease = TaskLease.create(
                        task_id=task.task_id,
                        worker_id=worker_id,
                        lease_seconds=lease_seconds or self._default_lease_seconds
                    )
                    
                    # 记录处理中
                    self._processing[lease.lease_id] = LeaseInfo(lease=lease, task=task)
                    
                    logger.debug(f"Task {task.task_id[:8]} reserved by {worker_id}")
                    return lease
                
                # 重置事件
                self._wait_event.clear()
            
            # 等待新任务或超时
            remaining = (deadline - datetime.utcnow()).total_seconds()
            if remaining <= 0:
                break
            
            try:
                await asyncio.wait_for(
                    self._wait_event.wait(),
                    timeout=min(remaining, 1.0)  # 最多等待1秒
                )
            except asyncio.TimeoutError:
                pass
        
        return None
    
    async def peek(self) -> Optional[Task]:
        """查看队首（不取出）"""
        async with self._lock:
            if self._ready_queue:
                return self._ready_queue[0].task
            return None
    
    async def remove(self, task_id: str) -> bool:
        """移除指定任务"""
        async with self._lock:
            # 从就绪队列移除
            if task_id in self._task_index:
                self._task_index.pop(task_id)
                # 重建堆（移除特定元素）
                self._ready_queue = [
                    item for item in self._ready_queue 
                    if item.task.task_id != task_id
                ]
                heapq.heapify(self._ready_queue)
                logger.debug(f"Task {task_id[:8]} removed from ready queue")
                return True
            
            # 从延迟任务移除
            if task_id in self._delayed_tasks:
                self._delayed_tasks.pop(task_id)
                logger.debug(f"Task {task_id[:8]} removed from delayed queue")
                return True
            
            return False
    
    async def size(self) -> int:
        """队列长度"""
        async with self._lock:
            return len(self._ready_queue)
    
    # ========== 确认与回收 ==========
    
    async def ack(self, lease_id: str) -> bool:
        """确认执行成功"""
        async with self._lock:
            info = self._processing.pop(lease_id, None)
            if info:
                logger.debug(f"Lease {lease_id[:8]} acknowledged")
                return True
            return False
    
    async def nack(
        self, 
        lease_id: str, 
        reason: str,
        retry: bool = True
    ) -> bool:
        """确认执行失败"""
        async with self._lock:
            info = self._processing.pop(lease_id, None)
            if not info:
                return False
            
            task = info.task
            task.retry_count += 1
            
            if retry and task.retry_count < task.max_retries:
                # 重新入队
                item = PriorityItem(
                    priority=-task.priority,
                    timestamp=datetime.utcnow().timestamp(),
                    task=task
                )
                heapq.heappush(self._ready_queue, item)
                self._task_index[task.task_id] = task
                self._wait_event.set()
                logger.info(f"Task {task.task_id[:8]} re-queued, retry {task.retry_count}")
            else:
                # 移入死信队列
                await self._move_to_dead_letter_internal(task, reason)
            
            return True
    
    async def heartbeat(self, lease_id: str, extend_seconds: int = 300) -> bool:
        """续租/心跳"""
        async with self._lock:
            info = self._processing.get(lease_id)
            if not info:
                return False
            
            info.lease.expires_at = datetime.utcnow() + timedelta(seconds=extend_seconds)
            logger.debug(f"Lease {lease_id[:8]} extended by {extend_seconds}s")
            return True
    
    async def reclaim_expired_leases(self) -> int:
        """回收过期租约，返回回收数量"""
        async with self._lock:
            now = datetime.utcnow()
            expired = []
            
            for lease_id, info in list(self._processing.items()):
                if info.lease.is_expired():
                    expired.append(lease_id)
            
            for lease_id in expired:
                info = self._processing.pop(lease_id)
                task = info.task
                task.retry_count += 1
                
                if task.retry_count < task.max_retries:
                    # 重新入队
                    item = PriorityItem(
                        priority=-task.priority,
                        timestamp=now.timestamp(),
                        task=task
                    )
                    heapq.heappush(self._ready_queue, item)
                    self._task_index[task.task_id] = task
                    logger.info(f"Reclaimed expired lease, task {task.task_id[:8]} re-queued")
                else:
                    await self._move_to_dead_letter_internal(task, "Max retries exceeded")
            
            if expired:
                self._wait_event.set()
                logger.info(f"Reclaimed {len(expired)} expired leases")
            
            return len(expired)
    
    # ========== 优先级 ==========
    
    async def reorder(self, task_id: str, new_priority: int) -> bool:
        """调整优先级"""
        async with self._lock:
            if task_id not in self._task_index:
                return False
            
            task = self._task_index[task_id]
            task.priority = new_priority
            
            # 重建堆
            self._ready_queue = [
                PriorityItem(
                    priority=-item.task.priority,
                    timestamp=item.timestamp,
                    task=item.task
                )
                for item in self._ready_queue
            ]
            heapq.heapify(self._ready_queue)
            
            logger.debug(f"Task {task_id[:8]} priority changed to {new_priority}")
            return True
    
    # ========== 延迟任务 ==========
    
    async def enqueue_delayed(self, task: Task, delay_seconds: int) -> bool:
        """延迟入队"""
        async with self._lock:
            if task.task_id in self._task_index or task.task_id in self._delayed_tasks:
                return False
            
            ready_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
            self._delayed_tasks[task.task_id] = (ready_time, task)
            
            logger.debug(f"Task {task.task_id[:8]} delayed for {delay_seconds}s")
            return True
    
    async def get_delayed_count(self) -> int:
        """延迟任务数"""
        async with self._lock:
            return len(self._delayed_tasks)
    
    async def promote_delayed(self) -> int:
        """将到期的延迟任务移入就绪队列，返回移动数量"""
        async with self._lock:
            return await self._promote_delayed_internal()
    
    async def _promote_delayed_internal(self) -> int:
        """内部方法：提升延迟任务（不加锁）"""
        now = datetime.utcnow()
        promoted = []
        
        for task_id, (ready_time, task) in list(self._delayed_tasks.items()):
            if now >= ready_time:
                promoted.append(task_id)
                item = PriorityItem(
                    priority=-task.priority,
                    timestamp=now.timestamp(),
                    task=task
                )
                heapq.heappush(self._ready_queue, item)
                self._task_index[task.task_id] = task
        
        for task_id in promoted:
            self._delayed_tasks.pop(task_id)
        
        if promoted:
            self._wait_event.set()
            logger.debug(f"Promoted {len(promoted)} delayed tasks")
        
        return len(promoted)
    
    # ========== 死信队列 ==========
    
    async def move_to_dead_letter(self, task_id: str, reason: str) -> bool:
        """移入死信队列"""
        async with self._lock:
            # 尝试从各个队列中找到并移除任务
            task = None
            
            if task_id in self._task_index:
                task = self._task_index.pop(task_id)
                self._ready_queue = [
                    item for item in self._ready_queue
                    if item.task.task_id != task_id
                ]
                heapq.heapify(self._ready_queue)
            elif task_id in self._delayed_tasks:
                _, task = self._delayed_tasks.pop(task_id)
            else:
                # 检查处理中
                for lease_id, info in list(self._processing.items()):
                    if info.task.task_id == task_id:
                        task = info.task
                        self._processing.pop(lease_id)
                        break
            
            if task:
                return await self._move_to_dead_letter_internal(task, reason)
            return False
    
    async def _move_to_dead_letter_internal(self, task: Task, reason: str) -> bool:
        """内部方法：移入死信队列（不加锁）"""
        task.result.error_message = reason
        task.status = TaskStatus.FAILED
        
        self._dead_letters.append(task)
        
        # 限制死信队列大小
        while len(self._dead_letters) > self._dead_letter_max:
            self._dead_letters.pop(0)
        
        logger.info(f"Task {task.task_id[:8]} moved to dead letter: {reason}")
        return True
    
    async def get_dead_letters(
        self, 
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        """获取死信任务"""
        async with self._lock:
            if session_id:
                tasks = [t for t in self._dead_letters if t.session_id == session_id]
            else:
                tasks = self._dead_letters.copy()
            return tasks[:limit]
    
    async def retry_dead_letter(self, task_id: str) -> bool:
        """重试死信任务"""
        async with self._lock:
            for i, task in enumerate(self._dead_letters):
                if task.task_id == task_id:
                    task = self._dead_letters.pop(i)
                    task.retry_count = 0
                    task.status = TaskStatus.PENDING
                    task.result = type(task.result)()  # 重置结果
                    
                    item = PriorityItem(
                        priority=-task.priority,
                        timestamp=datetime.utcnow().timestamp(),
                        task=task
                    )
                    heapq.heappush(self._ready_queue, item)
                    self._task_index[task.task_id] = task
                    self._wait_event.set()
                    
                    logger.info(f"Dead letter task {task_id[:8]} retried")
                    return True
            return False
    
    # ========== 监控 ==========
    
    async def get_stats(self) -> QueueStats:
        """队列统计"""
        async with self._lock:
            return QueueStats(
                ready_count=len(self._ready_queue),
                processing_count=len(self._processing),
                delayed_count=len(self._delayed_tasks),
                dead_letter_count=len(self._dead_letters)
            )
    
    async def health_check(self) -> bool:
        """健康检查"""
        return True
    
    # ========== 任务查询 ==========
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取队列中的任务"""
        async with self._lock:
            # 检查就绪队列
            if task_id in self._task_index:
                return self._task_index[task_id]
            
            # 检查延迟队列
            if task_id in self._delayed_tasks:
                return self._delayed_tasks[task_id][1]
            
            # 检查处理中
            for info in self._processing.values():
                if info.task.task_id == task_id:
                    return info.task
            
            return None

