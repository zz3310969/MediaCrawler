"""
数据库版任务存储实现
基于 CrawlerTask / TaskLog 表持久化任务数据
"""
import json
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_, delete as sa_delete, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from api.interfaces.storage import ITaskStorage
from api.schemas.task import Task, TaskStatus, TaskConfig, TaskProgress, TaskResult, TaskMetadata
from api.schemas.event import LogEntry
from database.webui_models import CrawlerTask, TaskLog

logger = logging.getLogger(__name__)


def _timestamp_to_datetime(ts: int) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _datetime_to_timestamp(dt: Optional[datetime]) -> int:
    if not dt:
        return 0
    return int(dt.timestamp())


def _db_task_to_schema(db_task: CrawlerTask) -> Task:
    """CrawlerTask ORM -> Task pydantic schema"""
    config_dict = json.loads(db_task.config) if db_task.config else {}
    progress_dict = json.loads(db_task.progress) if db_task.progress else {}
    result_dict = json.loads(db_task.result) if db_task.result else {}
    metadata_dict = json.loads(db_task.task_metadata) if db_task.task_metadata else {}

    config_dict.setdefault("platform", db_task.platform)
    config_dict.setdefault("crawler_type", db_task.crawler_type or "search")

    # 从 metadata 中还原 idempotency_key 和 cancel_requested
    idempotency_key = metadata_dict.pop("idempotency_key", None)
    cancel_requested = metadata_dict.pop("cancel_requested", False)

    # 过滤掉 TaskMetadata 不接受的字段
    valid_meta_fields = set(TaskMetadata.model_fields.keys())
    filtered_meta = {k: v for k, v in metadata_dict.items() if k in valid_meta_fields}

    return Task(
        task_id=db_task.task_id,
        user_id=db_task.user_id or None,
        session_id=db_task.session_id or "",
        task_name=db_task.task_name or None,
        platform=db_task.platform,
        crawler_type=db_task.crawler_type,
        status=TaskStatus(db_task.status),
        priority=db_task.priority or 5,
        retry_count=db_task.retry_count or 0,
        max_retries=db_task.max_retries or 3,
        idempotency_key=idempotency_key,
        cancel_requested=cancel_requested,
        error_message=db_task.error_message or None,
        created_at=_timestamp_to_datetime(db_task.created_at) or datetime.now(timezone.utc),
        scheduled_at=_timestamp_to_datetime(db_task.scheduled_at),
        started_at=_timestamp_to_datetime(db_task.started_at),
        finished_at=_timestamp_to_datetime(db_task.finished_at),
        last_heartbeat_at=_timestamp_to_datetime(db_task.last_heartbeat_at),
        config=TaskConfig(**config_dict),
        progress=TaskProgress(**progress_dict) if progress_dict else TaskProgress(),
        result=TaskResult(**result_dict) if result_dict else TaskResult(),
        metadata=TaskMetadata(**filtered_meta) if filtered_meta else TaskMetadata(),
        version=0,
    )


def _schema_to_db_dict(task: Task) -> dict:
    """Task pydantic schema -> dict for CrawlerTask insert/update"""
    now_ts = int(datetime.now(timezone.utc).timestamp())
    
    # 将 idempotency_key 和 cancel_requested 存入 task_metadata
    metadata_dict = task.metadata.model_dump()
    if task.idempotency_key:
        metadata_dict["idempotency_key"] = task.idempotency_key
    if task.cancel_requested:
        metadata_dict["cancel_requested"] = True
    
    return {
        "task_id": task.task_id,
        "user_id": task.user_id or "",
        "session_id": task.session_id,
        "task_name": task.task_name or "",
        "platform": task.config.platform,
        "crawler_type": task.config.crawler_type,
        "status": task.status if isinstance(task.status, str) else task.status.value,
        "priority": task.priority,
        "config": task.config.model_dump_json(),
        "progress": task.progress.model_dump_json(),
        "result": task.result.model_dump_json(),
        "task_metadata": json.dumps(metadata_dict, ensure_ascii=False, default=str),
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "error_message": task.error_message or "",
        "created_at": _datetime_to_timestamp(task.created_at) or now_ts,
        "scheduled_at": _datetime_to_timestamp(task.scheduled_at),
        "started_at": _datetime_to_timestamp(task.started_at),
        "finished_at": _datetime_to_timestamp(task.finished_at),
        "last_heartbeat_at": _datetime_to_timestamp(task.last_heartbeat_at),
    }


class DatabaseTaskStorage(ITaskStorage):
    """数据库版任务存储，基于 crawler_task / task_log 表"""

    def __init__(self, session_factory):
        """
        Args:
            session_factory: async sessionmaker for creating DB sessions
        """
        self._session_factory = session_factory

    def _get_session(self) -> AsyncSession:
        return self._session_factory()

    # ========== 任务 CRUD ==========

    async def create(self, task: Task) -> str:
        async with self._get_session() as session:
            existing = await session.execute(
                select(CrawlerTask).where(CrawlerTask.task_id == task.task_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Task {task.task_id} already exists")

            db_obj = CrawlerTask(**_schema_to_db_dict(task))
            session.add(db_obj)
            await session.commit()
            logger.debug(f"Task {task.task_id[:8]} created in DB")
            return task.task_id

    async def get(self, task_id: str) -> Optional[Task]:
        async with self._get_session() as session:
            result = await session.execute(
                select(CrawlerTask).where(CrawlerTask.task_id == task_id)
            )
            db_task = result.scalar_one_or_none()
            if not db_task:
                return None
            return _db_task_to_schema(db_task)

    async def update(
        self,
        task_id: str,
        data: Dict,
        version: Optional[int] = None
    ) -> bool:
        async with self._get_session() as session:
            result = await session.execute(
                select(CrawlerTask).where(CrawlerTask.task_id == task_id)
            )
            db_task = result.scalar_one_or_none()
            if not db_task:
                return False

            for key, value in data.items():
                if key == "status":
                    db_task.status = value if isinstance(value, str) else value.value
                    if value in (TaskStatus.RUNNING, "running") and not db_task.started_at:
                        db_task.started_at = int(datetime.now(timezone.utc).timestamp())
                    elif value in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED,
                                   "completed", "failed", "cancelled"):
                        db_task.finished_at = int(datetime.now(timezone.utc).timestamp())
                elif key == "progress" and isinstance(value, dict):
                    existing = json.loads(db_task.progress) if db_task.progress else {}
                    existing.update(value)
                    db_task.progress = json.dumps(existing, ensure_ascii=False)
                elif key == "result" and isinstance(value, dict):
                    existing = json.loads(db_task.result) if db_task.result else {}
                    existing.update(value)
                    db_task.result = json.dumps(existing, ensure_ascii=False)
                elif key == "metadata" and isinstance(value, dict):
                    existing = json.loads(db_task.task_metadata) if db_task.task_metadata else {}
                    existing.update(value)
                    db_task.task_metadata = json.dumps(existing, ensure_ascii=False)
                elif key == "config" and isinstance(value, dict):
                    existing = json.loads(db_task.config) if db_task.config else {}
                    existing.update(value)
                    db_task.config = json.dumps(existing, ensure_ascii=False)
                elif key == "error_message":
                    db_task.error_message = str(value) if value else ""
                elif key == "cancel_requested":
                    existing_meta = json.loads(db_task.task_metadata) if db_task.task_metadata else {}
                    existing_meta["cancel_requested"] = bool(value)
                    db_task.task_metadata = json.dumps(existing_meta, ensure_ascii=False)
                elif key == "retry_count":
                    db_task.retry_count = int(value)
                elif key == "priority":
                    db_task.priority = int(value)
                elif key == "last_heartbeat_at":
                    if isinstance(value, datetime):
                        db_task.last_heartbeat_at = int(value.timestamp())
                    elif isinstance(value, (int, float)):
                        db_task.last_heartbeat_at = int(value)
                elif key in ("started_at", "finished_at", "scheduled_at"):
                    if isinstance(value, datetime):
                        setattr(db_task, key, int(value.timestamp()))
                    elif isinstance(value, (int, float)):
                        setattr(db_task, key, int(value))

            db_task.last_heartbeat_at = int(datetime.now(timezone.utc).timestamp())
            session.add(db_task)
            await session.commit()
            return True

    async def delete(self, task_id: str) -> bool:
        async with self._get_session() as session:
            # 同时删除关联日志
            await session.execute(
                sa_delete(TaskLog).where(TaskLog.task_id == task_id)
            )
            result = await session.execute(
                sa_delete(CrawlerTask).where(CrawlerTask.task_id == task_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def exists(self, task_id: str) -> bool:
        async with self._get_session() as session:
            result = await session.execute(
                select(func.count()).select_from(CrawlerTask)
                .where(CrawlerTask.task_id == task_id)
            )
            return (result.scalar() or 0) > 0

    # ========== 批量操作 ==========

    async def get_by_user(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """按 user_id 查询任务，user_id 为空时全量查询（向后兼容）"""
        async with self._get_session() as session:
            query = select(CrawlerTask)
            if user_id:
                query = query.where(CrawlerTask.user_id == user_id)
            if status:
                s = status if isinstance(status, str) else status.value
                query = query.where(CrawlerTask.status == s)
            if platform:
                query = query.where(CrawlerTask.platform == platform)
            query = query.order_by(CrawlerTask.created_at.desc()).offset(offset).limit(limit)

            result = await session.execute(query)
            return [_db_task_to_schema(r) for r in result.scalars().all()]

    async def get_by_session(
        self,
        session_id: str,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """兼容旧接口，委托给 get_by_user（全量查询）"""
        return await self.get_by_user(
            status=status, platform=platform, limit=limit, offset=offset
        )

    async def get_by_status(
        self,
        status: TaskStatus,
        limit: int = 100
    ) -> List[Task]:
        async with self._get_session() as session:
            s = status if isinstance(status, str) else status.value
            query = (
                select(CrawlerTask)
                .where(CrawlerTask.status == s)
                .order_by(CrawlerTask.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            return [_db_task_to_schema(r) for r in result.scalars().all()]

    async def bulk_update_status(
        self,
        task_ids: List[str],
        status: TaskStatus
    ) -> int:
        if not task_ids:
            return 0
        async with self._get_session() as session:
            s = status if isinstance(status, str) else status.value
            now_ts = int(datetime.now(timezone.utc).timestamp())
            update_vals = {"status": s, "last_heartbeat_at": now_ts}
            if s in ("completed", "failed", "cancelled"):
                update_vals["finished_at"] = now_ts
            stmt = (
                sa_update(CrawlerTask)
                .where(CrawlerTask.task_id.in_(task_ids))
                .values(**update_vals)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    async def find_by_idempotency_key(
        self,
        session_id: str,
        idempotency_key: str
    ) -> Optional[Task]:
        # 幂等键存储在 task_metadata JSON 中
        async with self._get_session() as session:
            query = (
                select(CrawlerTask)
                .where(CrawlerTask.session_id == session_id)
                .order_by(CrawlerTask.created_at.desc())
                .limit(200)
            )
            result = await session.execute(query)
            for db_task in result.scalars().all():
                meta = json.loads(db_task.task_metadata) if db_task.task_metadata else {}
                if meta.get("idempotency_key") == idempotency_key:
                    return _db_task_to_schema(db_task)
            return None

    # ========== 日志存储 ==========

    async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
        async with self._get_session() as session:
            db_log = TaskLog(
                log_id=log_entry.log_id,
                task_id=task_id,
                level=log_entry.level if isinstance(log_entry.level, str) else log_entry.level.value,
                message=log_entry.message,
                extra=json.dumps(log_entry.extra, ensure_ascii=False, default=str) if log_entry.extra else "{}",
                created_at=int(log_entry.timestamp.timestamp()) if log_entry.timestamp else int(datetime.now(timezone.utc).timestamp()),
            )
            session.add(db_log)
            await session.commit()
            return True

    async def get_logs(
        self,
        task_id: str,
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        async with self._get_session() as session:
            query = select(TaskLog).where(TaskLog.task_id == task_id)
            if level:
                query = query.where(TaskLog.level == level)
            query = query.order_by(TaskLog.created_at.desc()).offset(offset).limit(limit)

            result = await session.execute(query)
            entries = []
            for db_log in result.scalars().all():
                extra = json.loads(db_log.extra) if db_log.extra else {}
                entries.append(LogEntry(
                    log_id=db_log.log_id,
                    task_id=db_log.task_id,
                    timestamp=_timestamp_to_datetime(db_log.created_at) or datetime.now(timezone.utc),
                    level=db_log.level,
                    message=db_log.message or "",
                    extra=extra,
                ))
            return entries

    async def clear_logs(self, task_id: str) -> bool:
        async with self._get_session() as session:
            await session.execute(
                sa_delete(TaskLog).where(TaskLog.task_id == task_id)
            )
            await session.commit()
            return True

    async def trim_logs(self, task_id: str, max_count: int) -> int:
        async with self._get_session() as session:
            count_result = await session.execute(
                select(func.count()).select_from(TaskLog)
                .where(TaskLog.task_id == task_id)
            )
            total = count_result.scalar() or 0
            if total <= max_count:
                return 0

            to_delete = total - max_count
            oldest = await session.execute(
                select(TaskLog.id)
                .where(TaskLog.task_id == task_id)
                .order_by(TaskLog.created_at.asc())
                .limit(to_delete)
            )
            ids = [r for r in oldest.scalars().all()]
            if ids:
                await session.execute(
                    sa_delete(TaskLog).where(TaskLog.id.in_(ids))
                )
                await session.commit()
            return len(ids)

    # ========== 统计查询 ==========

    async def count_by_status(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, int]:
        """按状态统计任务数，有 user_id 时仅统计该用户"""
        async with self._get_session() as session:
            counts = {s.value: 0 for s in TaskStatus}
            query = (
                select(CrawlerTask.status, func.count())
                .select_from(CrawlerTask)
            )
            if user_id:
                query = query.where(CrawlerTask.user_id == user_id)
            query = query.group_by(CrawlerTask.status)

            result = await session.execute(query)
            for status_val, cnt in result.all():
                if status_val in counts:
                    counts[status_val] = cnt
            return counts

    async def get_recent_tasks(
        self,
        session_id: str,
        limit: int = 10,
        user_id: Optional[str] = None
    ) -> List[Task]:
        return await self.get_by_user(user_id=user_id, limit=limit)

    async def count_by_user(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> int:
        """统计任务数，有 user_id 时仅统计该用户"""
        async with self._get_session() as session:
            query = select(func.count()).select_from(CrawlerTask)
            if user_id:
                query = query.where(CrawlerTask.user_id == user_id)
            result = await session.execute(query)
            return result.scalar() or 0

    async def count_by_session(self, session_id: str) -> int:
        """兼容旧接口，全量统计"""
        return await self.count_by_user()

    # ========== 维护 ==========

    async def cleanup_old_tasks(self, days: int) -> int:
        async with self._get_session() as session:
            cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
            terminal_statuses = [
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            ]
            # 先删关联日志
            subq = (
                select(CrawlerTask.task_id)
                .where(
                    and_(
                        CrawlerTask.created_at < cutoff_ts,
                        CrawlerTask.status.in_(terminal_statuses),
                    )
                )
            )
            await session.execute(
                sa_delete(TaskLog).where(TaskLog.task_id.in_(subq))
            )
            result = await session.execute(
                sa_delete(CrawlerTask).where(
                    and_(
                        CrawlerTask.created_at < cutoff_ts,
                        CrawlerTask.status.in_(terminal_statuses),
                    )
                )
            )
            await session.commit()
            deleted = result.rowcount
            if deleted:
                logger.info(f"Cleaned up {deleted} old tasks from DB")
            return deleted

    async def archive_task(self, task_id: str) -> bool:
        return False
