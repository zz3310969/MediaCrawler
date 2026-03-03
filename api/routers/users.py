# -*- coding: utf-8 -*-
"""
用户管理路由
提供用户的CRUD接口
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from database.db_session import get_session
from api.schemas.user import (
    User, UserCreate, UserUpdate, UserPasswordChange, UserPasswordReset,
    UserRole, UserStatus, UserListResponse
)
from api.services.crud.user import user_crud, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ==================== 用户CRUD接口 ====================

@router.post("/", response_model=User, summary="创建用户")
async def create_user(request: UserCreate):
    """
    创建新用户
    
    - **username**: 用户名（3-128字符，唯一）
    - **password**: 密码（至少6字符）
    - **email**: 邮箱（可选）
    - **nickname**: 昵称（可选）
    - **role**: 角色（admin/user，默认user）
    """
    async with get_session() as session:
        # 检查用户名是否已存在
        existing = await user_crud.get_by_username(session, request.username)
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        user = await user_crud.create_user(session, obj_in=request)
        logger.info(f"User created: {user.username}")
        
        return User.model_validate(user)


@router.get("/", response_model=UserListResponse, summary="获取用户列表")
async def list_users(
    status: Optional[UserStatus] = Query(None, description="状态筛选"),
    role: Optional[UserRole] = Query(None, description="角色筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取用户列表（分页）
    
    支持按状态、角色筛选，以及关键词搜索（用户名/昵称/邮箱）
    """
    async with get_session() as session:
        status_value = status.value if status else None
        role_value = role.value if role else None
        
        users = await user_crud.get_users_list(
            session,
            status=status_value,
            role=role_value,
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        
        total = await user_crud.count_users(
            session,
            status=status_value,
            role=role_value,
            keyword=keyword
        )
        
        return UserListResponse(
            items=[User.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size
        )


@router.get("/{user_id}", response_model=User, summary="获取用户详情")
async def get_user(user_id: str):
    """
    通过用户ID获取用户详情
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return User.model_validate(user)


@router.put("/{user_id}", response_model=User, summary="更新用户信息")
async def update_user(user_id: str, request: UserUpdate):
    """
    更新用户信息
    
    - **email**: 邮箱
    - **nickname**: 昵称
    - **avatar**: 头像URL
    - **status**: 状态
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user = await user_crud.update_user(session, db_obj=user, obj_in=request)
        logger.info(f"User updated: {user.username}")
        
        return User.model_validate(user)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(user_id: str):
    """
    删除用户
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 不允许删除admin用户
        if user.role == UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="不能删除管理员用户")
        
        await user_crud.delete_user(session, user_id=user_id)
        logger.info(f"User deleted: {user.username}")
        
        return {"message": "用户已删除"}


# ==================== 密码管理接口 ====================

@router.post("/{user_id}/change-password", summary="修改密码")
async def change_password(user_id: str, request: UserPasswordChange):
    """
    用户修改自己的密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码（至少6字符）
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 验证旧密码
        if not verify_password(request.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码错误")
        
        await user_crud.change_password(session, db_obj=user, new_password=request.new_password)
        logger.info(f"User password changed: {user.username}")
        
        return {"message": "密码修改成功"}


@router.post("/{user_id}/reset-password", summary="重置密码（管理员）")
async def reset_password(user_id: str, request: UserPasswordReset):
    """
    管理员重置用户密码
    
    - **new_password**: 新密码（至少6字符）
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        await user_crud.change_password(session, db_obj=user, new_password=request.new_password)
        logger.info(f"User password reset by admin: {user.username}")
        
        return {"message": "密码重置成功"}


# ==================== 用户状态管理 ====================

@router.post("/{user_id}/activate", summary="激活用户")
async def activate_user(user_id: str):
    """
    激活用户账号
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user.status = UserStatus.ACTIVE.value
        session.add(user)
        
        return {"message": "用户已激活"}


@router.post("/{user_id}/deactivate", summary="停用用户")
async def deactivate_user(user_id: str):
    """
    停用用户账号
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if user.role == UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="不能停用管理员用户")
        
        user.status = UserStatus.INACTIVE.value
        session.add(user)
        
        return {"message": "用户已停用"}


@router.post("/{user_id}/ban", summary="封禁用户")
async def ban_user(user_id: str):
    """
    封禁用户账号
    """
    async with get_session() as session:
        user = await user_crud.get_by_user_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if user.role == UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="不能封禁管理员用户")
        
        user.status = UserStatus.BANNED.value
        session.add(user)
        
        return {"message": "用户已封禁"}
