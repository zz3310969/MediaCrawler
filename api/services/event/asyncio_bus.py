"""
基于 asyncio 的事件总线实现
"""
import asyncio
import logging
import uuid
from typing import Optional, List, Dict, Set
from collections import defaultdict

from api.interfaces.event import IEventBus, EventHandler
from api.schemas.event import TaskEvent, EventType

logger = logging.getLogger(__name__)


class Subscription:
    """订阅信息"""
    def __init__(
        self,
        subscription_id: str,
        handler: EventHandler,
        event_type: Optional[EventType] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.subscription_id = subscription_id
        self.handler = handler
        self.event_type = event_type
        self.task_id = task_id
        self.session_id = session_id


class AsyncioEventBus(IEventBus):
    """基于 asyncio 的事件总线"""
    
    def __init__(
        self,
        queue_size: int = 1000,
        max_handlers_per_event: int = 100
    ):
        self._queue_size = queue_size
        self._max_handlers = max_handlers_per_event
        
        # 事件队列
        self._event_queue: asyncio.Queue = None
        
        # 订阅存储
        self._subscriptions: Dict[str, Subscription] = {}
        # 按事件类型索引
        self._type_subscriptions: Dict[EventType, Set[str]] = defaultdict(set)
        # 按任务 ID 索引
        self._task_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        # 按会话 ID 索引
        self._session_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # 运行状态
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        
        # 锁
        self._lock = asyncio.Lock()
    
    # ========== 发布 ==========
    
    async def publish(self, event: TaskEvent) -> bool:
        """发布事件"""
        if not self._running or not self._event_queue:
            logger.warning("Event bus not running")
            return False
        
        try:
            # 非阻塞入队
            self._event_queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
            return False
    
    async def publish_batch(self, events: List[TaskEvent]) -> int:
        """批量发布，返回成功数量"""
        count = 0
        for event in events:
            if await self.publish(event):
                count += 1
        return count
    
    # ========== 订阅 ==========
    
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: EventHandler
    ) -> str:
        """订阅事件类型，返回 subscription_id"""
        async with self._lock:
            if len(self._type_subscriptions[event_type]) >= self._max_handlers:
                raise ValueError(f"Too many handlers for event type {event_type}")
            
            sub_id = str(uuid.uuid4())
            sub = Subscription(
                subscription_id=sub_id,
                handler=handler,
                event_type=event_type
            )
            
            self._subscriptions[sub_id] = sub
            self._type_subscriptions[event_type].add(sub_id)
            
            logger.debug(f"Subscribed to {event_type}, id={sub_id[:8]}")
            return sub_id
    
    async def subscribe_task(
        self, 
        task_id: str, 
        handler: EventHandler
    ) -> str:
        """订阅特定任务事件"""
        async with self._lock:
            sub_id = str(uuid.uuid4())
            sub = Subscription(
                subscription_id=sub_id,
                handler=handler,
                task_id=task_id
            )
            
            self._subscriptions[sub_id] = sub
            self._task_subscriptions[task_id].add(sub_id)
            
            logger.debug(f"Subscribed to task {task_id[:8]}, id={sub_id[:8]}")
            return sub_id
    
    async def subscribe_session(
        self, 
        session_id: str, 
        handler: EventHandler
    ) -> str:
        """订阅用户所有任务事件"""
        async with self._lock:
            sub_id = str(uuid.uuid4())
            sub = Subscription(
                subscription_id=sub_id,
                handler=handler,
                session_id=session_id
            )
            
            self._subscriptions[sub_id] = sub
            self._session_subscriptions[session_id].add(sub_id)
            
            logger.debug(f"Subscribed to session {session_id[:8]}, id={sub_id[:8]}")
            return sub_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        async with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if not sub:
                return False
            
            # 从索引中移除
            if sub.event_type:
                self._type_subscriptions[sub.event_type].discard(subscription_id)
            if sub.task_id:
                self._task_subscriptions[sub.task_id].discard(subscription_id)
            if sub.session_id:
                self._session_subscriptions[sub.session_id].discard(subscription_id)
            
            logger.debug(f"Unsubscribed {subscription_id[:8]}")
            return True
    
    # ========== 管理 ==========
    
    async def get_subscribers_count(
        self, 
        event_type: Optional[EventType] = None
    ) -> int:
        """获取订阅者数量"""
        if event_type:
            return len(self._type_subscriptions[event_type])
        return len(self._subscriptions)
    
    async def clear_subscriptions(self, session_id: str) -> int:
        """清理用户所有订阅，返回清理数量"""
        async with self._lock:
            sub_ids = list(self._session_subscriptions.get(session_id, set()))
            
            for sub_id in sub_ids:
                sub = self._subscriptions.pop(sub_id, None)
                if sub:
                    if sub.event_type:
                        self._type_subscriptions[sub.event_type].discard(sub_id)
                    if sub.task_id:
                        self._task_subscriptions[sub.task_id].discard(sub_id)
            
            self._session_subscriptions.pop(session_id, None)
            
            logger.debug(f"Cleared {len(sub_ids)} subscriptions for session {session_id[:8]}")
            return len(sub_ids)
    
    # ========== 生命周期 ==========
    
    async def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return
        
        self._event_queue = asyncio.Queue(maxsize=self._queue_size)
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        
        logger.info("Event bus started")
    
    async def stop(self) -> None:
        """停止事件总线"""
        self._running = False
        
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None
        
        # 清空队列
        if self._event_queue:
            while not self._event_queue.empty():
                try:
                    self._event_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        logger.info("Event bus stopped")
    
    async def is_running(self) -> bool:
        """检查事件总线是否运行中"""
        return self._running
    
    # ========== 内部方法 ==========
    
    async def _dispatch_loop(self) -> None:
        """事件分发循环"""
        while self._running:
            try:
                # 等待事件
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                
                # 分发事件
                await self._dispatch_event(event)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatch error: {e}", exc_info=True)
    
    async def _dispatch_event(self, event: TaskEvent) -> None:
        """分发单个事件"""
        handlers_to_call: List[EventHandler] = []
        
        async with self._lock:
            # 按事件类型查找订阅者
            for sub_id in self._type_subscriptions.get(event.event_type, set()):
                sub = self._subscriptions.get(sub_id)
                if sub:
                    handlers_to_call.append(sub.handler)
            
            # 按任务 ID 查找订阅者
            for sub_id in self._task_subscriptions.get(event.task_id, set()):
                sub = self._subscriptions.get(sub_id)
                if sub:
                    handlers_to_call.append(sub.handler)
            
            # 按会话 ID 查找订阅者
            for sub_id in self._session_subscriptions.get(event.session_id, set()):
                sub = self._subscriptions.get(sub_id)
                if sub:
                    handlers_to_call.append(sub.handler)
        
        # 并发调用所有处理器
        if handlers_to_call:
            await asyncio.gather(
                *[self._safe_call(handler, event) for handler in handlers_to_call],
                return_exceptions=True
            )
    
    async def _safe_call(self, handler: EventHandler, event: TaskEvent) -> None:
        """安全调用处理器"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)

