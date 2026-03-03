# -*- coding: utf-8 -*-
"""
爬虫账号CRUD服务
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import CrawlerAccount
from api.schemas.account import AccountCreate, AccountUpdate, AccountStatus, Platform, LoginMethod
from .base import CRUDBase, generate_uuid, get_timestamp_seconds

logger = logging.getLogger(__name__)


class AccountCRUD(CRUDBase[CrawlerAccount, AccountCreate, AccountUpdate]):
    """爬虫账号CRUD操作"""
    
    def __init__(self):
        super().__init__(CrawlerAccount)
    
    async def get_by_account_id(
        self, 
        session: AsyncSession, 
        account_id: str
    ) -> Optional[CrawlerAccount]:
        """
        通过account_id获取账号
        
        Args:
            session: 数据库会话
            account_id: 账号唯一ID
            
        Returns:
            账号实例或None
        """
        return await self.get_by_field(session, "account_id", account_id)
    
    async def get_by_platform_username(
        self, 
        session: AsyncSession, 
        platform: str, 
        username: str
    ) -> Optional[CrawlerAccount]:
        """
        通过平台和用户名获取账号
        
        Args:
            session: 数据库会话
            platform: 平台标识
            username: 用户名
            
        Returns:
            账号实例或None
        """
        result = await session.execute(
            select(CrawlerAccount).where(
                and_(
                    CrawlerAccount.platform == platform,
                    CrawlerAccount.username == username
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_account(
        self, 
        session: AsyncSession, 
        *, 
        obj_in: AccountCreate
    ) -> CrawlerAccount:
        """
        创建账号
        
        Args:
            session: 数据库会话
            obj_in: 创建账号数据
            
        Returns:
            创建的账号实例
        """
        now = get_timestamp_seconds()
        
        account_data = {
            "account_id": generate_uuid(),
            "platform": obj_in.platform.value if isinstance(obj_in.platform, Platform) else obj_in.platform,
            "username": obj_in.username or "",
            "nickname": obj_in.nickname or "",
            "login_method": obj_in.login_method.value if isinstance(obj_in.login_method, LoginMethod) else obj_in.login_method,
            "cookies": obj_in.cookies or "",
            "cookie_valid": 1 if obj_in.cookies else 0,
            "status": AccountStatus.PENDING.value,
            "remark": obj_in.remark or "",
            "created_at": now,
            "updated_at": now,
        }
        
        return await self.create_from_dict(session, obj_in=account_data)
    
    async def update_account(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerAccount, 
        obj_in: AccountUpdate
    ) -> CrawlerAccount:
        """
        更新账号信息
        
        Args:
            session: 数据库会话
            db_obj: 数据库中的账号实例
            obj_in: 更新数据
            
        Returns:
            更新后的账号实例
        """
        update_data = obj_in.model_dump(exclude_unset=True, exclude_none=True)
        
        # 处理枚举类型
        if "status" in update_data and isinstance(update_data["status"], AccountStatus):
            update_data["status"] = update_data["status"].value
        
        update_data["updated_at"] = get_timestamp_seconds()
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_cookies(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerAccount, 
        cookies: str,
        nickname: str = None,
        avatar: str = None
    ) -> CrawlerAccount:
        """
        更新Cookie
        
        Args:
            session: 数据库会话
            db_obj: 账号实例
            cookies: 新的Cookie
            nickname: 昵称
            avatar: 头像
            
        Returns:
            更新后的账号实例
        """
        db_obj.cookies = cookies
        db_obj.cookie_valid = 1
        db_obj.status = AccountStatus.ACTIVE.value
        db_obj.last_validated_at = get_timestamp_seconds()
        db_obj.updated_at = get_timestamp_seconds()
        
        if nickname:
            db_obj.nickname = nickname
        if avatar:
            db_obj.avatar = avatar
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def mark_cookie_invalid(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerAccount
    ) -> CrawlerAccount:
        """
        标记Cookie无效
        
        Args:
            session: 数据库会话
            db_obj: 账号实例
            
        Returns:
            更新后的账号实例
        """
        db_obj.cookie_valid = 0
        db_obj.status = AccountStatus.EXPIRED.value
        db_obj.updated_at = get_timestamp_seconds()
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_last_used(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerAccount
    ) -> CrawlerAccount:
        """
        更新最后使用时间
        
        Args:
            session: 数据库会话
            db_obj: 账号实例
            
        Returns:
            更新后的账号实例
        """
        db_obj.last_used_at = get_timestamp_seconds()
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def get_accounts_list(
        self,
        session: AsyncSession,
        *,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[CrawlerAccount]:
        """
        获取账号列表
        
        Args:
            session: 数据库会话
            platform: 平台筛选
            status: 状态筛选
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            账号列表
        """
        skip = (page - 1) * page_size
        
        filters = {}
        if platform:
            filters["platform"] = platform
        if status:
            filters["status"] = status
        
        if keyword:
            return await self.search(
                session,
                keyword=keyword,
                search_fields=["username", "nickname", "remark"],
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
    
    async def count_accounts(
        self,
        session: AsyncSession,
        *,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> int:
        """
        统计账号数量
        
        Args:
            session: 数据库会话
            platform: 平台筛选
            status: 状态筛选
            keyword: 搜索关键词
            
        Returns:
            账号数量
        """
        filters = {}
        if platform:
            filters["platform"] = platform
        if status:
            filters["status"] = status
        
        if keyword:
            return await self.count_search(
                session,
                keyword=keyword,
                search_fields=["username", "nickname", "remark"],
                filters=filters
            )
        else:
            return await self.count(session, filters=filters)
    
    async def get_stats(
        self,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        获取账号统计数据
        
        Args:
            session: 数据库会话
            
        Returns:
            统计数据字典
        """
        # 总数
        total = await self.count(session)
        
        # 各状态数量
        active = await self.count(session, filters={"status": AccountStatus.ACTIVE.value})
        inactive = await self.count(session, filters={"status": AccountStatus.INACTIVE.value})
        pending = await self.count(session, filters={"status": AccountStatus.PENDING.value})
        expired = await self.count(session, filters={"status": AccountStatus.EXPIRED.value})
        
        # 各平台数量
        by_platform = {}
        for platform in Platform:
            count = await self.count(session, filters={"platform": platform.value})
            if count > 0:
                by_platform[platform.value] = count
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "pending": pending,
            "expired": expired,
            "by_platform": by_platform
        }
    
    async def get_active_accounts_by_platform(
        self,
        session: AsyncSession,
        platform: str
    ) -> List[CrawlerAccount]:
        """
        获取指定平台的有效账号列表
        
        Args:
            session: 数据库会话
            platform: 平台标识
            
        Returns:
            账号列表
        """
        result = await session.execute(
            select(CrawlerAccount).where(
                and_(
                    CrawlerAccount.platform == platform,
                    CrawlerAccount.status == AccountStatus.ACTIVE.value,
                    CrawlerAccount.cookie_valid == 1
                )
            ).order_by(CrawlerAccount.last_used_at.asc())
        )
        return list(result.scalars().all())
    
    async def delete_account(
        self, 
        session: AsyncSession, 
        *, 
        account_id: str
    ) -> int:
        """
        删除账号
        
        Args:
            session: 数据库会话
            account_id: 账号唯一ID
            
        Returns:
            影响的行数
        """
        return await self.delete_by_field(session, field_name="account_id", field_value=account_id)
    
    async def batch_delete(
        self,
        session: AsyncSession,
        *,
        account_ids: List[str]
    ) -> int:
        """
        批量删除账号
        
        Args:
            session: 数据库会话
            account_ids: 账号ID列表
            
        Returns:
            影响的行数
        """
        from sqlalchemy import delete
        
        stmt = delete(CrawlerAccount).where(CrawlerAccount.account_id.in_(account_ids))
        result = await session.execute(stmt)
        return result.rowcount
    
    async def batch_update_status(
        self,
        session: AsyncSession,
        *,
        account_ids: List[str],
        status: str
    ) -> int:
        """
        批量更新账号状态
        
        Args:
            session: 数据库会话
            account_ids: 账号ID列表
            status: 目标状态
            
        Returns:
            影响的行数
        """
        from sqlalchemy import update
        
        stmt = (
            update(CrawlerAccount)
            .where(CrawlerAccount.account_id.in_(account_ids))
            .values(status=status, updated_at=get_timestamp_seconds())
        )
        result = await session.execute(stmt)
        return result.rowcount


# 单例实例
account_crud = AccountCRUD()
