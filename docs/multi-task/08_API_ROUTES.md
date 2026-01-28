# 08. API 路由开发文档

> 模块: HTTP/WebSocket 接口  
> Phase: 3  
> 预估工期: 2 天  
> 产出文件:  
> - `api/routers/auth.py`  
> - `api/routers/tasks.py`  
> - `api/routers/websocket.py`  
> - `api/middleware/session.py`

---

## 一、模块职责

API 路由层负责：
1. **HTTP 接口**：认证、任务 CRUD、统计查询
2. **WebSocket**：实时日志推送、事件订阅
3. **中间件**：Session 校验、请求日志、错误处理

---

## 二、路由概览

```
/api
├── /auth
│   ├── POST   /session          # 创建匿名会话
│   ├── POST   /login            # 用户登录（可选）
│   ├── POST   /logout           # 用户登出
│   └── GET    /me               # 获取当前用户
│
├── /tasks
│   ├── POST   /                 # 创建任务
│   ├── GET    /                 # 任务列表
│   ├── GET    /stats            # 任务统计
│   ├── GET    /{task_id}        # 任务详情
│   ├── GET    /{task_id}/logs   # 任务日志
│   ├── POST   /{task_id}/cancel # 取消任务
│   ├── POST   /{task_id}/retry  # 重试任务
│   ├── PATCH  /{task_id}/priority # 调整优先级
│   └── DELETE /{task_id}        # 删除任务
│
└── /admin（可选）
    ├── GET    /tasks            # 所有任务
    ├── GET    /sessions         # 所有会话
    └── GET    /queue/stats      # 队列统计

/ws
├── /tasks/{task_id}/logs        # 订阅任务日志
├── /session/logs                # 订阅用户所有日志
└── /session/events              # 订阅用户事件
```

---

## 三、Session 中间件

### 3.1 实现 (`api/middleware/session.py`)

```python
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from api.services.factory import get_services


# 支持多种认证方式
api_key_header = APIKeyHeader(name="X-Session-ID", auto_error=False)


class SessionMiddleware(BaseHTTPMiddleware):
    """Session 校验中间件"""
    
    # 不需要认证的路径
    PUBLIC_PATHS = {
        "/api/auth/session",
        "/api/auth/login",
        "/docs",
        "/openapi.json",
        "/health",
    }
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 公开路径跳过认证
        if path in self.PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)
        
        # 获取 session_id
        session_id = await self._extract_session_id(request)
        
        if not session_id:
            raise HTTPException(status_code=401, detail="Session required")
        
        # 验证 session
        session_store = get_services()["session_store"]
        
        session = await session_store.get(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # 可选：UA/IP 绑定校验
        valid = await session_store.validate(
            session_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None
        )
        if not valid:
            raise HTTPException(status_code=401, detail="Session validation failed")
        
        # 刷新 session
        await session_store.refresh(session_id)
        
        # 将 session 挂载到 request.state
        request.state.session_id = session_id
        request.state.session = session
        
        return await call_next(request)
    
    async def _extract_session_id(self, request: Request) -> Optional[str]:
        """从请求中提取 session_id"""
        # 方式 1：Header
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id
        
        # 方式 2：Cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # 方式 3：Query 参数（仅用于 WebSocket）
        session_id = request.query_params.get("session_id")
        if session_id:
            return session_id
        
        return None


def get_current_session_id(request: Request) -> str:
    """依赖注入：获取当前 session_id"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    return session_id
```

---

## 四、认证路由

### 4.1 实现 (`api/routers/auth.py`)

```python
from fastapi import APIRouter, Response, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.services.factory import get_services
from api.schemas.session import SessionResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SessionCreateRequest(BaseModel):
    expire_hours: int = 24


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: Request,
    response: Response,
    body: SessionCreateRequest = SessionCreateRequest()
):
    """
    创建匿名会话
    
    返回 session_id，并设置到 Cookie
    """
    session_store = get_services()["session_store"]
    
    session = await session_store.create(
        expire_hours=body.expire_hours,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    
    # 设置 Cookie
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        secure=True,  # 生产环境启用
        samesite="lax",
        max_age=body.expire_hours * 3600,
        path="/api"
    )
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        quota=session.quota
    )


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    """
    用户登录（可选功能）
    
    TODO: 实现用户认证逻辑
    """
    raise HTTPException(status_code=501, detail="Login not implemented")


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    用户登出
    
    删除 session 并清除 Cookie
    """
    session_id = getattr(request.state, "session_id", None)
    
    if session_id:
        session_store = get_services()["session_store"]
        await session_store.delete(session_id)
    
    response.delete_cookie("session_id", path="/api")
    
    return {"message": "Logged out"}


@router.get("/me", response_model=SessionResponse)
async def get_current_user(request: Request):
    """获取当前用户信息"""
    session = getattr(request.state, "session", None)
    
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        quota=session.quota
    )
```

---

## 五、任务路由

### 5.1 实现 (`api/routers/tasks.py`)

```python
from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional, List

from api.services.factory import get_task_manager
from api.services.task_manager import (
    TaskNotFoundError, QuotaExceededError, 
    PermissionDeniedError, DuplicateTaskError
)
from api.schemas.task import (
    Task, TaskStatus, TaskCreateRequest,
    TaskListRequest, TaskListResponse, TaskStatsResponse
)
from api.schemas.event import LogEntry
from api.middleware.session import get_current_session_id

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ========== 异常处理 ==========

def handle_task_error(e: Exception):
    if isinstance(e, TaskNotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    elif isinstance(e, PermissionDeniedError):
        raise HTTPException(status_code=403, detail=str(e))
    elif isinstance(e, QuotaExceededError):
        raise HTTPException(status_code=429, detail=str(e))
    elif isinstance(e, DuplicateTaskError):
        raise HTTPException(status_code=409, detail=str(e))
    else:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 路由 ==========

@router.post("/", response_model=Task)
async def create_task(request: Request, body: TaskCreateRequest):
    """
    创建任务
    
    - 支持幂等键（idempotency_key）
    - 支持定时执行（scheduled_at）
    - 自动检查配额
    """
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    try:
        task = await manager.create_task(session_id, body)
        return task
    except Exception as e:
        handle_task_error(e)


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    platform: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取任务列表"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    list_request = TaskListRequest(
        status=status,
        platform=platform,
        page=page,
        page_size=page_size
    )
    
    tasks = await manager.list_tasks(session_id, list_request)
    total = await manager.count_tasks(session_id)
    
    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=TaskStatsResponse)
async def get_stats(request: Request):
    """获取任务统计"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    return await manager.get_stats(session_id)


@router.get("/{task_id}", response_model=Task)
async def get_task(request: Request, task_id: str):
    """获取任务详情"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    try:
        return await manager.get_task(session_id, task_id)
    except Exception as e:
        handle_task_error(e)


@router.get("/{task_id}/logs", response_model=List[LogEntry])
async def get_task_logs(
    request: Request,
    task_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    level: Optional[str] = None
):
    """获取任务日志"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    try:
        return await manager.get_logs(
            session_id, task_id, 
            limit=limit, offset=offset, level=level
        )
    except Exception as e:
        handle_task_error(e)


@router.post("/{task_id}/cancel")
async def cancel_task(request: Request, task_id: str):
    """取消任务"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    try:
        result = await manager.cancel_task(session_id, task_id)
        return {"success": result}
    except Exception as e:
        handle_task_error(e)


@router.post("/{task_id}/retry", response_model=Task)
async def retry_task(request: Request, task_id: str):
    """重试任务"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    try:
        return await manager.retry_task(session_id, task_id)
    except Exception as e:
        handle_task_error(e)


class PriorityUpdateRequest(BaseModel):
    priority: int


@router.patch("/{task_id}/priority")
async def update_priority(
    request: Request, 
    task_id: str, 
    body: PriorityUpdateRequest
):
    """调整任务优先级"""
    session_id = get_current_session_id(request)
    manager = get_task_manager()
    
    try:
        result = await manager.update_priority(session_id, task_id, body.priority)
        return {"success": result}
    except Exception as e:
        handle_task_error(e)


@router.delete("/{task_id}")
async def delete_task(request: Request, task_id: str):
    """删除任务"""
    session_id = get_current_session_id(request)
    services = get_services()
    manager = get_task_manager()
    
    try:
        # 先取消（如果在运行）
        await manager.cancel_task(session_id, task_id)
        # 再删除
        await services["storage"].delete(task_id)
        return {"success": True}
    except Exception as e:
        handle_task_error(e)
```

---

## 六、WebSocket 路由

### 6.1 实现 (`api/routers/websocket.py`)

```python
import asyncio
import json
import logging
from typing import Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from api.services.factory import get_services
from api.schemas.event import TaskEvent, EventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self, max_queue_size: int = 256):
        self._connections: Set[WebSocket] = set()
        self._subscriptions: dict = {}  # websocket -> subscription_id
        self._max_queue_size = max_queue_size
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)
        # 清理订阅
        sub_id = self._subscriptions.pop(websocket, None)
        return sub_id
    
    def set_subscription(self, websocket: WebSocket, sub_id: str):
        self._subscriptions[websocket] = sub_id
    
    async def send_event(self, websocket: WebSocket, event: TaskEvent):
        """发送事件到客户端"""
        try:
            await websocket.send_json(event.dict())
        except Exception as e:
            logger.warning(f"Send error: {e}")


manager = ConnectionManager()


async def validate_session(session_id: str) -> bool:
    """验证 session"""
    session_store = get_services()["session_store"]
    session = await session_store.get(session_id)
    return session is not None


async def validate_task_access(session_id: str, task_id: str) -> bool:
    """验证任务访问权限"""
    storage = get_services()["storage"]
    task = await storage.get(task_id)
    return task is not None and task.session_id == session_id


@router.websocket("/ws/tasks/{task_id}/logs")
async def task_logs_websocket(
    websocket: WebSocket,
    task_id: str,
    session_id: str = Query(...)
):
    """
    订阅特定任务的日志
    
    Query 参数：session_id（必须）
    """
    # 验证 session
    if not await validate_session(session_id):
        await websocket.close(code=4001, reason="Invalid session")
        return
    
    # 验证任务访问权限
    if not await validate_task_access(session_id, task_id):
        await websocket.close(code=4003, reason="Access denied")
        return
    
    await manager.connect(websocket)
    
    try:
        # 订阅任务事件
        event_bus = get_services()["event_bus"]
        
        async def handler(event: TaskEvent):
            await manager.send_event(websocket, event)
        
        sub_id = await event_bus.subscribe_task(task_id, handler)
        manager.set_subscription(websocket, sub_id)
        
        logger.info(f"WebSocket connected: task={task_id}")
        
        # 保持连接
        while True:
            try:
                # 等待客户端消息（心跳或关闭）
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
                
                # 处理客户端消息
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_json({"type": "ping"})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: task={task_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        sub_id = manager.disconnect(websocket)
        if sub_id:
            event_bus = get_services()["event_bus"]
            await event_bus.unsubscribe(sub_id)


@router.websocket("/ws/session/logs")
async def session_logs_websocket(
    websocket: WebSocket,
    session_id: str = Query(...)
):
    """
    订阅用户所有任务的日志
    """
    if not await validate_session(session_id):
        await websocket.close(code=4001, reason="Invalid session")
        return
    
    await manager.connect(websocket)
    
    try:
        event_bus = get_services()["event_bus"]
        
        async def handler(event: TaskEvent):
            # 只转发日志事件
            if event.event_type == EventType.TASK_LOG:
                await manager.send_event(websocket, event)
        
        sub_id = await event_bus.subscribe_session(session_id, handler)
        manager.set_subscription(websocket, sub_id)
        
        logger.info(f"WebSocket connected: session={session_id}")
        
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    
    except WebSocketDisconnect:
        pass
    finally:
        sub_id = manager.disconnect(websocket)
        if sub_id:
            await get_services()["event_bus"].unsubscribe(sub_id)


@router.websocket("/ws/session/events")
async def session_events_websocket(
    websocket: WebSocket,
    session_id: str = Query(...)
):
    """
    订阅用户所有任务事件（状态变更、进度等）
    """
    if not await validate_session(session_id):
        await websocket.close(code=4001, reason="Invalid session")
        return
    
    await manager.connect(websocket)
    
    try:
        event_bus = get_services()["event_bus"]
        
        async def handler(event: TaskEvent):
            # 所有事件都转发（除了日志）
            if event.event_type != EventType.TASK_LOG:
                await manager.send_event(websocket, event)
        
        sub_id = await event_bus.subscribe_session(session_id, handler)
        manager.set_subscription(websocket, sub_id)
        
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    
    except WebSocketDisconnect:
        pass
    finally:
        sub_id = manager.disconnect(websocket)
        if sub_id:
            await get_services()["event_bus"].unsubscribe(sub_id)
```

---

## 七、应用入口

### 7.1 FastAPI 应用 (`api/main.py`)

```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, tasks, websocket
from api.middleware.session import SessionMiddleware
from api.services.factory import get_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    services = get_services()
    await services["event_bus"].start()
    
    # 启动后台清理任务
    cleanup_task = asyncio.create_task(
        periodic_cleanup(services)
    )
    
    yield
    
    # 关闭
    cleanup_task.cancel()
    await services["event_bus"].stop()


async def periodic_cleanup(services: dict, interval: int = 3600):
    """定期清理任务"""
    while True:
        try:
            await asyncio.sleep(interval)
            
            # 清理过期会话
            count = await services["session_store"].cleanup_expired()
            if count > 0:
                print(f"Cleaned {count} expired sessions")
            
            # 清理旧任务
            count = await services["storage"].cleanup_old_tasks(days=7)
            if count > 0:
                print(f"Cleaned {count} old tasks")
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Cleanup error: {e}")


app = FastAPI(
    title="MediaCrawler API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session 中间件
app.add_middleware(SessionMiddleware)

# 路由
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(websocket.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## 八、验收标准

- [ ] 所有 HTTP 接口可用
- [ ] Session 认证正确
- [ ] 权限校验完整
- [ ] WebSocket 连接/断开/重连正常
- [ ] 事件实时推送
- [ ] 错误响应格式统一

---

*文档结束*

