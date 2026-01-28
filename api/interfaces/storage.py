"""
任务存储抽象接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from api.schemas.task import Task, TaskStatus
from api.schemas.event import LogEntry


class ITaskStorage(ABC):
    """任务存储抽象接口"""
    
    # ========== 任务 CRUD ==========
    
    @abstractmethod
    async def create(self, task: Task) -> str:
        """
        创建任务，返回 task_id
        
        Raises:
            ValueError: 如果 task_id 已存在
        """
        pass
    
    @abstractmethod
    async def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        pass
    
    @abstractmethod
    async def update(
        self, 
        task_id: str, 
        data: Dict,
        version: Optional[int] = None  # 乐观锁
    ) -> bool:
        """
        更新任务
        
        Args:
            task_id: 任务 ID
            data: 要更新的字段
            version: 版本号（用于乐观锁）
        
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        pass
    
    @abstractmethod
    async def exists(self, task_id: str) -> bool:
        """任务是否存在"""
        pass
    
    # ========== 批量操作 ==========
    
    @abstractmethod
    async def get_by_session(
        self, 
        session_id: str,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """获取用户任务"""
        pass
    
    @abstractmethod
    async def get_by_status(
        self, 
        status: TaskStatus,
        limit: int = 100
    ) -> List[Task]:
        """获取指定状态的任务"""
        pass
    
    @abstractmethod
    async def bulk_update_status(
        self, 
        task_ids: List[str], 
        status: TaskStatus
    ) -> int:
        """批量更新状态，返回更新数量"""
        pass
    
    @abstractmethod
    async def find_by_idempotency_key(
        self,
        session_id: str,
        idempotency_key: str
    ) -> Optional[Task]:
        """根据幂等键查找任务"""
        pass
    
    # ========== 日志存储 ==========
    
    @abstractmethod
    async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
        """追加日志"""
        pass
    
    @abstractmethod
    async def get_logs(
        self, 
        task_id: str, 
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        """获取日志"""
        pass
    
    @abstractmethod
    async def clear_logs(self, task_id: str) -> bool:
        """清空日志"""
        pass
    
    @abstractmethod
    async def trim_logs(self, task_id: str, max_count: int) -> int:
        """裁剪日志（保留最新 max_count 条），返回删除数量"""
        pass
    
    # ========== 统计查询 ==========
    
    @abstractmethod
    async def count_by_status(
        self, 
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """按状态统计"""
        pass
    
    @abstractmethod
    async def get_recent_tasks(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Task]:
        """获取最近任务"""
        pass
    
    @abstractmethod
    async def count_by_session(self, session_id: str) -> int:
        """获取用户任务总数"""
        pass
    
    # ========== 维护 ==========
    
    @abstractmethod
    async def cleanup_old_tasks(self, days: int) -> int:
        """清理旧任务，返回清理数量"""
        pass
    
    @abstractmethod
    async def archive_task(self, task_id: str) -> bool:
        """归档任务"""
        pass

