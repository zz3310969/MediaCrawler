# -*- coding: utf-8 -*-
"""
用户CRUD服务
"""
import logging
import hashlib
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import User
from api.schemas.user import UserCreate, UserUpdate, UserStatus, UserRole
from .base import CRUDBase, generate_uuid, get_timestamp_seconds

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    密码哈希（使用SHA256，生产环境建议使用bcrypt）
    
    Args:
        password: 原始密码
        
    Returns:
        哈希后的密码
    """
    # 添加盐值
    salt = "mediacrawler_salt_2024"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 原始密码
        hashed_password: 哈希后的密码
        
    Returns:
        是否匹配
    """
    return hash_password(plain_password) == hashed_password


class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
    """用户CRUD操作"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_user_id(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> Optional[User]:
        """
        通过user_id获取用户
        
        Args:
            session: 数据库会话
            user_id: 用户唯一ID
            
        Returns:
            用户实例或None
        """
        return await self.get_by_field(session, "user_id", user_id)
    
    async def get_by_username(
        self, 
        session: AsyncSession, 
        username: str
    ) -> Optional[User]:
        """
        通过用户名获取用户
        
        Args:
            session: 数据库会话
            username: 用户名
            
        Returns:
            用户实例或None
        """
        return await self.get_by_field(session, "username", username)
    
    async def create_user(
        self, 
        session: AsyncSession, 
        *, 
        obj_in: UserCreate
    ) -> User:
        """
        创建用户
        
        Args:
            session: 数据库会话
            obj_in: 创建用户数据
            
        Returns:
            创建的用户实例
        """
        now = get_timestamp_seconds()
        
        user_data = {
            "user_id": generate_uuid(),
            "username": obj_in.username,
            "password_hash": hash_password(obj_in.password),
            "email": obj_in.email or "",
            "nickname": obj_in.nickname or obj_in.username,
            "role": obj_in.role.value if isinstance(obj_in.role, UserRole) else obj_in.role,
            "status": UserStatus.ACTIVE.value,
            "created_at": now,
            "updated_at": now,
        }
        
        return await self.create_from_dict(session, obj_in=user_data)
    
    async def update_user(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: User, 
        obj_in: UserUpdate
    ) -> User:
        """
        更新用户信息
        
        Args:
            session: 数据库会话
            db_obj: 数据库中的用户实例
            obj_in: 更新数据
            
        Returns:
            更新后的用户实例
        """
        update_data = obj_in.model_dump(exclude_unset=True, exclude_none=True)
        
        # 处理枚举类型
        if "status" in update_data and isinstance(update_data["status"], UserStatus):
            update_data["status"] = update_data["status"].value
        
        update_data["updated_at"] = get_timestamp_seconds()
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def change_password(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: User, 
        new_password: str
    ) -> User:
        """
        修改密码
        
        Args:
            session: 数据库会话
            db_obj: 用户实例
            new_password: 新密码
            
        Returns:
            更新后的用户实例
        """
        db_obj.password_hash = hash_password(new_password)
        db_obj.updated_at = get_timestamp_seconds()
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_login_info(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: User, 
        login_ip: str = ""
    ) -> User:
        """
        更新登录信息
        
        Args:
            session: 数据库会话
            db_obj: 用户实例
            login_ip: 登录IP
            
        Returns:
            更新后的用户实例
        """
        db_obj.last_login_at = get_timestamp_seconds()
        db_obj.last_login_ip = login_ip
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def authenticate(
        self, 
        session: AsyncSession, 
        *, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """
        验证用户凭据
        
        Args:
            session: 数据库会话
            username: 用户名
            password: 密码
            
        Returns:
            验证成功返回用户实例，否则返回None
        """
        user = await self.get_by_username(session, username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if user.status != UserStatus.ACTIVE.value:
            return None
        return user
    
    async def get_users_list(
        self,
        session: AsyncSession,
        *,
        status: Optional[str] = None,
        role: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[User]:
        """
        获取用户列表
        
        Args:
            session: 数据库会话
            status: 状态筛选
            role: 角色筛选
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            用户列表
        """
        skip = (page - 1) * page_size
        
        filters = {}
        if status:
            filters["status"] = status
        if role:
            filters["role"] = role
        
        if keyword:
            return await self.search(
                session,
                keyword=keyword,
                search_fields=["username", "nickname", "email"],
                skip=skip,
                limit=page_size,
                filters=filters,
                order_by="created_at",
                order_desc=True
            )
        else:
            return await self.get_multi(
                session,
                skip=skip,
                limit=page_size,
                filters=filters,
                order_by="created_at",
                order_desc=True
            )
    
    async def count_users(
        self,
        session: AsyncSession,
        *,
        status: Optional[str] = None,
        role: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> int:
        """
        统计用户数量
        
        Args:
            session: 数据库会话
            status: 状态筛选
            role: 角色筛选
            keyword: 搜索关键词
            
        Returns:
            用户数量
        """
        filters = {}
        if status:
            filters["status"] = status
        if role:
            filters["role"] = role
        
        if keyword:
            return await self.count_search(
                session,
                keyword=keyword,
                search_fields=["username", "nickname", "email"],
                filters=filters
            )
        else:
            return await self.count(session, filters=filters)
    
    async def delete_user(
        self, 
        session: AsyncSession, 
        *, 
        user_id: str
    ) -> int:
        """
        删除用户
        
        Args:
            session: 数据库会话
            user_id: 用户唯一ID
            
        Returns:
            影响的行数
        """
        return await self.delete_by_field(session, field_name="user_id", field_value=user_id)


# 单例实例
user_crud = UserCRUD()
