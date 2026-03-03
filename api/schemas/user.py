# -*- coding: utf-8 -*-
"""
用户相关数据模型
"""
from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


# ========== 用户实体 ==========

class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=128, description="登录用户名")
    email: Optional[str] = Field(default="", max_length=255, description="邮箱")
    nickname: Optional[str] = Field(default="", max_length=128, description="显示昵称")
    avatar: Optional[str] = Field(default="", description="头像URL")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=128, description="登录用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    email: Optional[str] = Field(default="", max_length=255, description="邮箱")
    nickname: Optional[str] = Field(default="", max_length=128, description="显示昵称")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")


class UserUpdate(BaseModel):
    """更新用户请求"""
    email: Optional[str] = Field(default=None, max_length=255, description="邮箱")
    nickname: Optional[str] = Field(default=None, max_length=128, description="显示昵称")
    avatar: Optional[str] = Field(default=None, description="头像URL")
    status: Optional[UserStatus] = Field(default=None, description="用户状态")


class UserPasswordChange(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class UserPasswordReset(BaseModel):
    """重置密码请求（管理员）"""
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class User(BaseModel):
    """用户信息响应"""
    user_id: str = Field(..., description="用户唯一ID")
    username: str = Field(..., description="登录用户名")
    email: str = Field(default="", description="邮箱")
    nickname: str = Field(default="", description="显示昵称")
    avatar: str = Field(default="", description="头像URL")
    role: str = Field(..., description="用户角色")
    status: str = Field(..., description="用户状态")
    last_login_at: Optional[int] = Field(default=None, description="最后登录时间戳")
    last_login_ip: Optional[str] = Field(default=None, description="最后登录IP")
    created_at: int = Field(..., description="创建时间戳")
    
    class Config:
        from_attributes = True


# ========== 认证相关 ==========

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")
    user: User = Field(..., description="用户信息")


class TokenPayload(BaseModel):
    """令牌载荷"""
    user_id: str
    username: str
    role: str
    exp: int


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


# ========== 列表查询 ==========

class UserListRequest(BaseModel):
    """用户列表查询"""
    status: Optional[UserStatus] = Field(default=None, description="用户状态筛选")
    role: Optional[UserRole] = Field(default=None, description="用户角色筛选")
    keyword: Optional[str] = Field(default=None, description="搜索关键词(用户名/昵称)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[User] = Field(default_factory=list, description="用户列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


# ========== 通用响应 ==========

class UserResponse(BaseModel):
    """单个用户响应"""
    success: bool = True
    data: User


class MessageResponse(BaseModel):
    """消息响应"""
    success: bool = True
    message: str = ""
