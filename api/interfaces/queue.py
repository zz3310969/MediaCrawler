"""
任务队列抽象接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel

from api.schemas.task import Task, TaskLease


class QueueStats(BaseModel):
    """队列统计"""
    ready_count: int = 0
    processing_count: int = 0
    delayed_count: int = 0
    dead_letter_count: int = 0


class ITaskQueue(ABC):
    """任务队列抽象接口"""
    
    # ========== 基础操作 ==========
    
    @abstractmethod
    async def enqueue(self, task: Task, priority: Optional[int] = None) -> bool:
        """
        入队
        
        Args:
            task: 任务对象
            priority: 优先级，不传则使用 task.priority
        
        Returns:
            是否成功入队
        """
        pass
    
    @abstractmethod
    async def reserve(
        self, 
        worker_id: str,
        timeout: float = 30.0,
        lease_seconds: int = 300
    ) -> Optional[TaskLease]:
        """
        预留/取出任务（阻塞）
        
        Args:
            worker_id: 当前 worker 标识
            timeout: 等待超时时间（秒）
            lease_seconds: 租约有效期（秒）
        
        Returns:
            TaskLease 或 None（超时）
        """
        pass
    
    @abstractmethod
    async def peek(self) -> Optional[Task]:
        """查看队首（不取出）"""
        pass
    
    @abstractmethod
    async def remove(self, task_id: str) -> bool:
        """移除指定任务"""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """队列长度"""
        pass
    
    # ========== 确认与回收 ==========
    
    @abstractmethod
    async def ack(self, lease_id: str) -> bool:
        """确认执行成功"""
        pass
    
    @abstractmethod
    async def nack(
        self, 
        lease_id: str, 
        reason: str,
        retry: bool = True
    ) -> bool:
        """
        确认执行失败
        
        Args:
            lease_id: 租约 ID
            reason: 失败原因
            retry: 是否重试（False 则移入死信队列）
        """
        pass
    
    @abstractmethod
    async def heartbeat(self, lease_id: str, extend_seconds: int = 300) -> bool:
        """续租/心跳"""
        pass
    
    @abstractmethod
    async def reclaim_expired_leases(self) -> int:
        """回收过期租约，返回回收数量"""
        pass
    
    # ========== 优先级 ==========
    
    @abstractmethod
    async def reorder(self, task_id: str, new_priority: int) -> bool:
        """调整优先级"""
        pass
    
    # ========== 延迟任务 ==========
    
    @abstractmethod
    async def enqueue_delayed(self, task: Task, delay_seconds: int) -> bool:
        """延迟入队"""
        pass
    
    @abstractmethod
    async def get_delayed_count(self) -> int:
        """延迟任务数"""
        pass
    
    @abstractmethod
    async def promote_delayed(self) -> int:
        """将到期的延迟任务移入就绪队列，返回移动数量"""
        pass
    
    # ========== 死信队列 ==========
    
    @abstractmethod
    async def move_to_dead_letter(self, task_id: str, reason: str) -> bool:
        """移入死信队列"""
        pass
    
    @abstractmethod
    async def get_dead_letters(
        self, 
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        """获取死信任务"""
        pass
    
    @abstractmethod
    async def retry_dead_letter(self, task_id: str) -> bool:
        """重试死信任务"""
        pass
    
    # ========== 监控 ==========
    
    @abstractmethod
    async def get_stats(self) -> QueueStats:
        """队列统计"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    # ========== 任务查询 ==========
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取队列中的任务"""
        pass

