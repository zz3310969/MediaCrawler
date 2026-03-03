"""
Redis 版 Session 存储实现
"""
import logging
from typing import Optional, List
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis

from api.interfaces.session import ISessionStore
from api.schemas.session import Session

logger = logging.getLogger(__name__)


class RedisSessionStore(ISessionStore):
    """Redis 版 Session 存储"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "mc:session:",
        default_expire_hours: int = 24
    ):
        self._redis_url = redis_url
        self._prefix = key_prefix
        self._default_expire_hours = default_expire_hours
        
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await redis.from_url(self._redis_url, decode_responses=True)
        return self._redis
    
    def _key(self, name: str) -> str:
        return f"{self._prefix}{name}"
    
    async def create(
        self, 
        user_id: Optional[str] = None,
        expire_hours: int = 24,
        **kwargs
    ) -> Session:
        """创建会话"""
        r = await self._get_redis()
        
        session = Session.create(
            user_id=user_id,
            expire_hours=expire_hours,
            **kwargs
        )
        
        session_key = self._key(session.session_id)
        expire_seconds = expire_hours * 3600
        
        await r.setex(session_key, expire_seconds, session.model_dump_json())
        
        # 用户会话索引
        if user_id:
            await r.sadd(self._key(f"user:{user_id}"), session.session_id)
        
        logger.info(f"Session created: {session.session_id[:8]}...")
        return session
    
    async def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        r = await self._get_redis()
        
        data = await r.get(self._key(session_id))
        if data:
            session = Session.model_validate_json(data)
            if session.is_expired():
                await self.delete(session_id)
                return None
            return session
        
        return None
    
    async def update(self, session_id: str, data: dict) -> bool:
        """更新会话"""
        r = await self._get_redis()
        
        session = await self.get(session_id)
        if not session:
            return False
        
        for key, value in data.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.last_active = datetime.now(timezone.utc)
        
        # 获取剩余 TTL
        ttl = await r.ttl(self._key(session_id))
        if ttl > 0:
            await r.setex(self._key(session_id), ttl, session.model_dump_json())
        else:
            await r.set(self._key(session_id), session.model_dump_json())
        
        return True
    
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        r = await self._get_redis()
        
        session = await self.get(session_id)
        if session:
            await r.delete(self._key(session_id))
            
            if session.user_id:
                await r.srem(self._key(f"user:{session.user_id}"), session_id)
            
            logger.info(f"Session deleted: {session_id[:8]}...")
            return True
        
        return False
    
    async def refresh(self, session_id: str, extend_hours: int = 24) -> bool:
        """刷新过期时间"""
        r = await self._get_redis()
        
        session = await self.get(session_id)
        if not session:
            return False
        
        session.refresh(extend_hours)
        
        expire_seconds = extend_hours * 3600
        await r.setex(self._key(session_id), expire_seconds, session.model_dump_json())
        
        return True
    
    async def get_by_user(self, user_id: str) -> List[Session]:
        """获取用户所有会话"""
        r = await self._get_redis()
        
        session_ids = await r.smembers(self._key(f"user:{user_id}"))
        
        sessions = []
        for sid in session_ids:
            session = await self.get(sid)
            if session:
                sessions.append(session)
        
        return sessions
    
    async def cleanup_expired(self) -> int:
        """清理过期会话（Redis 自动过期，此方法主要清理索引）"""
        # Redis 会自动过期，这里主要用于清理用户索引
        return 0
    
    async def validate(self, session_id: str) -> bool:
        """验证会话有效性"""
        session = await self.get(session_id)
        return session is not None and session.is_valid()
    
    async def increment_daily_tasks(self, session_id: str) -> bool:
        """增加今日任务计数"""
        session = await self.get(session_id)
        if not session:
            return False
        
        # 检查是否需要重置每日配额
        now = datetime.now(timezone.utc)
        if now.date() > session.quota.quota_reset_at.date():
            session.reset_daily_quota()
        
        # 检查配额
        if session.quota.used_daily_tasks >= session.quota.max_daily_tasks:
            return False
        
        session.quota.used_daily_tasks += 1
        await self.update(session_id, {"quota": session.quota})
        
        return True
    
    async def reset_daily_quota(self, session_id: str) -> bool:
        """重置每日配额"""
        session = await self.get(session_id)
        if not session:
            return False
        
        session.reset_daily_quota()
        await self.update(session_id, {"quota": session.quota})
        
        return True
    
    async def get_running_tasks_count(self, session_id: str) -> int:
        """获取用户运行中的任务数"""
        # 需要和 TaskStorage 配合
        return 0
    
    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        r = await self._get_redis()
        return await r.exists(self._key(session_id))
    
    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None

