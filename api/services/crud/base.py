# -*- coding: utf-8 -*-
"""
CRUD基础服务类
提供通用的增删改查操作
"""
import time
import uuid
import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 类型变量
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())


def get_timestamp() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def get_timestamp_seconds() -> int:
    """获取当前时间戳（秒）"""
    return int(time.time())


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    CRUD基础类
    
    提供通用的数据库操作方法，子类可以继承并扩展
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        初始化CRUD实例
        
        Args:
            model: SQLAlchemy模型类
        """
        self.model = model
    
    async def get(
        self, 
        session: AsyncSession, 
        id: int
    ) -> Optional[ModelType]:
        """
        通过主键ID获取单条记录
        
        Args:
            session: 数据库会话
            id: 主键ID
            
        Returns:
            模型实例或None
        """
        result = await session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_field(
        self, 
        session: AsyncSession, 
        field_name: str, 
        field_value: Any
    ) -> Optional[ModelType]:
        """
        通过指定字段获取单条记录
        
        Args:
            session: 数据库会话
            field_name: 字段名
            field_value: 字段值
            
        Returns:
            模型实例或None
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"Model {self.model.__name__} has no field {field_name}")
        
        result = await session.execute(
            select(self.model).where(field == field_value)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        session: AsyncSession,
        *,
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[ModelType]:
        """
        获取多条记录（分页）
        
        Args:
            session: 数据库会话
            skip: 跳过记录数
            limit: 返回记录数上限
            filters: 过滤条件字典
            order_by: 排序字段名
            order_desc: 是否降序
            
        Returns:
            模型实例列表
        """
        query = select(self.model)
        
        # 应用过滤条件
        if filters:
            conditions = []
            for field_name, field_value in filters.items():
                if field_value is not None:
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        conditions.append(field == field_value)
            if conditions:
                query = query.where(and_(*conditions))
        
        # 应用排序
        if order_by:
            order_field = getattr(self.model, order_by, None)
            if order_field is not None:
                if order_desc:
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field.asc())
        
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count(
        self, 
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        统计记录数
        
        Args:
            session: 数据库会话
            filters: 过滤条件字典
            
        Returns:
            记录数
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            conditions = []
            for field_name, field_value in filters.items():
                if field_value is not None:
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        conditions.append(field == field_value)
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def create(
        self, 
        session: AsyncSession, 
        *, 
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        创建记录
        
        Args:
            session: 数据库会话
            obj_in: 创建数据Schema
            
        Returns:
            创建的模型实例
        """
        obj_data = obj_in.model_dump(exclude_unset=True)
        db_obj = self.model(**obj_data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def create_from_dict(
        self, 
        session: AsyncSession, 
        *, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        从字典创建记录
        
        Args:
            session: 数据库会话
            obj_in: 数据字典
            
        Returns:
            创建的模型实例
        """
        db_obj = self.model(**obj_in)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """
        更新记录
        
        Args:
            session: 数据库会话
            db_obj: 数据库中的模型实例
            obj_in: 更新数据Schema
            
        Returns:
            更新后的模型实例
        """
        obj_data = obj_in.model_dump(exclude_unset=True, exclude_none=True)
        
        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_by_id(
        self, 
        session: AsyncSession, 
        *, 
        id: int, 
        obj_in: Dict[str, Any]
    ) -> int:
        """
        通过ID更新记录
        
        Args:
            session: 数据库会话
            id: 主键ID
            obj_in: 更新数据字典
            
        Returns:
            影响的行数
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
        )
        result = await session.execute(stmt)
        return result.rowcount
    
    async def delete(
        self, 
        session: AsyncSession, 
        *, 
        id: int
    ) -> int:
        """
        删除记录
        
        Args:
            session: 数据库会话
            id: 主键ID
            
        Returns:
            影响的行数
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.rowcount
    
    async def delete_by_field(
        self, 
        session: AsyncSession, 
        *, 
        field_name: str, 
        field_value: Any
    ) -> int:
        """
        通过指定字段删除记录
        
        Args:
            session: 数据库会话
            field_name: 字段名
            field_value: 字段值
            
        Returns:
            影响的行数
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"Model {self.model.__name__} has no field {field_name}")
        
        stmt = delete(self.model).where(field == field_value)
        result = await session.execute(stmt)
        return result.rowcount
    
    async def exists(
        self, 
        session: AsyncSession, 
        *, 
        field_name: str, 
        field_value: Any
    ) -> bool:
        """
        检查记录是否存在
        
        Args:
            session: 数据库会话
            field_name: 字段名
            field_value: 字段值
            
        Returns:
            是否存在
        """
        field = getattr(self.model, field_name, None)
        if field is None:
            raise ValueError(f"Model {self.model.__name__} has no field {field_name}")
        
        result = await session.execute(
            select(func.count()).select_from(self.model).where(field == field_value)
        )
        count = result.scalar() or 0
        return count > 0
    
    async def search(
        self,
        session: AsyncSession,
        *,
        keyword: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[ModelType]:
        """
        关键词搜索
        
        Args:
            session: 数据库会话
            keyword: 搜索关键词
            search_fields: 搜索字段列表
            skip: 跳过记录数
            limit: 返回记录数上限
            filters: 额外过滤条件
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            模型实例列表
        """
        query = select(self.model)
        
        # 构建搜索条件
        if keyword and search_fields:
            search_conditions = []
            for field_name in search_fields:
                field = getattr(self.model, field_name, None)
                if field is not None:
                    search_conditions.append(field.like(f"%{keyword}%"))
            if search_conditions:
                query = query.where(or_(*search_conditions))
        
        # 应用额外过滤条件
        if filters:
            conditions = []
            for field_name, field_value in filters.items():
                if field_value is not None:
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        conditions.append(field == field_value)
            if conditions:
                query = query.where(and_(*conditions))
        
        # 应用排序
        if order_by:
            order_field = getattr(self.model, order_by, None)
            if order_field is not None:
                if order_desc:
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field.asc())
        
        # 应用分页
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_search(
        self,
        session: AsyncSession,
        *,
        keyword: str,
        search_fields: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        统计搜索结果数
        
        Args:
            session: 数据库会话
            keyword: 搜索关键词
            search_fields: 搜索字段列表
            filters: 额外过滤条件
            
        Returns:
            记录数
        """
        query = select(func.count()).select_from(self.model)
        
        # 构建搜索条件
        if keyword and search_fields:
            search_conditions = []
            for field_name in search_fields:
                field = getattr(self.model, field_name, None)
                if field is not None:
                    search_conditions.append(field.like(f"%{keyword}%"))
            if search_conditions:
                query = query.where(or_(*search_conditions))
        
        # 应用额外过滤条件
        if filters:
            conditions = []
            for field_name, field_value in filters.items():
                if field_value is not None:
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        conditions.append(field == field_value)
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
