"""
Schedule CRUD 操作
"""
import json
import time
import logging
from typing import Optional, List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import CrawlerSchedule

logger = logging.getLogger(__name__)


class ScheduleCRUD:
    async def create(
        self,
        db: AsyncSession,
        *,
        schedule_id: str,
        schedule_name: str,
        platform: str,
        crawler_type: str,
        task_config: dict,
        trigger_type: str,
        cron_expression: str = "",
        interval_seconds: int = 0,
        timezone: str = "Asia/Shanghai",
        webhook_url: str = "",
        webhook_secret: str = "",
        created_by: str = "",
    ) -> CrawlerSchedule:
        now = int(time.time())
        model = CrawlerSchedule(
            schedule_id=schedule_id,
            schedule_name=schedule_name,
            platform=platform,
            crawler_type=crawler_type,
            task_config=json.dumps(task_config, ensure_ascii=False),
            trigger_type=trigger_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            timezone=timezone,
            enabled=1,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        db.add(model)
        await db.flush()
        return model

    async def get_by_id(self, db: AsyncSession, schedule_id: str) -> Optional[CrawlerSchedule]:
        result = await db.execute(
            select(CrawlerSchedule).where(CrawlerSchedule.schedule_id == schedule_id)
        )
        return result.scalars().first()

    async def list_all(
        self,
        db: AsyncSession,
        *,
        platform: Optional[str] = None,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CrawlerSchedule]:
        query = select(CrawlerSchedule).order_by(CrawlerSchedule.created_at.desc())
        if platform:
            query = query.where(CrawlerSchedule.platform == platform)
        if enabled_only:
            query = query.where(CrawlerSchedule.enabled == 1)
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        db: AsyncSession,
        *,
        platform: Optional[str] = None,
        enabled_only: bool = False,
    ) -> int:
        query = select(func.count(CrawlerSchedule.id))
        if platform:
            query = query.where(CrawlerSchedule.platform == platform)
        if enabled_only:
            query = query.where(CrawlerSchedule.enabled == 1)
        result = await db.execute(query)
        return result.scalar() or 0

    async def update_fields(
        self, db: AsyncSession, schedule_id: str, **kwargs
    ) -> bool:
        kwargs["updated_at"] = int(time.time())
        result = await db.execute(
            update(CrawlerSchedule)
            .where(CrawlerSchedule.schedule_id == schedule_id)
            .values(**kwargs)
        )
        return result.rowcount > 0

    async def set_enabled(self, db: AsyncSession, schedule_id: str, enabled: bool) -> bool:
        return await self.update_fields(db, schedule_id, enabled=1 if enabled else 0)

    async def record_run(self, db: AsyncSession, schedule_id: str, next_run_at: int = 0) -> bool:
        now = int(time.time())
        model = await self.get_by_id(db, schedule_id)
        if not model:
            return False
        new_total = (model.total_runs or 0) + 1
        return await self.update_fields(
            db, schedule_id,
            last_run_at=now,
            next_run_at=next_run_at,
            total_runs=new_total,
        )

    async def delete(self, db: AsyncSession, schedule_id: str) -> bool:
        model = await self.get_by_id(db, schedule_id)
        if model:
            await db.delete(model)
            return True
        return False


schedule_crud = ScheduleCRUD()
