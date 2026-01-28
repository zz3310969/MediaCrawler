# 02. Session 服务开发文档

> 模块: 用户认证/会话管理  
> Phase: 2  
> 预估工期: 1 天  
> 产出文件:  
> - `api/services/session/memory.py`  
> - `api/services/session/redis.py`（Phase 6）

---

## 一、模块职责

Session 服务负责：
1. **会话创建与管理**：匿名/登录会话的生命周期
2. **用户认证**：Session ID 校验、过期检测
3. **配额管理**：并发任务数、每日任务上限
4. **安全控制**：会话绑定、刷新策略

---

## 二、类图

```
┌─────────────────────────────────────────────────────────────────┐
│                     ISessionStore (接口)                         │
├─────────────────────────────────────────────────────────────────┤
│ + create(user_id?, expire_hours) -> Session                     │
│ + get(session_id) -> Session?                                   │
│ + update(session_id, data) -> bool                              │
│ + delete(session_id) -> bool                                    │
│ + refresh(session_id, extend_hours) -> bool                     │
│ + validate(session_id) -> bool                                  │
│ + increment_daily_tasks(session_id) -> bool                     │
│ + cleanup_expired() -> int                                      │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
           ┌──────────────────┴──────────────────┐
           │                                     │
┌──────────────────────┐              ┌──────────────────────┐
│  MemorySessionStore  │              │  RedisSessionStore   │
├──────────────────────┤              ├──────────────────────┤
│ - sessions: Dict     │              │ - redis: Redis       │
│ - lock: asyncio.Lock │              │ - key_prefix: str    │
└──────────────────────┘              └──────────────────────┘
```

---

## 三、Memory 版实现

### 3.1 核心代码 (`api/services/session/memory.py`)

```python
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import secrets
import hashlib

from api.interfaces.session import ISessionStore
from api.schemas.session import Session, SessionQuota, SessionPreferences


class MemorySessionStore(ISessionStore):
    """内存版 Session 存储"""
    
    def __init__(self, max_sessions: int = 10000):
        self._sessions: Dict[str, Session] = {}
        self._user_index: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._lock = asyncio.Lock()
        self._max_sessions = max_sessions
    
    async def create(
        self,
        user_id: Optional[str] = None,
        expire_hours: int = 24,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs
    ) -> Session:
        async with self._lock:
            # 容量检查
            if len(self._sessions) >= self._max_sessions:
                await self._evict_oldest()
            
            # 生成安全的 session_id
            session_id = secrets.token_urlsafe(32)
            
            # 计算 UA 指纹（可选绑定）
            ua_hash = None
            if user_agent:
                ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            
            # IP 段（可选绑定）
            ip_prefix = None
            if ip_address:
                ip_prefix = ".".join(ip_address.split(".")[:2])  # 只取前两段
            
            session = Session(
                session_id=session_id,
                user_id=user_id,
                expires_at=datetime.utcnow() + timedelta(hours=expire_hours),
                user_agent_hash=ua_hash,
                ip_prefix=ip_prefix,
            )
            
            self._sessions[session_id] = session
            
            # 用户索引
            if user_id:
                if user_id not in self._user_index:
                    self._user_index[user_id] = []
                self._user_index[user_id].append(session_id)
            
            return session
    
    async def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            await self.delete(session_id)
            return None
        return session
    
    async def update(self, session_id: str, data: dict) -> bool:
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
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session and session.user_id:
                user_sessions = self._user_index.get(session.user_id, [])
                if session_id in user_sessions:
                    user_sessions.remove(session_id)
            return session is not None
    
    async def refresh(self, session_id: str, extend_hours: int = 24) -> bool:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.expires_at = datetime.utcnow() + timedelta(hours=extend_hours)
            session.last_active = datetime.utcnow()
            return True
    
    async def get_by_user(self, user_id: str) -> List[Session]:
        session_ids = self._user_index.get(user_id, [])
        sessions = []
        for sid in session_ids:
            session = await self.get(sid)
            if session:
                sessions.append(session)
        return sessions
    
    async def cleanup_expired(self) -> int:
        async with self._lock:
            now = datetime.utcnow()
            expired = [
                sid for sid, s in self._sessions.items()
                if s.expires_at < now
            ]
            for sid in expired:
                session = self._sessions.pop(sid, None)
                if session and session.user_id:
                    user_sessions = self._user_index.get(session.user_id, [])
                    if sid in user_sessions:
                        user_sessions.remove(sid)
            return len(expired)
    
    async def validate(
        self,
        session_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        session = await self.get(session_id)
        if not session:
            return False
        
        # UA 绑定校验
        if session.user_agent_hash and user_agent:
            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            if session.user_agent_hash != ua_hash:
                return False
        
        # IP 段校验
        if session.ip_prefix and ip_address:
            ip_prefix = ".".join(ip_address.split(".")[:2])
            if session.ip_prefix != ip_prefix:
                return False
        
        return True
    
    async def increment_daily_tasks(self, session_id: str) -> bool:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # 检查是否需要重置
            now = datetime.utcnow()
            if session.quota.quota_reset_at.date() < now.date():
                session.quota.used_daily_tasks = 0
                session.quota.quota_reset_at = now
            
            # 检查配额
            if session.quota.used_daily_tasks >= session.quota.max_daily_tasks:
                return False
            
            session.quota.used_daily_tasks += 1
            return True
    
    async def reset_daily_quota(self, session_id: str) -> bool:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session.quota.used_daily_tasks = 0
            session.quota.quota_reset_at = datetime.utcnow()
            return True
    
    async def _evict_oldest(self) -> None:
        """淘汰最旧的会话"""
        if not self._sessions:
            return
        oldest_id = min(
            self._sessions.keys(),
            key=lambda k: self._sessions[k].last_active
        )
        await self.delete(oldest_id)
```

---

## 四、Redis 版实现要点（Phase 6）

### 4.1 Key 设计

```
session:{session_id}           # HASH - 会话数据
session:user:{user_id}         # SET - 用户的所有会话 ID
session:ttl:{session_id}       # STRING - 配合 EXPIRE 实现自动过期
```

### 4.2 关键实现

```python
class RedisSessionStore(ISessionStore):
    """Redis 版 Session 存储"""
    
    def __init__(self, redis: Redis, key_prefix: str = "mc:"):
        self._redis = redis
        self._prefix = key_prefix
    
    def _key(self, *parts: str) -> str:
        return f"{self._prefix}session:{':'.join(parts)}"
    
    async def create(self, user_id: Optional[str] = None, expire_hours: int = 24, **kwargs) -> Session:
        session = Session(
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=expire_hours),
            **kwargs
        )
        
        # 使用 Pipeline 原子操作
        async with self._redis.pipeline() as pipe:
            key = self._key(session.session_id)
            pipe.hset(key, mapping=session.dict())
            pipe.expire(key, expire_hours * 3600)
            
            if user_id:
                pipe.sadd(self._key("user", user_id), session.session_id)
            
            await pipe.execute()
        
        return session
    
    async def get(self, session_id: str) -> Optional[Session]:
        data = await self._redis.hgetall(self._key(session_id))
        if not data:
            return None
        return Session(**data)
    
    async def validate(self, session_id: str, **kwargs) -> bool:
        # 使用 EXISTS 快速检查
        exists = await self._redis.exists(self._key(session_id))
        if not exists:
            return False
        
        session = await self.get(session_id)
        # ... 校验逻辑
        return True
    
    async def cleanup_expired(self) -> int:
        # Redis 自动过期，无需手动清理
        # 但需要清理 user 索引中的失效引用
        # ... 定期扫描 SCAN
        return 0
```

---

## 五、安全最佳实践

### 5.1 Session ID 生成

```python
import secrets

# ✅ 推荐：至少 256 bits 熵
session_id = secrets.token_urlsafe(32)  # 生成 43 字符

# ❌ 不推荐
import uuid
session_id = str(uuid.uuid4())  # 只有 122 bits 熵
```

### 5.2 Cookie 配置（前端对接）

```python
# FastAPI 响应设置 Cookie
from fastapi import Response

def set_session_cookie(response: Response, session_id: str):
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,      # 防止 XSS
        secure=True,        # 仅 HTTPS
        samesite="lax",     # 防止 CSRF
        max_age=24 * 3600,  # 24 小时
        path="/api"         # 限制路径
    )
```

### 5.3 会话绑定策略

| 策略 | 安全性 | 用户体验 | 推荐场景 |
|------|--------|----------|----------|
| 无绑定 | 低 | 最好 | 仅本地开发 |
| UA 绑定 | 中 | 好 | 默认推荐 |
| UA + IP 段 | 高 | 一般 | 敏感操作 |
| UA + 完整 IP | 最高 | 差 | 不推荐（移动网络漂移） |

---

## 六、配额管理

### 6.1 配额检查流程

```
创建任务请求
      │
      ▼
┌─────────────────┐
│ 检查并发配额    │
│ running < max   │
└─────────────────┘
      │ 通过
      ▼
┌─────────────────┐
│ 检查每日配额    │
│ used < daily_max│
└─────────────────┘
      │ 通过
      ▼
┌─────────────────┐
│ 增加计数        │
│ used_daily += 1 │
└─────────────────┘
      │
      ▼
    创建任务
```

### 6.2 配额重置策略

```python
async def check_and_reset_quota(session: Session) -> None:
    """检查并重置每日配额"""
    now = datetime.utcnow()
    reset_time = session.quota.quota_reset_at
    
    # 跨天重置
    if reset_time.date() < now.date():
        session.quota.used_daily_tasks = 0
        session.quota.quota_reset_at = now
```

---

## 七、定期清理

### 7.1 后台清理任务

```python
import asyncio

async def session_cleanup_task(store: ISessionStore, interval: int = 3600):
    """后台清理过期会话"""
    while True:
        try:
            count = await store.cleanup_expired()
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
        
        await asyncio.sleep(interval)
```

### 7.2 在应用启动时注册

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup():
    asyncio.create_task(session_cleanup_task(session_store))
```

---

## 八、单元测试用例

```python
import pytest
from api.services.session.memory import MemorySessionStore


@pytest.mark.asyncio
async def test_create_session():
    store = MemorySessionStore()
    session = await store.create(expire_hours=1)
    
    assert session.session_id is not None
    assert len(session.session_id) == 43  # base64url 编码 32 字节


@pytest.mark.asyncio
async def test_session_expiry():
    store = MemorySessionStore()
    session = await store.create(expire_hours=-1)  # 已过期
    
    result = await store.get(session.session_id)
    assert result is None


@pytest.mark.asyncio
async def test_daily_quota():
    store = MemorySessionStore()
    session = await store.create()
    session.quota.max_daily_tasks = 2
    
    assert await store.increment_daily_tasks(session.session_id) == True
    assert await store.increment_daily_tasks(session.session_id) == True
    assert await store.increment_daily_tasks(session.session_id) == False  # 超限


@pytest.mark.asyncio
async def test_ua_binding():
    store = MemorySessionStore()
    session = await store.create(user_agent="Mozilla/5.0 Test")
    
    assert await store.validate(session.session_id, user_agent="Mozilla/5.0 Test") == True
    assert await store.validate(session.session_id, user_agent="Different UA") == False
```

---

## 九、验收标准

- [ ] Memory 版所有接口实现完整
- [ ] 单元测试覆盖率 > 80%
- [ ] 性能测试：10000 并发会话操作 < 100ms
- [ ] 安全测试：Session ID 随机性验证
- [ ] 集成测试：与 API 中间件对接正常

---

*文档结束*

