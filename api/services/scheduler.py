"""
定时调度服务 - 基于 APScheduler 实现 Cron / Interval / Once 调度
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from api.schemas.schedule import (
    Schedule,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    ScheduleResponse,
    TriggerType,
)
from api.schemas.task import TaskCreateRequest, TaskConfig

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时调度管理服务"""

    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._started = False

    async def start(self):
        """启动调度器并从数据库恢复已有计划"""
        if self._started:
            return
        self._scheduler.start()
        self._started = True
        logger.info("SchedulerService started")
        await self._restore_schedules()

    async def stop(self):
        """停止调度器"""
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("SchedulerService stopped")

    # ========== Schedule CRUD ==========

    async def create_schedule(
        self,
        request: ScheduleCreateRequest,
        created_by: str = "",
    ) -> ScheduleResponse:
        """创建定时调度计划"""
        schedule_id = str(uuid.uuid4())
        task_config_dict = request.task_config.model_dump()

        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        async with get_db_session() as db:
            if db is None:
                raise RuntimeError("Database not available")

            model = await schedule_crud.create(
                db,
                schedule_id=schedule_id,
                schedule_name=request.schedule_name,
                platform=request.task_config.platform,
                crawler_type=request.task_config.crawler_type,
                task_config=task_config_dict,
                trigger_type=request.trigger_type.value,
                cron_expression=request.cron_expression or "",
                interval_seconds=request.interval_seconds or 0,
                timezone=request.timezone,
                webhook_url=request.webhook_url or "",
                webhook_secret=request.webhook_secret or "",
                created_by=created_by,
            )

        self._register_job(
            schedule_id=schedule_id,
            trigger_type=request.trigger_type.value,
            cron_expression=request.cron_expression,
            interval_seconds=request.interval_seconds,
            timezone=request.timezone,
        )

        logger.info(f"Schedule created: {schedule_id} name={request.schedule_name}")
        return await self.get_schedule(schedule_id)

    async def get_schedule(self, schedule_id: str) -> ScheduleResponse:
        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        async with get_db_session() as db:
            model = await schedule_crud.get_by_id(db, schedule_id)
            if not model:
                raise ValueError(f"Schedule not found: {schedule_id}")
            return self._model_to_response(model)

    async def list_schedules(
        self,
        platform: Optional[str] = None,
        enabled_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ScheduleResponse], int]:
        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        offset = (page - 1) * page_size

        async with get_db_session() as db:
            models = await schedule_crud.list_all(
                db, platform=platform, enabled_only=enabled_only,
                limit=page_size, offset=offset,
            )
            total = await schedule_crud.count(
                db, platform=platform, enabled_only=enabled_only,
            )

        return [self._model_to_response(m) for m in models], total

    async def update_schedule(
        self, schedule_id: str, request: ScheduleUpdateRequest
    ) -> ScheduleResponse:
        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        update_kwargs = {}
        if request.schedule_name is not None:
            update_kwargs["schedule_name"] = request.schedule_name
        if request.task_config is not None:
            cfg = request.task_config.model_dump()
            update_kwargs["task_config"] = json.dumps(cfg, ensure_ascii=False)
            update_kwargs["platform"] = request.task_config.platform
            update_kwargs["crawler_type"] = request.task_config.crawler_type
        if request.trigger_type is not None:
            update_kwargs["trigger_type"] = request.trigger_type.value
        if request.cron_expression is not None:
            update_kwargs["cron_expression"] = request.cron_expression
        if request.interval_seconds is not None:
            update_kwargs["interval_seconds"] = request.interval_seconds
        if request.timezone is not None:
            update_kwargs["timezone"] = request.timezone
        if request.webhook_url is not None:
            update_kwargs["webhook_url"] = request.webhook_url
        if request.webhook_secret is not None:
            update_kwargs["webhook_secret"] = request.webhook_secret

        async with get_db_session() as db:
            await schedule_crud.update_fields(db, schedule_id, **update_kwargs)

        self._remove_job(schedule_id)
        sched = await self.get_schedule(schedule_id)
        if sched.enabled:
            self._register_job(
                schedule_id=schedule_id,
                trigger_type=sched.trigger_type,
                cron_expression=sched.cron_expression,
                interval_seconds=sched.interval_seconds,
                timezone=sched.timezone,
            )

        logger.info(f"Schedule updated: {schedule_id}")
        return sched

    async def delete_schedule(self, schedule_id: str) -> bool:
        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        self._remove_job(schedule_id)

        async with get_db_session() as db:
            result = await schedule_crud.delete(db, schedule_id)

        logger.info(f"Schedule deleted: {schedule_id}")
        return result

    async def pause_schedule(self, schedule_id: str) -> ScheduleResponse:
        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        self._remove_job(schedule_id)

        async with get_db_session() as db:
            await schedule_crud.set_enabled(db, schedule_id, False)

        logger.info(f"Schedule paused: {schedule_id}")
        return await self.get_schedule(schedule_id)

    async def resume_schedule(self, schedule_id: str) -> ScheduleResponse:
        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        async with get_db_session() as db:
            await schedule_crud.set_enabled(db, schedule_id, True)

        sched = await self.get_schedule(schedule_id)
        self._register_job(
            schedule_id=schedule_id,
            trigger_type=sched.trigger_type,
            cron_expression=sched.cron_expression,
            interval_seconds=sched.interval_seconds,
            timezone=sched.timezone,
        )

        logger.info(f"Schedule resumed: {schedule_id}")
        return sched

    async def trigger_now(self, schedule_id: str) -> str:
        """立即触发一次，返回 task_id"""
        return await self._trigger_task(schedule_id)

    # ========== 内部方法 ==========

    def _register_job(
        self,
        schedule_id: str,
        trigger_type: str,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        timezone: str = "Asia/Shanghai",
    ):
        """在 APScheduler 中注册 Job"""
        job_id = f"schedule_{schedule_id}"

        self._remove_job(schedule_id)

        if trigger_type == TriggerType.CRON.value and cron_expression:
            parts = cron_expression.strip().split()
            trigger_kwargs = {}
            if len(parts) >= 1:
                trigger_kwargs["minute"] = parts[0]
            if len(parts) >= 2:
                trigger_kwargs["hour"] = parts[1]
            if len(parts) >= 3:
                trigger_kwargs["day"] = parts[2]
            if len(parts) >= 4:
                trigger_kwargs["month"] = parts[3]
            if len(parts) >= 5:
                trigger_kwargs["day_of_week"] = parts[4]

            trigger = CronTrigger(timezone=timezone, **trigger_kwargs)

        elif trigger_type == TriggerType.INTERVAL.value and interval_seconds:
            trigger = IntervalTrigger(seconds=interval_seconds, timezone=timezone)

        elif trigger_type == TriggerType.ONCE.value:
            trigger = DateTrigger(
                run_date=datetime.now() + timedelta(seconds=5),
                timezone=timezone,
            )
        else:
            logger.warning(f"Cannot register job for schedule {schedule_id}: invalid trigger config")
            return

        self._scheduler.add_job(
            self._trigger_task,
            trigger=trigger,
            id=job_id,
            args=[schedule_id],
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(f"Job registered: {job_id} trigger={trigger_type}")

    def _remove_job(self, schedule_id: str):
        """从 APScheduler 移除 Job"""
        job_id = f"schedule_{schedule_id}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

    async def _trigger_task(self, schedule_id: str) -> str:
        """被 APScheduler 触发时调用：根据 schedule 配置创建一个新 Task"""
        try:
            from database.db_session import get_session as get_db_session
            from api.services.crud.schedule import schedule_crud
            from api.services.factory import get_task_manager

            async with get_db_session() as db:
                model = await schedule_crud.get_by_id(db, schedule_id)
                if not model:
                    logger.error(f"Schedule not found when triggering: {schedule_id}")
                    return ""

                task_config_dict = json.loads(model.task_config) if isinstance(model.task_config, str) else model.task_config

                next_run_ts = int(datetime.now(timezone.utc).timestamp()) + (model.interval_seconds or 86400)
                await schedule_crud.record_run(db, schedule_id, next_run_at=next_run_ts)

            task_config = TaskConfig(**task_config_dict)
            create_request = TaskCreateRequest(
                task_name=f"[定时] {model.schedule_name}",
                config=task_config,
            )

            session_id = model.created_by or f"schedule:{schedule_id}"
            task_manager = get_task_manager()
            task = await task_manager.create_task(session_id, create_request)

            logger.info(f"Schedule {schedule_id} triggered -> task {task.task_id}")

            if model.webhook_url:
                from api.services.webhook import send_webhook
                await send_webhook(
                    url=model.webhook_url,
                    secret=model.webhook_secret,
                    event="schedule.triggered",
                    payload={
                        "schedule_id": schedule_id,
                        "schedule_name": model.schedule_name,
                        "task_id": task.task_id,
                        "platform": model.platform,
                        "crawler_type": model.crawler_type,
                    },
                )

            return task.task_id

        except Exception as e:
            logger.error(f"Failed to trigger schedule {schedule_id}: {e}", exc_info=True)
            return ""

    async def _restore_schedules(self):
        """从数据库恢复所有 enabled 的调度计划"""
        try:
            from database.db_session import get_session as get_db_session
            from api.services.crud.schedule import schedule_crud

            async with get_db_session() as db:
                if db is None:
                    logger.warning("Database not available, skipping schedule restore")
                    return

                models = await schedule_crud.list_all(db, enabled_only=True, limit=1000)

            count = 0
            for model in models:
                try:
                    self._register_job(
                        schedule_id=model.schedule_id,
                        trigger_type=model.trigger_type,
                        cron_expression=model.cron_expression,
                        interval_seconds=model.interval_seconds,
                        timezone=model.timezone or "Asia/Shanghai",
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to restore schedule {model.schedule_id}: {e}")

            logger.info(f"Restored {count} schedules from database")

        except Exception as e:
            logger.warning(f"Failed to restore schedules: {e}")

    @staticmethod
    def _model_to_response(model) -> ScheduleResponse:
        """将 DB model 转换为 ScheduleResponse"""
        from api.schemas.schedule import ScheduleConfig

        task_config_raw = model.task_config
        if isinstance(task_config_raw, str):
            task_config_raw = json.loads(task_config_raw)

        return ScheduleResponse(
            schedule_id=model.schedule_id,
            schedule_name=model.schedule_name,
            platform=model.platform,
            crawler_type=model.crawler_type,
            task_config=ScheduleConfig(**task_config_raw),
            trigger_type=model.trigger_type,
            cron_expression=model.cron_expression or None,
            interval_seconds=model.interval_seconds or None,
            timezone=model.timezone or "Asia/Shanghai",
            enabled=bool(model.enabled),
            last_run_at=datetime.fromtimestamp(model.last_run_at) if model.last_run_at else None,
            next_run_at=datetime.fromtimestamp(model.next_run_at) if model.next_run_at else None,
            total_runs=model.total_runs or 0,
            webhook_url=model.webhook_url or None,
            created_by=model.created_by or "",
            created_at=datetime.fromtimestamp(model.created_at),
            updated_at=datetime.fromtimestamp(model.updated_at) if model.updated_at else None,
        )


# 全局单例
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
