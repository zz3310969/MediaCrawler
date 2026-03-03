# -*- coding: utf-8 -*-
"""
代理池CRUD服务
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import ProxyPool, ProxyBinding
from .base import CRUDBase, generate_uuid, get_timestamp_seconds

logger = logging.getLogger(__name__)


class ProxyCRUD(CRUDBase[ProxyPool, None, None]):
    """代理池CRUD操作"""
    
    def __init__(self):
        super().__init__(ProxyPool)
    
    async def get_by_proxy_id(
        self, 
        session: AsyncSession, 
        proxy_id: str
    ) -> Optional[ProxyPool]:
        """
        通过proxy_id获取代理
        
        Args:
            session: 数据库会话
            proxy_id: 代理唯一ID
            
        Returns:
            代理实例或None
        """
        return await self.get_by_field(session, "proxy_id", proxy_id)
    
    async def get_by_ip_port(
        self, 
        session: AsyncSession, 
        ip: str, 
        port: int
    ) -> Optional[ProxyPool]:
        """
        通过IP和端口获取代理
        
        Args:
            session: 数据库会话
            ip: IP地址
            port: 端口
            
        Returns:
            代理实例或None
        """
        result = await session.execute(
            select(ProxyPool).where(
                and_(
                    ProxyPool.ip == ip,
                    ProxyPool.port == port
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_proxy(
        self, 
        session: AsyncSession, 
        *,
        ip: str,
        port: int,
        protocol: str = "http",
        username: str = "",
        password: str = "",
        source: str = "manual",
        country: str = "CN",
        province: str = "",
        city: str = ""
    ) -> ProxyPool:
        """
        创建代理
        
        Args:
            session: 数据库会话
            ip: IP地址
            port: 端口
            protocol: 协议
            username: 认证用户名
            password: 认证密码
            source: 来源
            country: 国家
            province: 省份
            city: 城市
            
        Returns:
            创建的代理实例
        """
        now = get_timestamp_seconds()
        
        proxy_data = {
            "proxy_id": generate_uuid(),
            "ip": ip,
            "port": port,
            "protocol": protocol,
            "username": username,
            "password": password,
            "source": source,
            "country": country,
            "province": province,
            "city": city,
            "status": "testing",
            "is_active": 1,
            "quality_score": 50.0,
            "created_at": now,
            "updated_at": now,
        }
        
        return await self.create_from_dict(session, obj_in=proxy_data)
    
    async def batch_create_proxies(
        self,
        session: AsyncSession,
        *,
        proxies: List[Dict[str, Any]],
        source: str = "manual"
    ) -> tuple[int, int]:
        """
        批量创建代理
        
        Args:
            session: 数据库会话
            proxies: 代理数据列表
            source: 来源
            
        Returns:
            (成功数, 失败数)
        """
        success_count = 0
        failed_count = 0
        now = get_timestamp_seconds()
        
        for proxy_data in proxies:
            try:
                # 检查是否已存在
                existing = await self.get_by_ip_port(
                    session, 
                    proxy_data["ip"], 
                    proxy_data["port"]
                )
                if existing:
                    failed_count += 1
                    continue
                
                data = {
                    "proxy_id": generate_uuid(),
                    "ip": proxy_data["ip"],
                    "port": proxy_data["port"],
                    "protocol": proxy_data.get("protocol", "http"),
                    "username": proxy_data.get("username", ""),
                    "password": proxy_data.get("password", ""),
                    "source": source,
                    "country": proxy_data.get("country", "CN"),
                    "province": proxy_data.get("province", ""),
                    "city": proxy_data.get("city", ""),
                    "status": "testing",
                    "is_active": 1,
                    "quality_score": 50.0,
                    "created_at": now,
                    "updated_at": now,
                }
                
                db_obj = ProxyPool(**data)
                session.add(db_obj)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to create proxy: {e}")
                failed_count += 1
        
        await session.flush()
        return success_count, failed_count
    
    async def update_proxy_status(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: ProxyPool, 
        status: str,
        response_time: int = None
    ) -> ProxyPool:
        """
        更新代理状态
        
        Args:
            session: 数据库会话
            db_obj: 代理实例
            status: 新状态
            response_time: 响应时间
            
        Returns:
            更新后的代理实例
        """
        db_obj.status = status
        db_obj.last_checked_at = get_timestamp_seconds()
        db_obj.updated_at = get_timestamp_seconds()
        
        if response_time is not None:
            db_obj.response_time = response_time
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_quality_metrics(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: ProxyPool, 
        success: bool,
        response_time: int = 0
    ) -> ProxyPool:
        """
        更新质量指标
        
        Args:
            session: 数据库会话
            db_obj: 代理实例
            success: 是否成功
            response_time: 响应时间
            
        Returns:
            更新后的代理实例
        """
        now = get_timestamp_seconds()
        
        db_obj.total_requests += 1
        
        if success:
            db_obj.success_requests += 1
            db_obj.consecutive_failures = 0
            db_obj.last_success_at = now
            if response_time > 0:
                db_obj.response_time = response_time
        else:
            db_obj.failed_requests += 1
            db_obj.consecutive_failures += 1
            db_obj.last_failure_at = now
        
        # 计算质量评分
        if db_obj.total_requests > 0:
            success_rate = db_obj.success_requests / db_obj.total_requests
            # 基于成功率和连续失败次数计算评分
            db_obj.quality_score = max(0, min(100, 
                success_rate * 80 + 
                max(0, 20 - db_obj.consecutive_failures * 5)
            ))
        
        db_obj.updated_at = now
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def set_active_status(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: ProxyPool, 
        is_active: bool
    ) -> ProxyPool:
        """
        设置激活状态
        
        Args:
            session: 数据库会话
            db_obj: 代理实例
            is_active: 是否激活
            
        Returns:
            更新后的代理实例
        """
        db_obj.is_active = 1 if is_active else 0
        db_obj.updated_at = get_timestamp_seconds()
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def get_proxies_list(
        self,
        session: AsyncSession,
        *,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        source: Optional[str] = None,
        country: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[ProxyPool]:
        """
        获取代理列表
        
        Args:
            session: 数据库会话
            status: 状态筛选
            is_active: 是否激活筛选
            source: 来源筛选
            country: 国家筛选
            min_quality_score: 最低质量评分
            keyword: 搜索关键词(IP)
            page: 页码
            page_size: 每页数量
            
        Returns:
            代理列表
        """
        skip = (page - 1) * page_size
        
        query = select(ProxyPool)
        conditions = []
        
        if status:
            conditions.append(ProxyPool.status == status)
        if is_active is not None:
            conditions.append(ProxyPool.is_active == (1 if is_active else 0))
        if source:
            conditions.append(ProxyPool.source == source)
        if country:
            conditions.append(ProxyPool.country == country)
        if min_quality_score is not None:
            conditions.append(ProxyPool.quality_score >= min_quality_score)
        if keyword:
            conditions.append(ProxyPool.ip.like(f"%{keyword}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(ProxyPool.quality_score.desc()).offset(skip).limit(page_size)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_proxies(
        self,
        session: AsyncSession,
        *,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        source: Optional[str] = None,
        country: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        keyword: Optional[str] = None
    ) -> int:
        """
        统计代理数量
        """
        query = select(func.count()).select_from(ProxyPool)
        conditions = []
        
        if status:
            conditions.append(ProxyPool.status == status)
        if is_active is not None:
            conditions.append(ProxyPool.is_active == (1 if is_active else 0))
        if source:
            conditions.append(ProxyPool.source == source)
        if country:
            conditions.append(ProxyPool.country == country)
        if min_quality_score is not None:
            conditions.append(ProxyPool.quality_score >= min_quality_score)
        if keyword:
            conditions.append(ProxyPool.ip.like(f"%{keyword}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def get_stats(
        self,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        获取代理统计数据
        
        Args:
            session: 数据库会话
            
        Returns:
            统计数据字典
        """
        total = await self.count_proxies(session)
        online = await self.count_proxies(session, status="online")
        offline = await self.count_proxies(session, status="offline")
        testing = await self.count_proxies(session, status="testing")
        
        # 计算平均响应时间和质量评分
        result = await session.execute(
            select(
                func.avg(ProxyPool.response_time),
                func.avg(ProxyPool.quality_score)
            ).where(ProxyPool.status == "online")
        )
        row = result.one()
        avg_response_time = float(row[0] or 0)
        avg_quality_score = float(row[1] or 0)
        
        # 计算平均成功率
        result = await session.execute(
            select(
                func.sum(ProxyPool.success_requests),
                func.sum(ProxyPool.total_requests)
            ).where(ProxyPool.is_active == 1)
        )
        row = result.one()
        total_success = int(row[0] or 0)
        total_requests = int(row[1] or 0)
        avg_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total": total,
            "online": online,
            "offline": offline,
            "testing": testing,
            "avg_response_time": round(avg_response_time, 2),
            "avg_quality_score": round(avg_quality_score, 2),
            "avg_success_rate": round(avg_success_rate, 2)
        }
    
    async def get_best_proxy(
        self,
        session: AsyncSession,
        *,
        exclude_ids: List[str] = None
    ) -> Optional[ProxyPool]:
        """
        获取最优代理
        
        Args:
            session: 数据库会话
            exclude_ids: 排除的代理ID列表
            
        Returns:
            代理实例或None
        """
        query = (
            select(ProxyPool)
            .where(
                and_(
                    ProxyPool.status == "online",
                    ProxyPool.is_active == 1
                )
            )
            .order_by(ProxyPool.quality_score.desc())
        )
        
        if exclude_ids:
            query = query.where(~ProxyPool.proxy_id.in_(exclude_ids))
        
        result = await session.execute(query.limit(1))
        return result.scalar_one_or_none()
    
    async def delete_proxy(
        self, 
        session: AsyncSession, 
        *, 
        proxy_id: str
    ) -> int:
        """
        删除代理
        
        Args:
            session: 数据库会话
            proxy_id: 代理唯一ID
            
        Returns:
            影响的行数
        """
        return await self.delete_by_field(session, field_name="proxy_id", field_value=proxy_id)
    
    async def batch_delete(
        self,
        session: AsyncSession,
        *,
        proxy_ids: List[str]
    ) -> int:
        """
        批量删除代理
        
        Args:
            session: 数据库会话
            proxy_ids: 代理ID列表
            
        Returns:
            影响的行数
        """
        from sqlalchemy import delete
        
        stmt = delete(ProxyPool).where(ProxyPool.proxy_id.in_(proxy_ids))
        result = await session.execute(stmt)
        return result.rowcount


class ProxyBindingCRUD(CRUDBase[ProxyBinding, None, None]):
    """代理绑定CRUD操作"""
    
    def __init__(self):
        super().__init__(ProxyBinding)
    
    async def get_by_binding_id(
        self, 
        session: AsyncSession, 
        binding_id: str
    ) -> Optional[ProxyBinding]:
        """
        通过binding_id获取绑定
        """
        return await self.get_by_field(session, "binding_id", binding_id)
    
    async def get_by_account_platform(
        self, 
        session: AsyncSession, 
        account_id: str, 
        platform: str
    ) -> Optional[ProxyBinding]:
        """
        通过账号ID和平台获取绑定
        """
        result = await session.execute(
            select(ProxyBinding).where(
                and_(
                    ProxyBinding.account_id == account_id,
                    ProxyBinding.platform == platform
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_binding(
        self, 
        session: AsyncSession, 
        *,
        account_id: str,
        platform: str,
        proxy_id: str,
        is_sticky: bool = True
    ) -> ProxyBinding:
        """
        创建绑定
        """
        now = get_timestamp_seconds()
        
        binding_data = {
            "binding_id": generate_uuid(),
            "account_id": account_id,
            "platform": platform,
            "proxy_id": proxy_id,
            "is_sticky": 1 if is_sticky else 0,
            "status": "active",
            "bound_at": now,
        }
        
        return await self.create_from_dict(session, obj_in=binding_data)
    
    async def update_binding(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: ProxyBinding, 
        proxy_id: str
    ) -> ProxyBinding:
        """
        更新绑定的代理
        """
        db_obj.proxy_id = proxy_id
        db_obj.rebind_count += 1
        db_obj.last_used_at = get_timestamp_seconds()
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def get_bindings_list(
        self,
        session: AsyncSession,
        *,
        account_id: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[ProxyBinding]:
        """
        获取绑定列表
        """
        skip = (page - 1) * page_size
        
        query = select(ProxyBinding)
        conditions = []
        
        if account_id:
            conditions.append(ProxyBinding.account_id == account_id)
        if platform:
            conditions.append(ProxyBinding.platform == platform)
        if status:
            conditions.append(ProxyBinding.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(ProxyBinding.bound_at.desc()).offset(skip).limit(page_size)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_bindings(
        self,
        session: AsyncSession,
        *,
        account_id: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        统计绑定数量
        """
        query = select(func.count()).select_from(ProxyBinding)
        conditions = []
        
        if account_id:
            conditions.append(ProxyBinding.account_id == account_id)
        if platform:
            conditions.append(ProxyBinding.platform == platform)
        if status:
            conditions.append(ProxyBinding.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def delete_binding(
        self, 
        session: AsyncSession, 
        *, 
        binding_id: str
    ) -> int:
        """
        删除绑定
        """
        return await self.delete_by_field(session, field_name="binding_id", field_value=binding_id)
    
    async def delete_by_account(
        self,
        session: AsyncSession,
        *,
        account_id: str,
        platform: str = None
    ) -> int:
        """
        删除账号的绑定
        """
        from sqlalchemy import delete
        
        conditions = [ProxyBinding.account_id == account_id]
        if platform:
            conditions.append(ProxyBinding.platform == platform)
        
        stmt = delete(ProxyBinding).where(and_(*conditions))
        result = await session.execute(stmt)
        return result.rowcount


# 单例实例
proxy_crud = ProxyCRUD()
proxy_binding_crud = ProxyBindingCRUD()
