# -*- coding: utf-8 -*-
"""
任务CRUD服务
"""
import json
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import CrawlerTask, TaskLog
from api.schemas.task import TaskStatus
from .base import CRUDBase, generate_uuid, get_timestamp_seconds

logger = logging.getLogger(__name__)


class TaskCRUD(CRUDBase[CrawlerTask, None, None]):
    """任务CRUD操作"""
    
    def __init__(self):
        super().__init__(CrawlerTask)
    
    async def get_by_task_id(
        self, 
        session: AsyncSession, 
        task_id: str
    ) -> Optional[CrawlerTask]:
        """
        通过task_id获取任务
        
        Args:
            session: 数据库会话
            task_id: 任务唯一ID
            
        Returns:
            任务实例或None
        """
        return await self.get_by_field(session, "task_id", task_id)
    
    async def create_task(
        self, 
        session: AsyncSession, 
        *,
        task_name: str = "",
        platform: str,
        crawler_type: str = "search",
        user_id: str = "",
        session_id: str = "",
        config: Dict[str, Any] = None,
        priority: int = 5
    ) -> CrawlerTask:
        """
        创建任务
        
        Args:
            session: 数据库会话
            task_name: 任务名称
            platform: 平台
            crawler_type: 爬取类型
            user_id: 用户ID
            session_id: 会话ID
            config: 任务配置
            priority: 优先级
            
        Returns:
            创建的任务实例
        """
        now = get_timestamp_seconds()
        
        task_data = {
            "task_id": generate_uuid(),
            "task_name": task_name or f"{platform}_{crawler_type}_{now}",
            "platform": platform,
            "crawler_type": crawler_type,
            "user_id": user_id,
            "session_id": session_id,
            "status": TaskStatus.PENDING.value,
            "priority": priority,
            "config": json.dumps(config or {}, ensure_ascii=False),
            "progress": "{}",
            "result": "{}",
            "task_metadata": "{}",
            "created_at": now,
        }
        
        return await self.create_from_dict(session, obj_in=task_data)
    
    async def update_status(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerTask, 
        status: str,
        error_message: str = None
    ) -> CrawlerTask:
        """
        更新任务状态
        
        Args:
            session: 数据库会话
            db_obj: 任务实例
            status: 新状态
            error_message: 错误信息
            
        Returns:
            更新后的任务实例
        """
        now = get_timestamp_seconds()
        
        db_obj.status = status
        
        if status == TaskStatus.RUNNING.value:
            db_obj.started_at = now
        elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            db_obj.finished_at = now
        
        if error_message:
            db_obj.error_message = error_message
        
        db_obj.last_heartbeat_at = now
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_progress(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerTask, 
        progress: Dict[str, Any]
    ) -> CrawlerTask:
        """
        更新任务进度
        
        Args:
            session: 数据库会话
            db_obj: 任务实例
            progress: 进度信息
            
        Returns:
            更新后的任务实例
        """
        db_obj.progress = json.dumps(progress, ensure_ascii=False)
        db_obj.last_heartbeat_at = get_timestamp_seconds()
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def update_result(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerTask, 
        result: Dict[str, Any]
    ) -> CrawlerTask:
        """
        更新任务结果
        
        Args:
            session: 数据库会话
            db_obj: 任务实例
            result: 结果信息
            
        Returns:
            更新后的任务实例
        """
        db_obj.result = json.dumps(result, ensure_ascii=False)
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def increment_retry(
        self, 
        session: AsyncSession, 
        *, 
        db_obj: CrawlerTask
    ) -> CrawlerTask:
        """
        增加重试次数
        
        Args:
            session: 数据库会话
            db_obj: 任务实例
            
        Returns:
            更新后的任务实例
        """
        db_obj.retry_count += 1
        db_obj.status = TaskStatus.PENDING.value
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj
    
    async def get_tasks_list(
        self,
        session: AsyncSession,
        *,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        crawler_type: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[CrawlerTask]:
        """
        获取任务列表
        
        Args:
            session: 数据库会话
            status: 状态筛选
            platform: 平台筛选
            crawler_type: 爬取类型筛选
            user_id: 用户ID筛选
            session_id: 会话ID筛选
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            任务列表
        """
        skip = (page - 1) * page_size
        
        query = select(CrawlerTask)
        conditions = []
        
        if status:
            conditions.append(CrawlerTask.status == status)
        if platform:
            conditions.append(CrawlerTask.platform == platform)
        if crawler_type:
            conditions.append(CrawlerTask.crawler_type == crawler_type)
        if user_id:
            conditions.append(CrawlerTask.user_id == user_id)
        if session_id:
            conditions.append(CrawlerTask.session_id == session_id)
        if keyword:
            conditions.append(CrawlerTask.task_name.like(f"%{keyword}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(CrawlerTask.created_at.desc()).offset(skip).limit(page_size)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_tasks(
        self,
        session: AsyncSession,
        *,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        crawler_type: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> int:
        """
        统计任务数量
        """
        query = select(func.count()).select_from(CrawlerTask)
        conditions = []
        
        if status:
            conditions.append(CrawlerTask.status == status)
        if platform:
            conditions.append(CrawlerTask.platform == platform)
        if crawler_type:
            conditions.append(CrawlerTask.crawler_type == crawler_type)
        if user_id:
            conditions.append(CrawlerTask.user_id == user_id)
        if session_id:
            conditions.append(CrawlerTask.session_id == session_id)
        if keyword:
            conditions.append(CrawlerTask.task_name.like(f"%{keyword}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def get_stats(
        self,
        session: AsyncSession,
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        获取任务统计数据
        
        Args:
            session: 数据库会话
            user_id: 用户ID筛选
            session_id: 会话ID筛选
            
        Returns:
            统计数据字典
        """
        base_filters = {}
        if user_id:
            base_filters["user_id"] = user_id
        if session_id:
            base_filters["session_id"] = session_id
        
        pending = await self.count_tasks(session, status=TaskStatus.PENDING.value, **base_filters)
        running = await self.count_tasks(session, status=TaskStatus.RUNNING.value, **base_filters)
        completed = await self.count_tasks(session, status=TaskStatus.COMPLETED.value, **base_filters)
        failed = await self.count_tasks(session, status=TaskStatus.FAILED.value, **base_filters)
        cancelled = await self.count_tasks(session, status=TaskStatus.CANCELLED.value, **base_filters)
        
        total = pending + running + completed + failed + cancelled
        
        return {
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "total": total
        }
    
    async def get_pending_tasks(
        self,
        session: AsyncSession,
        *,
        limit: int = 10
    ) -> List[CrawlerTask]:
        """
        获取待执行的任务（按优先级排序）
        
        Args:
            session: 数据库会话
            limit: 数量限制
            
        Returns:
            任务列表
        """
        result = await session.execute(
            select(CrawlerTask)
            .where(CrawlerTask.status == TaskStatus.PENDING.value)
            .order_by(CrawlerTask.priority.desc(), CrawlerTask.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def delete_task(
        self, 
        session: AsyncSession, 
        *, 
        task_id: str
    ) -> int:
        """
        删除任务
        
        Args:
            session: 数据库会话
            task_id: 任务唯一ID
            
        Returns:
            影响的行数
        """
        return await self.delete_by_field(session, field_name="task_id", field_value=task_id)
    
    async def batch_delete(
        self,
        session: AsyncSession,
        *,
        task_ids: List[str]
    ) -> int:
        """
        批量删除任务
        
        Args:
            session: 数据库会话
            task_ids: 任务ID列表
            
        Returns:
            影响的行数
        """
        from sqlalchemy import delete
        
        stmt = delete(CrawlerTask).where(CrawlerTask.task_id.in_(task_ids))
        result = await session.execute(stmt)
        return result.rowcount


class TaskLogCRUD(CRUDBase[TaskLog, None, None]):
    """任务日志CRUD操作"""
    
    def __init__(self):
        super().__init__(TaskLog)
    
    async def create_log(
        self, 
        session: AsyncSession, 
        *,
        task_id: str,
        level: str = "info",
        message: str = "",
        extra: Dict[str, Any] = None
    ) -> TaskLog:
        """
        创建日志
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            level: 日志级别
            message: 日志内容
            extra: 扩展信息
            
        Returns:
            创建的日志实例
        """
        log_data = {
            "log_id": generate_uuid(),
            "task_id": task_id,
            "level": level,
            "message": message,
            "extra": json.dumps(extra or {}, ensure_ascii=False),
            "created_at": get_timestamp_seconds(),
        }
        
        return await self.create_from_dict(session, obj_in=log_data)
    
    async def get_logs_by_task(
        self,
        session: AsyncSession,
        task_id: str,
        *,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskLog]:
        """
        获取任务日志
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            level: 日志级别筛选
            limit: 数量限制
            offset: 偏移量
            
        Returns:
            日志列表
        """
        query = select(TaskLog).where(TaskLog.task_id == task_id)
        
        if level:
            query = query.where(TaskLog.level == level)
        
        query = query.order_by(TaskLog.created_at.desc()).offset(offset).limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_logs_by_task(
        self,
        session: AsyncSession,
        task_id: str,
        *,
        level: Optional[str] = None
    ) -> int:
        """
        统计任务日志数量
        """
        query = select(func.count()).select_from(TaskLog).where(TaskLog.task_id == task_id)
        
        if level:
            query = query.where(TaskLog.level == level)
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def delete_logs_by_task(
        self, 
        session: AsyncSession, 
        *, 
        task_id: str
    ) -> int:
        """
        删除任务的所有日志
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            影响的行数
        """
        return await self.delete_by_field(session, field_name="task_id", field_value=task_id)


# 单例实例
task_crud = TaskCRUD()
task_log_crud = TaskLogCRUD()
