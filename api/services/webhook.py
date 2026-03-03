"""
Webhook 回调服务 - 任务完成时主动推送结果给外部系统(AI Agent 等)
支持 HMAC-SHA256 签名验证和失败重试。
"""
import hmac
import json
import hashlib
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 15]


async def send_webhook(
    url: str,
    secret: str,
    event: str,
    payload: Dict[str, Any],
    *,
    retries: int = MAX_RETRIES,
) -> bool:
    """
    发送 Webhook 回调。

    Args:
        url: 回调 URL
        secret: HMAC 签名密钥（空字符串则不签名）
        event: 事件类型 (e.g. "task.completed")
        payload: 事件数据
        retries: 最大重试次数

    Returns:
        是否发送成功
    """
    if not url:
        return False

    body = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": payload,
    }
    body_bytes = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MediaCrawler-Webhook/1.0",
        "X-Webhook-Event": event,
    }

    if secret:
        signature = hmac.new(
            secret.encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, content=body_bytes, headers=headers)

            if 200 <= resp.status_code < 300:
                logger.info(f"Webhook sent: event={event} url={url} status={resp.status_code}")
                return True
            else:
                logger.warning(
                    f"Webhook failed: event={event} url={url} "
                    f"status={resp.status_code} attempt={attempt + 1}/{retries + 1}"
                )

        except Exception as e:
            logger.warning(
                f"Webhook error: event={event} url={url} "
                f"error={e} attempt={attempt + 1}/{retries + 1}"
            )

        if attempt < retries:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            await asyncio.sleep(delay)

    logger.error(f"Webhook exhausted retries: event={event} url={url}")
    return False


async def send_task_completed_webhook(
    url: str,
    secret: str,
    *,
    task_id: str,
    schedule_id: Optional[str] = None,
    platform: str = "",
    crawler_type: str = "",
    stats: Optional[Dict[str, Any]] = None,
) -> bool:
    """发送任务完成 Webhook"""
    payload = {
        "task_id": task_id,
        "platform": platform,
        "crawler_type": crawler_type,
        "stats": stats or {},
        "result_url": f"/api/data/export?task_id={task_id}&format=json",
    }
    if schedule_id:
        payload["schedule_id"] = schedule_id

    return await send_webhook(url, secret, "task.completed", payload)


async def send_task_failed_webhook(
    url: str,
    secret: str,
    *,
    task_id: str,
    schedule_id: Optional[str] = None,
    error_message: str = "",
) -> bool:
    """发送任务失败 Webhook"""
    payload = {
        "task_id": task_id,
        "error_message": error_message,
    }
    if schedule_id:
        payload["schedule_id"] = schedule_id

    return await send_webhook(url, secret, "task.failed", payload)
