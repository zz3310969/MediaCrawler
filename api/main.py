# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/main.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
MediaCrawler WebUI API Server
Start command: uvicorn api.main:app --port 8080 --reload
Or: python -m api.main

环境变量:
- INTEGRATED_WORKER=1  启用集成 Worker 模式（开发测试用，Worker 与 API 同进程运行）
"""
import asyncio
import os
import sys
import subprocess
import uvicorn
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .routers import crawler_router, data_router, websocket_router, wechat_router
from .routers.auth import router as auth_router
from .routers.tasks import router as tasks_router
from .routers.ws_tasks import router as ws_tasks_router, setup_event_subscriptions, cleanup_event_subscriptions
from .routers.proxy import router as proxy_router
from .middleware.session import SessionMiddleware
from .services.factory import get_services, get_event_bus
from .services.task_executor import TaskExecutor, CrawlerFunc, TaskContext
from .schemas.task import Task
import config
from database import db

logger = logging.getLogger(__name__)

# ========== 集成 Worker 爬虫函数 ==========
# 当 INTEGRATED_WORKER=1 时，这些爬虫在 API 同进程运行

# 检查是否使用真实爬虫
USE_REAL_CRAWLER = os.environ.get("USE_REAL_CRAWLER", "0") == "1"


async def real_crawler(task: Task, ctx: TaskContext) -> None:
    """
    真实爬虫 - 通过子进程调用 MediaCrawler
    支持所有平台: xhs, dy, bili, wb, wechat, ks, tieba, zhihu
    """
    from .services.crawler_adapter import run_crawler_task
    await run_crawler_task(task, ctx)


async def mock_crawler(task: Task, ctx: TaskContext, platform_name: str) -> None:
    """Mock 爬虫 - 用于测试"""
    await ctx.info(f"Starting {platform_name} crawler (Mock Mode)...")
    total = task.config.max_notes
    for i in range(total):
        ctx.check_cancelled()
        await ctx.update_progress(i + 1, total, items_crawled=i + 1)
        await ctx.info(f"[Mock] Crawled item {i + 1}/{total}")
        await asyncio.sleep(0.1)  # 模拟爬取延迟
    await ctx.info(f"{platform_name} crawler finished (Mock)")


async def xhs_crawler(task: Task, ctx: TaskContext) -> None:
    """小红书爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "XHS")


async def douyin_crawler(task: Task, ctx: TaskContext) -> None:
    """抖音爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "Douyin")


async def bilibili_crawler(task: Task, ctx: TaskContext) -> None:
    """B站爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "Bilibili")


async def weibo_crawler(task: Task, ctx: TaskContext) -> None:
    """微博爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "Weibo")


async def wechat_crawler(task: Task, ctx: TaskContext) -> None:
    """微信爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "WeChat")


async def kuaishou_crawler(task: Task, ctx: TaskContext) -> None:
    """快手爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "Kuaishou")


async def tieba_crawler(task: Task, ctx: TaskContext) -> None:
    """贴吧爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "Tieba")


async def zhihu_crawler(task: Task, ctx: TaskContext) -> None:
    """知乎爬虫"""
    if USE_REAL_CRAWLER:
        await real_crawler(task, ctx)
    else:
        await mock_crawler(task, ctx, "Zhihu")


INTEGRATED_CRAWLERS: Dict[str, CrawlerFunc] = {
    "xhs": xhs_crawler,
    "dy": douyin_crawler,
    "bili": bilibili_crawler,
    "wb": weibo_crawler,
    "wechat": wechat_crawler,
    "ks": kuaishou_crawler,
    "tieba": tieba_crawler,
    "zhihu": zhihu_crawler,
}

# 全局 executor 引用（用于关闭）
_integrated_executor: Optional[TaskExecutor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """API 服务生命周期管理"""
    global _integrated_executor
    
    # 启动时执行
    print("[API] MediaCrawler WebUI API 正在启动...")
    
    # 检查是否启用集成 Worker 模式
    integrated_worker = os.environ.get("INTEGRATED_WORKER", "0") == "1"
    use_real_crawler = os.environ.get("USE_REAL_CRAWLER", "0") == "1"
    
    if integrated_worker:
        print("[API] 🔧 集成 Worker 模式已启用（开发测试用）")
        if use_real_crawler:
            print("[API] 🕷️  真实爬虫模式 - 将调用 MediaCrawler 执行真实爬取")
        else:
            print("[API] 🧪 Mock 爬虫模式 - 仅模拟进度（设置 USE_REAL_CRAWLER=1 启用真实爬虫）")
    
    # 解析命令行参数（如果有的话）
    # 这样可以支持 --save_data_option 等参数
    if len(sys.argv) > 1 and not any(arg.startswith('api.main') or arg == '-m' for arg in sys.argv[:3]):
        try:
            import cmd_arg
            await cmd_arg.parse_cmd()
            print(f"[API] 已应用命令行参数")
        except SystemExit:
            # parse_cmd 可能会触发 help 等退出，忽略
            pass
        except Exception as e:
            print(f"[API] 解析命令行参数失败（将使用配置文件）: {e}")
    
    # 如果使用数据库模式，验证数据库连接
    if config.SAVE_DATA_OPTION in ("db", "sqlite", "mysql", "postgres"):
        print(f"[API] 正在验证数据库连接...")
        if not await db.verify_connection():
            print(f"[API] ⚠️  数据库连接失败，请检查数据库配置和连接状态")
            print(f"[API] 当前数据库类型: {config.SAVE_DATA_OPTION}")
            print(f"[API] API 服务将继续启动，但数据存储功能可能不可用")
        else:
            print(f"[API] ✓ 数据库连接验证成功")
    
    # 初始化多任务服务
    print("[API] 正在初始化多任务服务...")
    try:
        services = get_services()
        event_bus = services["event_bus"]
        await event_bus.start()
        await setup_event_subscriptions()
        print("[API] ✓ 多任务服务初始化完成")
    except Exception as e:
        print(f"[API] ⚠️  多任务服务初始化失败: {e}")
    
    # 如果启用集成 Worker 模式，启动 TaskExecutor
    if integrated_worker:
        try:
            print("[API] 正在启动集成 Worker...")
            
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
            _integrated_executor = TaskExecutor(
                worker_id="integrated-worker",
                queue=services["queue"],
                storage=services["storage"],
                event_bus=services["event_bus"],
                crawlers=INTEGRATED_CRAWLERS,
                global_semaphore=global_sem,
                platform_semaphores=platform_sems
            )
            
            # 启动执行器
            await _integrated_executor.start(worker_count=4)
            print("[API] ✓ 集成 Worker 已启动 (4 workers)")
        except Exception as e:
            print(f"[API] ⚠️  集成 Worker 启动失败: {e}")
            _integrated_executor = None
    
    print(f"[API] ✓ API 服务启动完成")
    
    yield
    
    # 关闭时执行
    print("[API] API 服务正在关闭...")
    
    # 停止集成 Worker
    if _integrated_executor is not None:
        try:
            print("[API] 正在停止集成 Worker...")
            await _integrated_executor.stop(graceful_timeout=10)
            print("[API] ✓ 集成 Worker 已停止")
        except Exception as e:
            print(f"[API] ⚠️  集成 Worker 停止失败: {e}")
    
    # 清理多任务服务
    try:
        await cleanup_event_subscriptions()
        event_bus = get_event_bus()
        await event_bus.stop()
        print("[API] ✓ 多任务服务已关闭")
    except Exception as e:
        print(f"[API] ⚠️  多任务服务关闭失败: {e}")


app = FastAPI(
    title="MediaCrawler WebUI API",
    description="API for controlling MediaCrawler from WebUI",
    version="1.0.0",
    lifespan=lifespan
)

# Get webui static files directory
WEBUI_DIR = os.path.join(os.path.dirname(__file__), "webui")

# CORS configuration - allow frontend dev server access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Backup port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for multi-task support
app.add_middleware(SessionMiddleware)

# Register routers
app.include_router(crawler_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(wechat_router, prefix="/api")

# Multi-task routers
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(ws_tasks_router)

# Proxy management router
app.include_router(proxy_router, prefix="/api")


@app.get("/")
async def serve_frontend():
    """Return frontend page"""
    index_path = os.path.join(WEBUI_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "MediaCrawler WebUI API",
        "version": "1.0.0",
        "docs": "/docs",
        "note": "WebUI not found, please build it first: cd webui && npm run build"
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/db/check")
async def check_database():
    """检查数据库连接状态"""
    try:
        db_type = config.SAVE_DATA_OPTION
        
        # 如果不是数据库模式
        if db_type in ["json", "csv", "excel"]:
            return {
                "success": True,
                "db_type": db_type,
                "message": f"当前使用文件存储模式 ({db_type})，无需数据库连接",
                "need_db": False
            }
        
        # 验证数据库连接
        is_connected = await db.verify_connection(db_type)
        
        if is_connected:
            return {
                "success": True,
                "db_type": db_type,
                "message": f"{db_type} 数据库连接正常",
                "need_db": True
            }
        else:
            return {
                "success": False,
                "db_type": db_type,
                "message": f"{db_type} 数据库连接失败，请检查配置",
                "need_db": True
            }
    except Exception as e:
        return {
            "success": False,
            "db_type": config.SAVE_DATA_OPTION,
            "message": f"数据库连接检查失败: {str(e)}",
            "error": str(e),
            "need_db": True
        }


@app.get("/api/env/check")
async def check_environment():
    """Check if MediaCrawler environment is configured correctly"""
    try:
        # Run uv run main.py --help command to check environment
        process = await asyncio.create_subprocess_exec(
            "uv", "run", "main.py", "--help",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="."  # Project root directory
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=30.0  # 30 seconds timeout
        )

        if process.returncode == 0:
            return {
                "success": True,
                "message": "MediaCrawler environment configured correctly",
                "output": stdout.decode("utf-8", errors="ignore")[:500]  # Truncate to first 500 characters
            }
        else:
            error_msg = stderr.decode("utf-8", errors="ignore") or stdout.decode("utf-8", errors="ignore")
            return {
                "success": False,
                "message": "Environment check failed",
                "error": error_msg[:500]
            }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": "Environment check timeout",
            "error": "Command execution exceeded 30 seconds"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "uv command not found",
            "error": "Please ensure uv is installed and configured in system PATH"
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Environment check error",
            "error": str(e)
        }


@app.get("/api/config/platforms")
async def get_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {"value": "xhs", "label": "Xiaohongshu", "icon": "book-open"},
            {"value": "dy", "label": "Douyin", "icon": "music"},
            {"value": "ks", "label": "Kuaishou", "icon": "video"},
            {"value": "bili", "label": "Bilibili", "icon": "tv"},
            {"value": "wb", "label": "Weibo", "icon": "message-circle"},
            {"value": "wechat", "label": "WeChat MP", "icon": "message-square"},
            {"value": "tieba", "label": "Baidu Tieba", "icon": "messages-square"},
            {"value": "zhihu", "label": "Zhihu", "icon": "help-circle"},
        ]
    }


@app.get("/api/config/options")
async def get_config_options():
    """Get all configuration options"""
    return {
        "login_types": [
            {"value": "qrcode", "label": "QR Code Login"},
            {"value": "mp_qrcode", "label": "WeChat MP Backend Login"},
            {"value": "cookie", "label": "Cookie Login"},
        ],
        "crawler_types": [
            {"value": "search", "label": "Search Mode"},
            {"value": "detail", "label": "Detail Mode"},
            {"value": "creator", "label": "Creator Mode"},
            {"value": "creator_vip", "label": "VIP Content Mode (Weibo)"},
            {"value": "album", "label": "Album Mode (WeChat)"},
        ],
        "save_options": [
            {"value": "json", "label": "JSON File"},
            {"value": "csv", "label": "CSV File"},
            {"value": "excel", "label": "Excel File"},
            {"value": "sqlite", "label": "SQLite Database"},
            {"value": "db", "label": "MySQL Database"},
            {"value": "mongodb", "label": "MongoDB Database"},
        ],
        "incremental_config": {
            "description": "Incremental crawling (only fetch new content, 10-100x faster)",
            "supports_platforms": ["xhs", "wb", "dy", "bili"],  # 支持的平台
            "supports_crawler_types": ["creator", "creator_vip"],  # 支持的爬取类型
            "default_enabled": False,
            "default_threshold": 3,
            "threshold_range": {"min": 1, "max": 10},
        },
    }


# Mount static resources - must be placed after all routes
if os.path.exists(WEBUI_DIR):
    assets_dir = os.path.join(WEBUI_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    # Mount logos directory
    logos_dir = os.path.join(WEBUI_DIR, "logos")
    if os.path.exists(logos_dir):
        app.mount("/logos", StaticFiles(directory=logos_dir), name="logos")
    # Mount other static files (e.g., vite.svg)
    app.mount("/static", StaticFiles(directory=WEBUI_DIR), name="webui-static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
