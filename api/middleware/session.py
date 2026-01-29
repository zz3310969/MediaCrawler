"""
Session 中间件
"""
import logging
from typing import Optional
from contextvars import ContextVar

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.services.factory import get_session_store
from api.schemas.session import Session

logger = logging.getLogger(__name__)

# 使用 ContextVar 存储当前请求的 session
_current_session: ContextVar[Optional[Session]] = ContextVar("current_session", default=None)
_current_session_id: ContextVar[Optional[str]] = ContextVar("current_session_id", default=None)


def get_current_session() -> Optional[Session]:
    """获取当前请求的 Session"""
    return _current_session.get()


def get_session_id() -> Optional[str]:
    """获取当前请求的 Session ID"""
    return _current_session_id.get()


class SessionMiddleware(BaseHTTPMiddleware):
    """Session 中间件"""
    
    # 不需要 session 的路径（精确匹配）
    EXCLUDED_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/session",
        "/api/health",
        "/health",
    }
    
    # 路径前缀排除（这些路径不需要 session 认证）
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
        
        # 获取 session_id
        session_id = self._extract_session_id(request)
        
        if session_id:
            # 验证 session
            session_store = get_session_store()
            session = await session_store.get(session_id)
            
            if session and session.is_valid():
                # 刷新活跃时间
                await session_store.refresh(session_id)
                
                # 设置 context
                _current_session.set(session)
                _current_session_id.set(session_id)
                
                # 继续处理请求
                response = await call_next(request)
                
                # 清理 context
                _current_session.set(None)
                _current_session_id.set(None)
                
                return response
        
        # 对于需要认证的 API，返回 401
        if path.startswith("/api/") and not self._should_skip(path):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing session"}
            )
        
        # 对于其他路径，继续处理
        return await call_next(request)
    
    def _should_skip(self, path: str) -> bool:
        """检查是否应该跳过验证"""
        # 精确匹配
        if path in self.EXCLUDED_PATHS:
            return True
        
        # 前缀匹配
        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_session_id(self, request: Request) -> Optional[str]:
        """从请求中提取 session_id"""
        # 1. 从 Header 获取
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id
        
        # 2. 从 Cookie 获取
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # 3. 从 Query 参数获取（用于 WebSocket）
        session_id = request.query_params.get("session_id")
        if session_id:
            return session_id
        
        return None


# ========== FastAPI 依赖项 ==========

async def require_session(request: Request) -> Session:
    """
    要求有效的 Session（FastAPI 依赖项）
    
    Usage:
        @app.get("/api/tasks")
        async def list_tasks(session: Session = Depends(require_session)):
            ...
    """
    session = get_current_session()
    if not session:
        raise HTTPException(status_code=401, detail="Session required")
    return session


async def require_session_id(request: Request) -> str:
    """
    要求有效的 Session ID（FastAPI 依赖项）
    """
    session_id = get_session_id()
    if not session_id:
        raise HTTPException(status_code=401, detail="Session required")
    return session_id


async def optional_session(request: Request) -> Optional[Session]:
    """
    可选的 Session（FastAPI 依赖项）
    """
    return get_current_session()

