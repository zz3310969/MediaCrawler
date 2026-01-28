"""
Redis 版事件总线实现
使用 Redis Pub/Sub
"""
import asyncio
import json
import logging
import uuid
from typing import Optional, List, Dict, Set
from collections import defaultdict

import redis.asyncio as redis

from api.interfaces.event import IEventBus, EventHandler
from api.schemas.event import TaskEvent, EventType

logger = logging.getLogger(__name__)


class RedisEventBus(IEventBus):
    """Redis 版事件总线"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        channel_prefix: str = "mc:events:"
    ):
        self._redis_url = redis_url
        self._channel_prefix = channel_prefix
        
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        
        # 本地订阅存储
        self._subscriptions: Dict[str, dict] = {}
        self._type_subscriptions: Dict[EventType, Set[str]] = defaultdict(set)
        self._task_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._session_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _channel(self, name: str) -> str:
        return f"{self._channel_prefix}{name}"
    
    # ========== 发布 ==========
    
    async def publish(self, event: TaskEvent) -> bool:
        """发布事件"""
        r = await self._get_redis()
        
        # 发布到多个频道
        channels = [
            self._channel(f"type:{event.event_type}"),
            self._channel(f"task:{event.task_id}"),
            self._channel(f"session:{event.session_id}"),
            self._channel("all"),
        ]
        
        data = event.model_dump_json()
        
        for channel in channels:
            await r.publish(channel, data)
        
        return True
    
    async def publish_batch(self, events: List[TaskEvent]) -> int:
        """批量发布"""
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
        """订阅事件类型"""
        async with self._lock:
            sub_id = str(uuid.uuid4())
            
            self._subscriptions[sub_id] = {
                "handler": handler,
                "event_type": event_type,
            }
            self._type_subscriptions[event_type].add(sub_id)
            
            # 确保订阅了对应频道
            if self._pubsub:
                await self._pubsub.subscribe(self._channel(f"type:{event_type.value}"))
            
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
            
            self._subscriptions[sub_id] = {
                "handler": handler,
                "task_id": task_id,
            }
            self._task_subscriptions[task_id].add(sub_id)
            
            if self._pubsub:
                await self._pubsub.subscribe(self._channel(f"task:{task_id}"))
            
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
            
            self._subscriptions[sub_id] = {
                "handler": handler,
                "session_id": session_id,
            }
            self._session_subscriptions[session_id].add(sub_id)
            
            if self._pubsub:
                await self._pubsub.subscribe(self._channel(f"session:{session_id}"))
            
            logger.debug(f"Subscribed to session {session_id[:8]}, id={sub_id[:8]}")
            return sub_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        async with self._lock:
            sub = self._subscriptions.pop(subscription_id, None)
            if not sub:
                return False
            
            if "event_type" in sub:
                self._type_subscriptions[sub["event_type"]].discard(subscription_id)
            if "task_id" in sub:
                self._task_subscriptions[sub["task_id"]].discard(subscription_id)
            if "session_id" in sub:
                self._session_subscriptions[sub["session_id"]].discard(subscription_id)
            
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
        """清理用户所有订阅"""
        async with self._lock:
            sub_ids = list(self._session_subscriptions.get(session_id, set()))
            
            for sub_id in sub_ids:
                sub = self._subscriptions.pop(sub_id, None)
                if sub and "event_type" in sub:
                    self._type_subscriptions[sub["event_type"]].discard(sub_id)
            
            self._session_subscriptions.pop(session_id, None)
            
            return len(sub_ids)
    
    # ========== 生命周期 ==========
    
    async def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return
        
        r = await self._get_redis()
        self._pubsub = r.pubsub()
        
        # 订阅全局频道
        await self._pubsub.subscribe(self._channel("all"))
        
        self._running = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        
        logger.info("Redis event bus started")
    
    async def stop(self) -> None:
        """停止事件总线"""
        self._running = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None
        
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        logger.info("Redis event bus stopped")
    
    async def is_running(self) -> bool:
        """检查是否运行中"""
        return self._running
    
    # ========== 内部方法 ==========
    
    async def _listen_loop(self) -> None:
        """监听消息循环"""
        while self._running:
            try:
                if not self._pubsub:
                    await asyncio.sleep(0.1)
                    continue
                
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message["type"] == "message":
                    await self._handle_message(message)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1.0)
    
    async def _handle_message(self, message: dict) -> None:
        """处理消息"""
        try:
            channel = message["channel"]
            data = message["data"]
            
            event = TaskEvent.model_validate_json(data)
            
            # 查找对应的处理器
            handlers_to_call: List[EventHandler] = []
            
            async with self._lock:
                # 按事件类型
                for sub_id in self._type_subscriptions.get(event.event_type, set()):
                    sub = self._subscriptions.get(sub_id)
                    if sub:
                        handlers_to_call.append(sub["handler"])
                
                # 按任务 ID
                for sub_id in self._task_subscriptions.get(event.task_id, set()):
                    sub = self._subscriptions.get(sub_id)
                    if sub:
                        handlers_to_call.append(sub["handler"])
                
                # 按会话 ID
                for sub_id in self._session_subscriptions.get(event.session_id, set()):
                    sub = self._subscriptions.get(sub_id)
                    if sub:
                        handlers_to_call.append(sub["handler"])
            
            # 调用处理器
            for handler in handlers_to_call:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Handler error: {e}")
        
        except Exception as e:
            logger.error(f"Message handling error: {e}")

