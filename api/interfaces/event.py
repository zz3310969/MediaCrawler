"""
事件总线抽象接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Callable, Awaitable

from api.schemas.event import TaskEvent, EventType


# 事件处理器类型
EventHandler = Callable[[TaskEvent], Awaitable[None]]


class IEventBus(ABC):
    """事件总线抽象接口"""
    
    # ========== 发布 ==========
    
    @abstractmethod
    async def publish(self, event: TaskEvent) -> bool:
        """发布事件"""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[TaskEvent]) -> int:
        """批量发布，返回成功数量"""
        pass
    
    # ========== 订阅 ==========
    
    @abstractmethod
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: EventHandler
    ) -> str:
        """订阅事件类型，返回 subscription_id"""
        pass
    
    @abstractmethod
    async def subscribe_task(
        self, 
        task_id: str, 
        handler: EventHandler
    ) -> str:
        """订阅特定任务事件"""
        pass
    
    @abstractmethod
    async def subscribe_session(
        self, 
        session_id: str, 
        handler: EventHandler
    ) -> str:
        """订阅用户所有任务事件"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        pass
    
    # ========== 管理 ==========
    
    @abstractmethod
    async def get_subscribers_count(
        self, 
        event_type: Optional[EventType] = None
    ) -> int:
        """获取订阅者数量"""
        pass
    
    @abstractmethod
    async def clear_subscriptions(self, session_id: str) -> int:
        """清理用户所有订阅，返回清理数量"""
        pass
    
    # ========== 生命周期 ==========
    
    @abstractmethod
    async def start(self) -> None:
        """启动事件总线"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止事件总线"""
        pass
    
    @abstractmethod
    async def is_running(self) -> bool:
        """检查事件总线是否运行中"""
        pass

