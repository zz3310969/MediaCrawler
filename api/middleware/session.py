"""
Session 中间件 - 支持 Session + API Key 双重认证
"""
import json
import logging
from typing import Optional
from contextvars import ContextVar

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.services.factory import get_session_store
from api.schemas.session import Session

logger = logging.getLogger(__name__)

# 使用 ContextVar 存储当前请求的 session / api_key 信息
_current_session: ContextVar[Optional[Session]] = ContextVar("current_session", default=None)
_current_session_id: ContextVar[Optional[str]] = ContextVar("current_session_id", default=None)
_current_api_key_id: ContextVar[Optional[str]] = ContextVar("current_api_key_id", default=None)
_current_api_key_scopes: ContextVar[Optional[list]] = ContextVar("current_api_key_scopes", default=None)


def get_current_session() -> Optional[Session]:
    """获取当前请求的 Session"""
    return _current_session.get()


def get_session_id() -> Optional[str]:
    """获取当前请求的 Session ID"""
    return _current_session_id.get()


def get_api_key_id() -> Optional[str]:
    """获取当前请求的 API Key ID"""
    return _current_api_key_id.get()


def get_api_key_scopes() -> Optional[list]:
    """获取当前请求的 API Key 权限范围"""
    return _current_api_key_scopes.get()


def is_api_key_request() -> bool:
    """判断当前请求是否通过 API Key 认证"""
    return _current_api_key_id.get() is not None


class SessionMiddleware(BaseHTTPMiddleware):
    """Session + API Key 认证中间件"""
    
    # 不需要认证的路径（精确匹配）
    EXCLUDED_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/health",
        "/health",
    }
    
    # 路径前缀排除（这些路径不需要认证）
    EXCLUDED_PREFIXES = [
        "/static/",
        "/assets/",
        "/logos/",
        # 原有 API - 不需要 session
        "/api/crawler/",      # 爬虫控制 API
        "/api/config/",       # 配置 API
        "/api/data/",         # 数据查询 API
        "/api/env/",          # 环境检查 API
        "/api/db/",           # 数据库检查 API
        "/api/ws/",           # 原有 WebSocket API
        "/api/wechat/",       # 微信相关 API
        "/api/proxy/",        # 代理管理 API
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 跳过 OPTIONS 请求（CORS 预检）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 检查是否需要跳过验证
        if self._should_skip(path):
            return await call_next(request)
        
        # 优先检查 API Key (Bearer token)
        api_key_token = self._extract_bearer_token(request)
        if api_key_token and api_key_token.startswith("mc_"):
            auth_result = await self._authenticate_api_key(api_key_token, request, call_next)
            if auth_result is not None:
                return auth_result

        # 然后检查 Session
        session_id = self._extract_session_id(request)
        
        if session_id:
            session_store = get_session_store()
            session = await session_store.get(session_id)
            
            if session and session.is_valid():
                await session_store.refresh(session_id)
                
                _current_session.set(session)
                _current_session_id.set(session_id)
                
                try:
                    response = await call_next(request)
                finally:
                    _current_session.set(None)
                    _current_session_id.set(None)
                
                return response
        
        # 对于需要认证的 API，返回 401
        if path.startswith("/api/") and not self._should_skip(path):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing session. Use Session ID or API Key (Authorization: Bearer mc_xxx)."}
            )
        
        # 对于其他路径，继续处理
        return await call_next(request)
    
    async def _authenticate_api_key(self, raw_key: str, request: Request, call_next):
        """通过 API Key 认证请求"""
        try:
            from database.db_session import get_session as get_db_session
            from api.services.crud.api_key import api_key_crud

            async with get_db_session() as db_session:
                if db_session is None:
                    return None

                key_model = await api_key_crud.verify_key(db_session, raw_key)
                if not key_model:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or expired API Key"}
                    )

                scopes = json.loads(key_model.scopes) if key_model.scopes else []

                _current_api_key_id.set(key_model.key_id)
                _current_api_key_scopes.set(scopes)
                _current_session_id.set(f"apikey:{key_model.key_id}")

                try:
                    response = await call_next(request)
                finally:
                    _current_api_key_id.set(None)
                    _current_api_key_scopes.set(None)
                    _current_session_id.set(None)

                return response

        except Exception as e:
            logger.warning(f"API Key authentication failed: {e}")
            return None

    def _should_skip(self, path: str) -> bool:
        """检查是否应该跳过验证"""
        if path in self.EXCLUDED_PATHS:
            return True
        
        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_bearer_token(self, request: Request) -> Optional[str]:
        """从 Authorization header 提取 Bearer token"""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        return None
    
    def _extract_session_id(self, request: Request) -> Optional[str]:
        """从请求中提取 session_id"""
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id
        
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        session_id = request.query_params.get("session_id")
        if session_id:
            return session_id
        
        return None


# ========== FastAPI 依赖项 ==========

async def require_session(request: Request) -> Session:
    """要求有效的 Session（FastAPI 依赖项），也兼容 API Key 认证"""
    session = get_current_session()
    if session:
        return session
    
    # API Key 认证场景：没有真实 session，构造临时 session 供路由使用
    api_key_id = get_api_key_id()
    if api_key_id:
        from api.schemas.session import SessionQuota
        from datetime import timedelta, timezone
        now = __import__('datetime').datetime.now(timezone.utc)
        return Session(
            session_id=f"apikey:{api_key_id}",
            user_id=None,
            created_at=now,
            expires_at=now + timedelta(hours=24),
            last_active=now,
            quota=SessionQuota(max_concurrent_tasks=10, max_daily_tasks=1000)
        )
    
    raise HTTPException(status_code=401, detail="需要登录，请先使用账号密码登录")


async def require_session_id(request: Request) -> str:
    """要求有效的 Session ID（FastAPI 依赖项），支持 Session 和 API Key"""
    session_id = get_session_id()
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required (Session or API Key)")
    return session_id


async def require_api_key_scope(scope: str):
    """生成检查 API Key scope 的依赖"""
    async def checker(request: Request) -> str:
        key_id = get_api_key_id()
        if key_id:
            scopes = get_api_key_scopes() or []
            from api.schemas.api_key import ApiKey
            dummy = ApiKey(key_id=key_id, key_hash="", key_prefix="", scopes=scopes)
            if not dummy.has_scope(scope):
                raise HTTPException(status_code=403, detail=f"Missing required scope: {scope}")
            return get_session_id()
        session_id = get_session_id()
        if not session_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        return session_id
    return checker


async def optional_session(request: Request) -> Optional[Session]:
    """可选的 Session（FastAPI 依赖项）"""
    return get_current_session()

