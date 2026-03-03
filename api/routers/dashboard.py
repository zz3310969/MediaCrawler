# -*- coding: utf-8 -*-
"""
仪表盘统计路由
提供仪表盘数据的聚合查询接口
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

# psutil 是可选依赖，用于获取系统状态
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

from fastapi import APIRouter, Query

from database.db_session import get_session
from api.schemas.dashboard import (
    DashboardStats, DashboardResponse, SystemStatus, PlatformStats,
    TaskStats, ProxyStats, DataStats, AccountStats, ActivityLog
)
from api.schemas.account import Platform
from api.services.crud.task import task_crud
from api.services.crud.proxy import proxy_crud
from api.services.crud.account import account_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def format_bytes(bytes_value: int) -> str:
    """格式化字节数"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"


def format_uptime(seconds: float) -> str:
    """格式化运行时间"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    
    return "".join(parts) if parts else "刚刚启动"


def get_system_status() -> SystemStatus:
    """获取系统状态"""
    if not HAS_PSUTIL:
        # psutil 不可用时返回默认值
        return SystemStatus(
            cpu=0.0,
            memory=0.0,
            disk=0.0,
            network="N/A",
            uptime="N/A (psutil not installed)"
        )
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取网络IO
        net_io = psutil.net_io_counters()
        # 简化处理，只显示总发送速度
        network_speed = format_bytes(net_io.bytes_sent + net_io.bytes_recv) + "/s"
        
        # 获取启动时间
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        return SystemStatus(
            cpu=round(cpu_percent, 1),
            memory=round(memory.percent, 1),
            disk=round(disk.percent, 1),
            network=network_speed,
            uptime=format_uptime(uptime_seconds)
        )
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return SystemStatus()


@router.get("/", response_model=DashboardResponse, summary="获取仪表盘数据")
async def get_dashboard():
    """
    获取仪表盘汇总数据
    
    包含：
    - 任务统计（运行中、已完成、失败、等待中）
    - 代理统计（活跃代理数、健康率）
    - 账号统计（活跃账号数、总账号数）
    - 系统状态（CPU、内存、磁盘）
    - 各平台统计
    """
    async with get_session() as session:
        # 获取任务统计
        task_stats = await task_crud.get_stats(session)
        
        # 获取代理统计
        proxy_stats = await proxy_crud.get_stats(session)
        
        # 获取账号统计
        account_stats = await account_crud.get_stats(session)
        
        # 构建仪表盘统计
        stats = DashboardStats(
            running_tasks=task_stats["running"],
            completed_tasks=task_stats["completed"],
            failed_tasks=task_stats["failed"],
            pending_tasks=task_stats["pending"],
            total_data="0",  # TODO: 从各平台数据表汇总
            total_data_count=0,
            active_proxies=proxy_stats["online"],
            proxy_health=f"{proxy_stats['avg_success_rate']:.1f}%",
            proxy_health_value=proxy_stats["avg_success_rate"],
            active_accounts=account_stats["active"],
            total_accounts=account_stats["total"]
        )
        
        # 获取系统状态
        system_status = get_system_status()
        
        # 构建各平台统计
        platform_stats = []
        platform_names = {
            "xhs": "小红书",
            "dy": "抖音",
            "bili": "B站",
            "wb": "微博",
            "wechat": "微信公众号",
            "ks": "快手",
            "tieba": "百度贴吧",
            "zhihu": "知乎"
        }
        
        for platform_code, platform_name in platform_names.items():
            task_count = await task_crud.count_tasks(session, platform=platform_code)
            account_count = account_stats["by_platform"].get(platform_code, 0)
            
            if task_count > 0 or account_count > 0:
                platform_stats.append(PlatformStats(
                    platform=platform_code,
                    platform_name=platform_name,
                    task_count=task_count,
                    data_count=0,  # TODO: 从各平台数据表获取
                    account_count=account_count,
                    trend="stable"
                ))
        
        # 最近活动日志（暂时返回空列表）
        recent_activities = []
        
        return DashboardResponse(
            stats=stats,
            system=system_status,
            platform_stats=platform_stats,
            recent_activities=recent_activities
        )


@router.get("/tasks", response_model=TaskStats, summary="获取任务统计")
async def get_task_stats(
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    session_id: Optional[str] = Query(None, description="会话ID筛选")
):
    """
    获取任务统计数据
    """
    async with get_session() as session:
        stats = await task_crud.get_stats(
            session,
            user_id=user_id,
            session_id=session_id
        )
        
        return TaskStats(**stats)


@router.get("/proxies", response_model=ProxyStats, summary="获取代理统计")
async def get_proxy_stats():
    """
    获取代理池统计数据
    """
    async with get_session() as session:
        stats = await proxy_crud.get_stats(session)
        
        return ProxyStats(**stats)


@router.get("/accounts", response_model=AccountStats, summary="获取账号统计")
async def get_account_stats():
    """
    获取账号统计数据
    """
    async with get_session() as session:
        stats = await account_crud.get_stats(session)
        
        return AccountStats(**stats)


@router.get("/system", response_model=SystemStatus, summary="获取系统状态")
async def get_system():
    """
    获取系统运行状态
    
    包含：CPU使用率、内存使用率、磁盘使用率、网络速度、运行时间
    """
    return get_system_status()


@router.get("/platforms", summary="获取各平台统计")
async def get_platform_stats():
    """
    获取各平台的详细统计数据
    """
    async with get_session() as session:
        account_stats = await account_crud.get_stats(session)
        
        platform_names = {
            "xhs": "小红书",
            "dy": "抖音",
            "bili": "B站",
            "wb": "微博",
            "wechat": "微信公众号",
            "ks": "快手",
            "tieba": "百度贴吧",
            "zhihu": "知乎"
        }
        
        items = []
        for platform_code, platform_name in platform_names.items():
            task_count = await task_crud.count_tasks(session, platform=platform_code)
            account_count = account_stats["by_platform"].get(platform_code, 0)
            
            items.append({
                "platform": platform_code,
                "platform_name": platform_name,
                "task_count": task_count,
                "data_count": 0,  # TODO
                "account_count": account_count,
                "active_accounts": account_count if account_count > 0 else 0
            })
        
        return {"items": items}


@router.get("/overview", summary="获取总览数据")
async def get_overview():
    """
    获取简化的总览数据（用于顶部统计卡片）
    """
    async with get_session() as session:
        task_stats = await task_crud.get_stats(session)
        proxy_stats = await proxy_crud.get_stats(session)
        account_stats = await account_crud.get_stats(session)
        
        return {
            "tasks": {
                "total": task_stats["total"],
                "running": task_stats["running"],
                "completed": task_stats["completed"],
                "failed": task_stats["failed"]
            },
            "proxies": {
                "total": proxy_stats["total"],
                "online": proxy_stats["online"],
                "health_rate": round(proxy_stats["avg_success_rate"], 1)
            },
            "accounts": {
                "total": account_stats["total"],
                "active": account_stats["active"]
            }
        }
