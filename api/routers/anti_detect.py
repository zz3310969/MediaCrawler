"""
反爬增强管理路由
"""
import logging
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends

from api.schemas.anti_detect import (
    AntiDetectConfig,
    AntiDetectStats,
    AccountHealthStatus,
    AccountHealthListResponse,
    BindingInfo,
    BindingListResponse,
)
from api.middleware.session import require_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/anti-detect", tags=["anti-detect"])


def get_anti_detect_manager():
    """获取反爬增强管理器（延迟导入）"""
    try:
        from anti_detect import AntiDetectBindingManager
        return AntiDetectBindingManager()
    except ImportError:
        raise HTTPException(status_code=500, detail="Anti-detect module not available")


def get_health_manager():
    """获取账号健康管理器"""
    try:
        from anti_detect import AccountHealthManager
        return AccountHealthManager()
    except ImportError:
        raise HTTPException(status_code=500, detail="Anti-detect module not available")


@router.get("/stats/{platform}", response_model=AntiDetectStats)
async def get_stats(
    platform: str,
    session_id: str = Depends(require_session_id)
):
    """获取反爬增强统计信息"""
    try:
        binding_manager = get_anti_detect_manager()
        health_manager = get_health_manager()

        # 获取绑定统计
        binding_stats = binding_manager.get_stats(platform)

        # 获取账号健康统计
        health_stats = health_manager.get_stats(platform)

        # 获取限速统计（如果有的话）
        rate_limit_stats = {
            "total_requests": 0,
            "hourly_requests": 0,
            "daily_requests": 0,
            "hourly_limit": 150,
            "daily_limit": 1500,
        }

        return AntiDetectStats(
            platform=platform,
            # 账号健康统计
            total_accounts=health_stats.get("total_accounts", 0),
            active_accounts=health_stats.get("active_accounts", 0),
            cooling_accounts=health_stats.get("cooling_accounts", 0),
            warning_accounts=health_stats.get("warning_accounts", 0),
            banned_accounts=health_stats.get("banned_accounts", 0),
            avg_risk_score=health_stats.get("avg_risk_score", 0.0),
            # 绑定统计
            total_bindings=binding_stats.get("total_bindings", 0),
            with_proxy=binding_stats.get("with_proxy", 0),
            with_fingerprint=binding_stats.get("with_fingerprint", 0),
            complete_bindings=binding_stats.get("complete_bindings", 0),
            # 限速统计
            **rate_limit_stats
        )
    except Exception as e:
        logger.error(f"Failed to get anti-detect stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{platform}", response_model=AccountHealthListResponse)
async def list_account_health(
    platform: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: str = Depends(require_session_id)
):
    """获取账号健康列表"""
    try:
        health_manager = get_health_manager()

        # 获取所有账号
        all_accounts = health_manager.list_accounts(platform)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        accounts = all_accounts[start:end]

        # 转换为响应格式
        account_list = []
        for account in accounts:
            account_list.append(AccountHealthStatus(
                account_id=account.account_id,
                platform=account.platform,
                total_requests=account.total_requests,
                failed_requests=account.failed_requests,
                captcha_count=account.captcha_count,
                risk_score=account.risk_score,
                status=account.status,
                last_request_at=account.last_request_at,
                cooling_until=account.cooling_until,
                bound_proxy_id=account.bound_proxy_id,
                bound_fingerprint_id=account.bound_fingerprint_id,
            ))

        return AccountHealthListResponse(
            accounts=account_list,
            total=len(all_accounts),
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Failed to list account health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bindings/{platform}", response_model=BindingListResponse)
async def list_bindings(
    platform: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: str = Depends(require_session_id)
):
    """获取绑定列表"""
    try:
        binding_manager = get_anti_detect_manager()

        # 获取所有绑定
        all_bindings = binding_manager.list_bindings(platform)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        bindings = all_bindings[start:end]

        # 转换为响应格式
        binding_list = []
        for binding in bindings:
            binding_list.append(BindingInfo(
                account_id=binding.account_id,
                platform=binding.platform,
                proxy_id=binding.proxy_id,
                fingerprint_id=binding.fingerprint_id,
                created_at=binding.created_at,
                updated_at=binding.updated_at,
            ))

        return BindingListResponse(
            bindings=binding_list,
            total=len(all_bindings),
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Failed to list bindings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bindings/{platform}/{account_id}/proxy")
async def bind_proxy(
    platform: str,
    account_id: str,
    proxy_id: str,
    session_id: str = Depends(require_session_id)
):
    """绑定代理"""
    try:
        binding_manager = get_anti_detect_manager()
        binding_manager.bind_proxy(account_id, platform, proxy_id)
        return {"success": True, "message": "Proxy bound successfully"}
    except Exception as e:
        logger.error(f"Failed to bind proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bindings/{platform}/{account_id}")
async def delete_binding(
    platform: str,
    account_id: str,
    session_id: str = Depends(require_session_id)
):
    """删除绑定"""
    try:
        binding_manager = get_anti_detect_manager()
        binding_manager.remove_binding(account_id, platform)
        return {"success": True, "message": "Binding deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete binding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/default", response_model=AntiDetectConfig)
async def get_default_config(
    platform: Optional[str] = None,
    session_id: str = Depends(require_session_id)
):
    """获取默认配置"""
    try:
        from anti_detect.config import get_platform_config

        if platform:
            config = get_platform_config(platform)
            return AntiDetectConfig(
                enable_fingerprint=True,
                enable_rate_limit=True,
                enable_human_behavior=True,
                enable_account_health=True,
                enable_binding=True,
                rate_limit_min_interval=config.rate_limit_min_interval,
                rate_limit_max_interval=config.rate_limit_max_interval,
                rate_limit_hourly_limit=config.rate_limit_hourly_limit,
                rate_limit_daily_limit=config.rate_limit_daily_limit,
            )
        else:
            return AntiDetectConfig()
    except Exception as e:
        logger.error(f"Failed to get default config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
