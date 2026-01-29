# -*- coding: utf-8 -*-
# @Desc    : 代理管理API路由

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from ..schemas.proxy import (
    ProxyInfo,
    ProxyImportRequest,
    ProxyImportResponse,
    ProxyListResponse,
    ProxyDeleteRequest,
    ProxyStatusUpdateRequest,
    ProxyWithQuality,
    BindingInfo,
    BindingCreateRequest,
    BindingListResponse,
    BatchBindRequest,
    BatchUnbindRequest,
    QualityMetrics,
    StatisticsResponse,
    OverviewStats,
    DailyStats,
    PlatformStats,
    ProxySettings,
    GlobalSettings,
    QualitySettings,
    FailoverSettings,
    SourceConfig,
    SourcesConfig,
    SuccessResponse,
    ErrorResponse,
)

from proxy.proxy_manager import ProxyManager, get_proxy_manager
from proxy.types import IpInfoModel, PersistedProxy

router = APIRouter(prefix="/proxy", tags=["代理管理"])


# ==================== 依赖 ====================

async def get_manager() -> ProxyManager:
    """获取代理管理器实例"""
    return await get_proxy_manager()


# ==================== 设置（需要在 /{proxy_id} 之前定义） ====================

@router.get("/settings", response_model=ProxySettings)
async def get_settings(
    manager: ProxyManager = Depends(get_manager),
):
    """获取代理设置"""
    config = manager.config
    
    return ProxySettings(
        global_settings=GlobalSettings(
            enable_proxy=config.global_settings.enable_proxy,
            proxy_pool_size=config.global_settings.proxy_pool_size,
            validate_on_get=config.global_settings.validate_on_get,
            validate_timeout=config.global_settings.validate_timeout,
            enable_binding=config.global_settings.enable_binding,
            binding_sticky=config.global_settings.binding_sticky,
            auto_rebind=config.global_settings.auto_rebind,
            max_bindings_per_proxy=config.global_settings.max_bindings_per_proxy,
            prefer_similar_region=config.global_settings.prefer_similar_region,
        ),
        quality=QualitySettings(
            enabled=config.quality.enabled,
            sample_window=config.quality.sample_window,
            time_window_hours=config.quality.time_window_hours,
            min_quality_score=config.quality.min_quality_score,
            min_requests_for_retire=config.quality.min_requests_for_retire,
            max_consecutive_failures=config.quality.max_consecutive_failures,
            auto_retire_enabled=config.quality.auto_retire_enabled,
            check_interval_seconds=config.quality.check_interval_seconds,
        ),
        failover=FailoverSettings(
            enabled=config.failover.enabled,
            strategy=config.failover.strategy,
            max_retries=config.failover.max_retries,
            retry_delay_seconds=config.failover.retry_delay_seconds,
            cb_failure_threshold=config.failover.cb_failure_threshold,
            cb_recovery_timeout=config.failover.cb_recovery_timeout,
        ),
    )


@router.get("/sources", response_model=SourcesConfig)
async def get_sources(
    manager: ProxyManager = Depends(get_manager),
):
    """获取代理源配置"""
    sources = []
    for source in manager.config.sources:
        sources.append(SourceConfig(
            name=source.name,
            enabled=source.enabled,
            priority=source.priority,
            api_url=source.api_url,
            file_path=source.file_path,
            auto_reload=source.auto_reload,
            default_protocol=source.default_protocol,
        ))
    
    return SourcesConfig(sources=sources)


# ==================== 代理管理 ====================

@router.get("/list", response_model=ProxyListResponse)
async def list_proxies(
    source: Optional[str] = None,
    protocol: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    manager: ProxyManager = Depends(get_manager),
):
    """获取代理列表"""
    proxies = await manager.get_all_proxies(
        source=source,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    
    # 筛选协议
    if protocol:
        proxies = [p for p in proxies if p.protocol == protocol]
    
    items = [_proxy_to_info(p) for p in proxies]
    
    # 获取总数
    total = await manager._proxy_store.count_proxies(source=source, is_active=is_active)
    
    return ProxyListResponse(total=total, items=items)


@router.get("/{proxy_id}", response_model=ProxyWithQuality)
async def get_proxy(
    proxy_id: str,
    manager: ProxyManager = Depends(get_manager),
):
    """获取代理详情（含质量信息）"""
    proxy = await manager._proxy_store.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    info = _proxy_to_info(proxy)
    
    # 获取质量信息
    quality_data = await manager.get_proxy_quality(proxy_id)
    if quality_data:
        info_dict = info.model_dump()
        info_dict["quality"] = QualityMetrics(**quality_data)
        return ProxyWithQuality(**info_dict)
    
    return ProxyWithQuality(**info.model_dump())


@router.post("/import", response_model=ProxyImportResponse)
async def import_proxies(
    request: ProxyImportRequest,
    manager: ProxyManager = Depends(get_manager),
):
    """批量导入代理"""
    try:
        proxies = [
            IpInfoModel(
                ip=p.ip,
                port=p.port,
                protocol=p.protocol,
                user=p.username or "",
                password=p.password or "",
                country=p.country or "CN",
                province=p.province,
                city=p.city,
            )
            for p in request.proxies
        ]
        
        imported = await manager.import_proxies(proxies, source=request.source)
        
        return ProxyImportResponse(
            success=True,
            imported_count=imported,
            failed_count=len(request.proxies) - imported,
            message=f"成功导入 {imported} 个代理",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{proxy_id}", response_model=SuccessResponse)
async def delete_proxy(
    proxy_id: str,
    manager: ProxyManager = Depends(get_manager),
):
    """删除代理"""
    success = await manager.delete_proxy(proxy_id)
    if not success:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    return SuccessResponse(message="代理已删除")


@router.post("/batch-delete", response_model=SuccessResponse)
async def batch_delete_proxies(
    request: ProxyDeleteRequest,
    manager: ProxyManager = Depends(get_manager),
):
    """批量删除代理"""
    deleted = 0
    for proxy_id in request.proxy_ids:
        if await manager.delete_proxy(proxy_id):
            deleted += 1
    
    return SuccessResponse(message=f"成功删除 {deleted} 个代理")


@router.patch("/{proxy_id}/status", response_model=SuccessResponse)
async def update_proxy_status(
    proxy_id: str,
    request: ProxyStatusUpdateRequest,
    manager: ProxyManager = Depends(get_manager),
):
    """更新代理状态"""
    success = await manager.update_proxy_status(proxy_id, request.is_active)
    if not success:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    status = "启用" if request.is_active else "禁用"
    return SuccessResponse(message=f"代理已{status}")


# ==================== 绑定管理 ====================

@router.get("/bindings/list", response_model=BindingListResponse)
async def list_bindings(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    manager: ProxyManager = Depends(get_manager),
):
    """获取绑定列表"""
    if not manager.binding_manager:
        raise HTTPException(status_code=400, detail="绑定功能未启用")
    
    bindings = await manager.get_all_bindings(
        platform=platform,
        limit=limit,
        offset=offset,
    )
    
    # 筛选状态
    if status:
        bindings = [b for b in bindings if b.status == status]
    
    items = []
    for b in bindings:
        # 获取代理信息
        proxy = await manager._proxy_store.get_proxy(b.proxy_id)
        items.append(BindingInfo(
            binding_id=b.binding_id,
            account_id=b.account_id,
            platform=b.platform,
            proxy_id=b.proxy_id,
            proxy_ip=proxy.ip if proxy else None,
            proxy_port=proxy.port if proxy else None,
            is_sticky=b.is_sticky,
            status=b.status,
            bound_at=b.bound_at,
            last_used_at=b.last_used_at,
            rebind_count=b.rebind_count,
        ))
    
    total = await manager._binding_store.count_bindings(platform=platform)
    
    return BindingListResponse(total=total, items=items)


@router.post("/bindings/bind", response_model=SuccessResponse)
async def create_binding(
    request: BindingCreateRequest,
    manager: ProxyManager = Depends(get_manager),
):
    """创建绑定"""
    if not manager.binding_manager:
        raise HTTPException(status_code=400, detail="绑定功能未启用")
    
    success = await manager.bind_proxy(
        account_id=request.account_id,
        platform=request.platform,
        proxy_id=request.proxy_id,
        is_sticky=request.is_sticky,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="绑定失败")
    
    return SuccessResponse(message="绑定成功")


@router.delete("/bindings/{account_id}/{platform}", response_model=SuccessResponse)
async def delete_binding(
    account_id: str,
    platform: str,
    manager: ProxyManager = Depends(get_manager),
):
    """解除绑定"""
    if not manager.binding_manager:
        raise HTTPException(status_code=400, detail="绑定功能未启用")
    
    success = await manager.unbind_proxy(account_id, platform)
    if not success:
        raise HTTPException(status_code=404, detail="绑定不存在")
    
    return SuccessResponse(message="已解除绑定")


@router.post("/bindings/batch-bind", response_model=SuccessResponse)
async def batch_bind(
    request: BatchBindRequest,
    manager: ProxyManager = Depends(get_manager),
):
    """批量绑定"""
    if not manager.binding_manager:
        raise HTTPException(status_code=400, detail="绑定功能未启用")
    
    success_count = 0
    for b in request.bindings:
        if await manager.bind_proxy(
            account_id=b.account_id,
            platform=b.platform,
            proxy_id=b.proxy_id,
            is_sticky=b.is_sticky,
        ):
            success_count += 1
    
    return SuccessResponse(message=f"成功绑定 {success_count}/{len(request.bindings)} 个")


@router.post("/bindings/batch-unbind", response_model=SuccessResponse)
async def batch_unbind(
    request: BatchUnbindRequest,
    manager: ProxyManager = Depends(get_manager),
):
    """批量解绑"""
    if not manager.binding_manager:
        raise HTTPException(status_code=400, detail="绑定功能未启用")
    
    success_count = 0
    for account_id in request.account_ids:
        if await manager.unbind_proxy(account_id, request.platform):
            success_count += 1
    
    return SuccessResponse(message=f"成功解绑 {success_count}/{len(request.account_ids)} 个")


# ==================== 统计 ====================

@router.get("/statistics/overview", response_model=OverviewStats)
async def get_overview_stats(
    manager: ProxyManager = Depends(get_manager),
):
    """获取总览统计"""
    # 代理统计
    total_proxies = await manager._proxy_store.count_proxies()
    active_proxies = await manager._proxy_store.count_proxies(is_active=True)
    
    # 绑定统计
    total_bindings = 0
    active_bindings = 0
    if manager._binding_store:
        total_bindings = await manager._binding_store.count_bindings()
        active_bindings = await manager._binding_store.count_bindings(status="active")
    
    # 今日请求统计
    today_requests = 0
    today_success_rate = 0.0
    if manager._stats_collector:
        all_stats = manager._stats_collector.get_all_realtime_stats()
        for stats in all_stats:
            today_requests += stats.get("total_requests", 0)
        
        total_success = sum(s.get("success_requests", 0) for s in all_stats)
        if today_requests > 0:
            today_success_rate = total_success / today_requests
    
    # 平均质量分
    avg_quality = 50.0
    if manager.quality_evaluator:
        all_metrics = await manager.quality_evaluator.get_all_metrics()
        if all_metrics:
            avg_quality = sum(m.quality_score for m in all_metrics) / len(all_metrics)
    
    return OverviewStats(
        total_proxies=total_proxies,
        active_proxies=active_proxies,
        total_bindings=total_bindings,
        active_bindings=active_bindings,
        today_requests=today_requests,
        today_success_rate=today_success_rate,
        avg_quality_score=avg_quality,
    )


@router.get("/statistics/proxy/{proxy_id}", response_model=QualityMetrics)
async def get_proxy_stats(
    proxy_id: str,
    manager: ProxyManager = Depends(get_manager),
):
    """获取代理统计"""
    quality = await manager.get_proxy_quality(proxy_id)
    if not quality:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    return QualityMetrics(**quality)


# ==================== 工具函数 ====================

def _proxy_to_info(proxy: PersistedProxy) -> ProxyInfo:
    """转换代理为API模型"""
    return ProxyInfo(
        proxy_id=proxy.proxy_id,
        ip=proxy.ip,
        port=proxy.port,
        protocol=proxy.protocol,
        username=proxy.username,
        source=proxy.source,
        country=proxy.country,
        province=proxy.province,
        city=proxy.city,
        isp=proxy.isp,
        is_active=proxy.is_active,
        created_at=proxy.created_at,
        updated_at=proxy.updated_at,
        expired_at=proxy.expired_at,
    )

