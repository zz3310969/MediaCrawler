"""
内存版 Session 存储实现
"""
import asyncio
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from api.interfaces.session import ISessionStore
from api.schemas.session import Session

logger = logging.getLogger(__name__)


class MemorySessionStore(ISessionStore):
    """内存版 Session 存储"""
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids
        self._lock = asyncio.Lock()
    
    async def create(
        self, 
        user_id: Optional[str] = None,
        expire_hours: int = 24,
        **kwargs
    ) -> Session:
        """创建会话"""
        async with self._lock:
            session = Session.create(
                user_id=user_id,
                expire_hours=expire_hours,
                **kwargs
            )
            
            self._sessions[session.session_id] = session
            
            # 记录用户会话映射
            if user_id:
                if user_id not in self._user_sessions:
                    self._user_sessions[user_id] = []
                self._user_sessions[user_id].append(session.session_id)
            
            logger.info(f"Session created: {session.session_id[:8]}...")
            return session
    
    async def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            # 懒删除过期会话
            await self.delete(session_id)
            return None
        return session
    
    async def update(self, session_id: str, data: dict) -> bool:
        """更新会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # 更新字段
            for key, value in data.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            session.last_active = datetime.utcnow()
            return True
    
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                # 清理用户会话映射
                if session.user_id and session.user_id in self._user_sessions:
                    self._user_sessions[session.user_id] = [
                        sid for sid in self._user_sessions[session.user_id] 
                        if sid != session_id
                    ]
                logger.info(f"Session deleted: {session_id[:8]}...")
                return True
            return False
    
    async def refresh(self, session_id: str, extend_hours: int = 24) -> bool:
        """刷新过期时间"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.refresh(extend_hours)
            return True
    
    async def get_by_user(self, user_id: str) -> List[Session]:
        """获取用户所有会话"""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        for sid in session_ids:
            session = await self.get(sid)
            if session:
                sessions.append(session)
        return sessions
    
    async def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量"""
        async with self._lock:
            now = datetime.utcnow()
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            
            for sid in expired_ids:
                session = self._sessions.pop(sid, None)
                if session and session.user_id:
                    if session.user_id in self._user_sessions:
                        self._user_sessions[session.user_id] = [
                            s for s in self._user_sessions[session.user_id] if s != sid
                        ]
            
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
            
            return len(expired_ids)
    
    async def validate(self, session_id: str) -> bool:
        """验证会话有效性"""
        session = await self.get(session_id)
        return session is not None and session.is_valid()
    
    async def increment_daily_tasks(self, session_id: str) -> bool:
        """
        增加今日任务计数
        
        Returns:
            如果超过配额返回 False，否则返回 True
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # 检查是否需要重置每日配额
            now = datetime.utcnow()
            if now.date() > session.quota.quota_reset_at.date():
                session.reset_daily_quota()
            
            # 检查配额
            if session.quota.used_daily_tasks >= session.quota.max_daily_tasks:
                return False
            
            session.quota.used_daily_tasks += 1
            return True
    
    async def reset_daily_quota(self, session_id: str) -> bool:
        """重置每日配额"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.reset_daily_quota()
            return True
    
    async def get_running_tasks_count(self, session_id: str) -> int:
        """获取用户运行中的任务数"""
        # 注：这个方法需要和 TaskStorage 配合
        # 在 MemorySessionStore 中，我们暂时返回 0
        # 实际实现需要在 TaskManager 层面处理
        return 0
    
    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return session_id in self._sessions and not self._sessions[session_id].is_expired()

