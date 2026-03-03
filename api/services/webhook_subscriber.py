"""
Webhook EventBus 订阅器
监听任务完成/失败事件，触发 Webhook 回调。
"""
import json
import logging
import asyncio
from typing import List

from api.schemas.event import TaskEvent, EventType
from api.services.webhook import send_task_completed_webhook, send_task_failed_webhook

logger = logging.getLogger(__name__)

_subscription_ids: List[str] = []


async def _webhook_event_handler(event: TaskEvent):
    """处理任务完成/失败事件，查找关联的 schedule 并发送 webhook"""
    if event.event_type not in (EventType.TASK_COMPLETED, EventType.TASK_FAILED):
        return

    try:
        from api.services.factory import get_storage
        storage = get_storage()
        task = await storage.get(event.task_id)
        if not task:
            return

        task_name = task.task_name or ""
        if not task_name.startswith("[定时]"):
            return

        from database.db_session import get_session as get_db_session
        from api.services.crud.schedule import schedule_crud

        async with get_db_session() as db:
            if db is None:
                return

            models = await schedule_crud.list_all(db, enabled_only=False, limit=1000)

            matching_schedule = None
            for model in models:
                if model.webhook_url and model.created_by == task.session_id:
                    matching_schedule = model
                    break

        if not matching_schedule or not matching_schedule.webhook_url:
            return

        if event.event_type == EventType.TASK_COMPLETED:
            asyncio.create_task(send_task_completed_webhook(
                url=matching_schedule.webhook_url,
                secret=matching_schedule.webhook_secret or "",
                task_id=event.task_id,
                schedule_id=matching_schedule.schedule_id,
                platform=task.platform or "",
                crawler_type=task.crawler_type or "",
                stats=task.result.statistics if task.result else {},
            ))
        elif event.event_type == EventType.TASK_FAILED:
            asyncio.create_task(send_task_failed_webhook(
                url=matching_schedule.webhook_url,
                secret=matching_schedule.webhook_secret or "",
                task_id=event.task_id,
                schedule_id=matching_schedule.schedule_id,
                error_message=task.error_message or "",
            ))

    except Exception as e:
        logger.error(f"Webhook event handler error: {e}", exc_info=True)


async def setup_webhook_subscriptions():
    """注册 Webhook 事件订阅"""
    global _subscription_ids
    from api.services.factory import get_event_bus

    event_bus = get_event_bus()

    for event_type in (EventType.TASK_COMPLETED, EventType.TASK_FAILED):
        sub_id = await event_bus.subscribe(event_type, _webhook_event_handler)
        _subscription_ids.append(sub_id)

    logger.info("Webhook event subscriptions set up")


async def cleanup_webhook_subscriptions():
    """清理 Webhook 事件订阅"""
    global _subscription_ids
    from api.services.factory import get_event_bus

    event_bus = get_event_bus()

    for sub_id in _subscription_ids:
        await event_bus.unsubscribe(sub_id)

    _subscription_ids.clear()
    logger.info("Webhook event subscriptions cleaned up")
