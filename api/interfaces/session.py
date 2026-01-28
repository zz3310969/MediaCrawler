"""
会话存储抽象接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from api.schemas.session import Session


class ISessionStore(ABC):
    """会话存储抽象接口"""
    
    @abstractmethod
    async def create(
        self, 
        user_id: Optional[str] = None,
        expire_hours: int = 24,
        **kwargs
    ) -> Session:
        """创建会话"""
        pass
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        pass
    
    @abstractmethod
    async def update(self, session_id: str, data: dict) -> bool:
        """更新会话"""
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        pass
    
    @abstractmethod
    async def refresh(self, session_id: str, extend_hours: int = 24) -> bool:
        """刷新过期时间"""
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: str) -> List[Session]:
        """获取用户所有会话"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量"""
        pass
    
    @abstractmethod
    async def validate(self, session_id: str) -> bool:
        """验证会话有效性"""
        pass
    
    @abstractmethod
    async def increment_daily_tasks(self, session_id: str) -> bool:
        """
        增加今日任务计数
        
        Returns:
            如果超过配额返回 False，否则返回 True
        """
        pass
    
    @abstractmethod
    async def reset_daily_quota(self, session_id: str) -> bool:
        """重置每日配额"""
        pass
    
    @abstractmethod
    async def get_running_tasks_count(self, session_id: str) -> int:
        """获取用户运行中的任务数"""
        pass
    
    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        pass

