"""
认证相关路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, Depends

from api.services.factory import get_session_store
from api.schemas.session import Session, SessionCreateRequest, SessionResponse
from api.schemas.user import LoginRequest, LoginResponse, User as UserSchema
from api.middleware.session import get_current_session, get_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest = None,
    response: Response = None
):
    """
    创建/获取匿名 Session
    
    如果请求中已有有效 session，则返回现有 session
    """
    # 如果有有效 session，返回现有的
    current_session = get_current_session()
    if current_session:
        return SessionResponse(
            session_id=current_session.session_id,
            user_id=current_session.user_id,
            created_at=current_session.created_at,
            expires_at=current_session.expires_at,
            quota=current_session.quota
        )
    
    # 创建新 session
    session_store = get_session_store()
    
    user_id = request.user_id if request else None
    expire_hours = request.expire_hours if request else 24
    
    session = await session_store.create(
        user_id=user_id,
        expire_hours=expire_hours
    )
    
    # 设置 Cookie（可选）
    if response:
        response.set_cookie(
            key="session_id",
            value=session.session_id,
            httponly=True,
            max_age=expire_hours * 3600,
            samesite="lax"
        )
    
    logger.info(f"Session created: {session.session_id[:8]}...")
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        quota=session.quota
    )


@router.post("/login")
async def login(
    login_req: LoginRequest,
    request: Request,
    response: Response
):
    """
    用户名密码登录
    
    验证成功后创建带 user_id 的 Session
    """
    try:
        from database.db_session import get_session as get_db_session
        from api.services.crud.user import user_crud
    except Exception as e:
        logger.error(f"Failed to import database modules: {e}")
        raise HTTPException(status_code=500, detail="数据库服务不可用")
    
    async with get_db_session() as db_session:
        if db_session is None:
            raise HTTPException(status_code=500, detail="数据库连接失败")
        
        user = await user_crud.authenticate(
            db_session,
            username=login_req.username,
            password=login_req.password
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 创建带 user_id 的 Session
        session_store = get_session_store()
        session = await session_store.create(
            user_id=user.user_id,
            expire_hours=24 * 7  # 登录用户 7 天有效
        )
        
        # 更新登录信息
        client_ip = request.client.host if request.client else ""
        await user_crud.update_login_info(
            db_session, db_obj=user, login_ip=client_ip
        )
        
        # 设置 Cookie
        response.set_cookie(
            key="session_id",
            value=session.session_id,
            httponly=True,
            max_age=24 * 7 * 3600,
            samesite="lax"
        )
        
        logger.info(f"User {user.username} logged in, session: {session.session_id[:8]}...")
        
        return {
            "session_id": session.session_id,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "nickname": user.nickname or user.username,
                "email": user.email or "",
                "avatar": user.avatar or "",
                "role": user.role,
                "status": user.status,
            }
        }


@router.get("/me", response_model=SessionResponse)
async def get_current_user():
    """获取当前用户信息"""
    session = get_current_session()
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        quota=session.quota
    )


@router.post("/logout")
async def logout(response: Response):
    """用户登出"""
    session_id = get_session_id()
    if session_id:
        session_store = get_session_store()
        await session_store.delete(session_id)
        
        # 清除 Cookie
        response.delete_cookie("session_id")
        
        logger.info(f"Session logged out: {session_id[:8]}...")
    
    return {"message": "Logged out"}


@router.post("/refresh")
async def refresh_session():
    """刷新 Session 过期时间"""
    session_id = get_session_id()
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_store = get_session_store()
    success = await session_store.refresh(session_id, extend_hours=24)
    
    if not success:
        raise HTTPException(status_code=401, detail="Session not found")
    
    session = await session_store.get(session_id)
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        quota=session.quota
    )

