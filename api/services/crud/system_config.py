# -*- coding: utf-8 -*-
"""
系统配置CRUD服务
"""
import json
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import SystemConfig
from .base import CRUDBase, generate_uuid, get_timestamp_seconds

logger = logging.getLogger(__name__)


class SystemConfigCRUD(CRUDBase[SystemConfig, None, None]):
    """系统配置CRUD操作"""
    
    def __init__(self):
        super().__init__(SystemConfig)
    
    async def get_by_key(
        self, 
        session: AsyncSession, 
        config_key: str
    ) -> Optional[SystemConfig]:
        """
        通过配置键获取配置
        
        Args:
            session: 数据库会话
            config_key: 配置键
            
        Returns:
            配置实例或None
        """
        return await self.get_by_field(session, "config_key", config_key)
    
    async def get_value(
        self, 
        session: AsyncSession, 
        config_key: str,
        default: Any = None
    ) -> Any:
        """
        获取配置值
        
        Args:
            session: 数据库会话
            config_key: 配置键
            default: 默认值
            
        Returns:
            配置值（JSON解析后的对象）
        """
        config = await self.get_by_key(session, config_key)
        if not config:
            return default
        
        try:
            return json.loads(config.config_value)
        except json.JSONDecodeError:
            return config.config_value
    
    async def set_value(
        self, 
        session: AsyncSession, 
        *,
        config_key: str,
        config_value: Any,
        config_type: str = "system",
        description: str = ""
    ) -> SystemConfig:
        """
        设置配置值
        
        Args:
            session: 数据库会话
            config_key: 配置键
            config_value: 配置值（会自动JSON序列化）
            config_type: 配置类型
            description: 描述
            
        Returns:
            配置实例
        """
        now = get_timestamp_seconds()
        
        # 序列化配置值
        if not isinstance(config_value, str):
            value_str = json.dumps(config_value, ensure_ascii=False)
        else:
            value_str = config_value
        
        # 检查是否存在
        existing = await self.get_by_key(session, config_key)
        
        if existing:
            # 更新
            existing.config_value = value_str
            existing.config_type = config_type
            if description:
                existing.description = description
            existing.updated_at = now
            
            session.add(existing)
            await session.flush()
            await session.refresh(existing)
            return existing
        else:
            # 创建
            config_data = {
                "config_key": config_key,
                "config_value": value_str,
                "config_type": config_type,
                "description": description,
                "created_at": now,
                "updated_at": now,
            }
            return await self.create_from_dict(session, obj_in=config_data)
    
    async def delete_config(
        self, 
        session: AsyncSession, 
        *, 
        config_key: str
    ) -> int:
        """
        删除配置
        
        Args:
            session: 数据库会话
            config_key: 配置键
            
        Returns:
            影响的行数
        """
        return await self.delete_by_field(session, field_name="config_key", field_value=config_key)
    
    async def get_configs_by_type(
        self,
        session: AsyncSession,
        config_type: str
    ) -> List[SystemConfig]:
        """
        获取指定类型的所有配置
        
        Args:
            session: 数据库会话
            config_type: 配置类型
            
        Returns:
            配置列表
        """
        result = await session.execute(
            select(SystemConfig)
            .where(SystemConfig.config_type == config_type)
            .order_by(SystemConfig.config_key.asc())
        )
        return list(result.scalars().all())
    
    async def get_all_configs(
        self,
        session: AsyncSession,
        *,
        config_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[SystemConfig]:
        """
        获取所有配置（分页）
        
        Args:
            session: 数据库会话
            config_type: 配置类型筛选
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            配置列表
        """
        skip = (page - 1) * page_size
        
        query = select(SystemConfig)
        conditions = []
        
        if config_type:
            conditions.append(SystemConfig.config_type == config_type)
        if keyword:
            conditions.append(
                SystemConfig.config_key.like(f"%{keyword}%") |
                SystemConfig.description.like(f"%{keyword}%")
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(SystemConfig.config_type.asc(), SystemConfig.config_key.asc())
        query = query.offset(skip).limit(page_size)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_configs(
        self,
        session: AsyncSession,
        *,
        config_type: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> int:
        """
        统计配置数量
        """
        query = select(func.count()).select_from(SystemConfig)
        conditions = []
        
        if config_type:
            conditions.append(SystemConfig.config_type == config_type)
        if keyword:
            conditions.append(
                SystemConfig.config_key.like(f"%{keyword}%") |
                SystemConfig.description.like(f"%{keyword}%")
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def get_configs_as_dict(
        self,
        session: AsyncSession,
        config_type: str = None
    ) -> Dict[str, Any]:
        """
        获取配置为字典形式
        
        Args:
            session: 数据库会话
            config_type: 配置类型
            
        Returns:
            配置字典 {key: value}
        """
        if config_type:
            configs = await self.get_configs_by_type(session, config_type)
        else:
            configs = await self.get_all_configs(session, page_size=1000)
        
        result = {}
        for config in configs:
            try:
                result[config.config_key] = json.loads(config.config_value)
            except json.JSONDecodeError:
                result[config.config_key] = config.config_value
        
        return result
    
    async def batch_set_values(
        self,
        session: AsyncSession,
        *,
        configs: Dict[str, Any],
        config_type: str = "system"
    ) -> int:
        """
        批量设置配置值
        
        Args:
            session: 数据库会话
            configs: 配置字典 {key: value}
            config_type: 配置类型
            
        Returns:
            更新的配置数量
        """
        count = 0
        for key, value in configs.items():
            await self.set_value(
                session,
                config_key=key,
                config_value=value,
                config_type=config_type
            )
            count += 1
        
        return count


# 单例实例
system_config_crud = SystemConfigCRUD()


# ==================== 预定义配置键 ====================

class ConfigKeys:
    """预定义的配置键常量"""
    
    # 代理配置
    PROXY_ENABLE = "proxy.enable"
    PROXY_POOL_SIZE = "proxy.pool_size"
    PROXY_VALIDATE_TIMEOUT = "proxy.validate_timeout"
    PROXY_BINDING_STICKY = "proxy.binding_sticky"
    PROXY_AUTO_REBIND = "proxy.auto_rebind"
    
    # 爬虫配置
    CRAWLER_CONCURRENCY = "crawler.concurrency"
    CRAWLER_REQUEST_INTERVAL = "crawler.request_interval"
    CRAWLER_MAX_RETRIES = "crawler.max_retries"
    CRAWLER_TIMEOUT = "crawler.timeout"
    
    # 系统配置
    SYSTEM_LOG_LEVEL = "system.log_level"
    SYSTEM_DATA_RETENTION_DAYS = "system.data_retention_days"
    SYSTEM_MAINTENANCE_MODE = "system.maintenance_mode"


# 默认配置值
DEFAULT_CONFIGS = {
    ConfigKeys.PROXY_ENABLE: True,
    ConfigKeys.PROXY_POOL_SIZE: 5,
    ConfigKeys.PROXY_VALIDATE_TIMEOUT: 10,
    ConfigKeys.PROXY_BINDING_STICKY: True,
    ConfigKeys.PROXY_AUTO_REBIND: True,
    
    ConfigKeys.CRAWLER_CONCURRENCY: 3,
    ConfigKeys.CRAWLER_REQUEST_INTERVAL: 1.0,
    ConfigKeys.CRAWLER_MAX_RETRIES: 3,
    ConfigKeys.CRAWLER_TIMEOUT: 30,
    
    ConfigKeys.SYSTEM_LOG_LEVEL: "INFO",
    ConfigKeys.SYSTEM_DATA_RETENTION_DAYS: 30,
    ConfigKeys.SYSTEM_MAINTENANCE_MODE: False,
}
