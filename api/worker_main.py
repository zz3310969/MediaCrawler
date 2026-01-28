"""
Worker 入口
独立进程运行，负责执行任务
"""
import asyncio
import signal
import logging
from typing import Dict

from api.services.factory import get_services
from api.services.task_executor import TaskExecutor, CrawlerFunc, TaskContext
from api.schemas.task import Task

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ========== 爬虫注册 ==========

async def xhs_crawler(task: Task, ctx: TaskContext) -> None:
    """小红书爬虫"""
    await ctx.info("Starting XHS crawler...")
    
    # TODO: 集成真实的爬虫逻辑
    # from media_platform.xhs import XhsCrawler
    
    total = task.config.max_notes
    for i in range(total):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        await ctx.info(f"Crawled item {i + 1}/{total}")
        await asyncio.sleep(0.1)  # 模拟爬取延迟
    
    await ctx.info("XHS crawler finished")


async def douyin_crawler(task: Task, ctx: TaskContext) -> None:
    """抖音爬虫"""
    await ctx.info("Starting Douyin crawler...")
    
    total = task.config.max_notes
    for i in range(total):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        await asyncio.sleep(0.1)
    
    await ctx.info("Douyin crawler finished")


async def bilibili_crawler(task: Task, ctx: TaskContext) -> None:
    """B站爬虫"""
    await ctx.info("Starting Bilibili crawler...")
    
    total = task.config.max_notes
    for i in range(total):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        await asyncio.sleep(0.1)
    
    await ctx.info("Bilibili crawler finished")


async def weibo_crawler(task: Task, ctx: TaskContext) -> None:
    """微博爬虫"""
    await ctx.info("Starting Weibo crawler...")
    
    total = task.config.max_notes
    for i in range(total):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        await asyncio.sleep(0.1)
    
    await ctx.info("Weibo crawler finished")


async def wechat_crawler(task: Task, ctx: TaskContext) -> None:
    """微信爬虫"""
    await ctx.info("Starting WeChat crawler...")
    
    total = task.config.max_notes
    for i in range(total):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        await asyncio.sleep(0.1)
    
    await ctx.info("WeChat crawler finished")


CRAWLERS: Dict[str, CrawlerFunc] = {
    "xhs": xhs_crawler,
    "dy": douyin_crawler,
    "bili": bilibili_crawler,
    "wb": weibo_crawler,
    "wechat": wechat_crawler,
}


# ========== 后台任务 ==========

async def lease_reclaim_task(queue, interval: int = 60):
    """租约回收后台任务"""
    while True:
        try:
            count = await queue.reclaim_expired_leases()
            if count > 0:
                logger.info(f"Reclaimed {count} expired leases")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Lease reclaim error: {e}")
        await asyncio.sleep(interval)


async def delayed_promote_task(queue, interval: int = 10):
    """延迟任务提升后台任务"""
    while True:
        try:
            count = await queue.promote_delayed()
            if count > 0:
                logger.debug(f"Promoted {count} delayed tasks")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Delayed promote error: {e}")
        await asyncio.sleep(interval)


# ========== 主函数 ==========

async def main():
    """Worker 主函数"""
    # 获取服务
    services = get_services()
    
    # 启动事件总线
    await services["event_bus"].start()
    
    # 创建并发控制
    global_sem = asyncio.Semaphore(10)
    platform_sems = {
        "xhs": asyncio.Semaphore(2),
        "dy": asyncio.Semaphore(2),
        "bili": asyncio.Semaphore(3),
        "wb": asyncio.Semaphore(2),
        "wechat": asyncio.Semaphore(3),
    }
    
    # 创建执行器
    executor = TaskExecutor(
        worker_id="worker-main",
        queue=services["queue"],
        storage=services["storage"],
        event_bus=services["event_bus"],
        crawlers=CRAWLERS,
        global_semaphore=global_sem,
        platform_semaphores=platform_sems
    )
    
    # 设置信号处理
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # 启动执行器
    await executor.start(worker_count=4)
    
    # 启动后台任务
    bg_tasks = [
        asyncio.create_task(lease_reclaim_task(services["queue"])),
        asyncio.create_task(delayed_promote_task(services["queue"]))
    ]
    
    logger.info("Worker started, waiting for tasks...")
    
    # 等待停止信号
    await stop_event.wait()
    
    # 优雅关闭
    logger.info("Shutting down...")
    
    # 取消后台任务
    for task in bg_tasks:
        task.cancel()
    await asyncio.gather(*bg_tasks, return_exceptions=True)
    
    await executor.stop(graceful_timeout=30)
    await services["event_bus"].stop()
    
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())

