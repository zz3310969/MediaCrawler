# -*- coding: utf-8 -*-
# @Desc    : 代理相关API数据模型

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 代理模型 ====================

class ProxyInfo(BaseModel):
    """代理信息"""
    proxy_id: str
    ip: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    source: str = "manual"
    country: str = "CN"
    province: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    status: str = "testing"                     # online/offline/testing
    is_active: bool = True
    quality_score: float = 50.0
    response_time: int = 0                      # 响应时间(ms)
    # 质量指标（直接集成，无需单独表）
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_success_at: Optional[int] = None       # 时间戳
    last_failure_at: Optional[int] = None       # 时间戳
    last_checked_at: Optional[int] = None       # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_requests == 0:
            return 0.0
        return round(self.success_requests / self.total_requests * 100, 2)


class ProxyImportItem(BaseModel):
    """代理导入项"""
    ip: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None


class ProxyImportRequest(BaseModel):
    """代理导入请求"""
    proxies: List[ProxyImportItem]
    source: str = "manual"


class ProxyImportResponse(BaseModel):
    """代理导入响应"""
    success: bool
    imported_count: int
    failed_count: int = 0
    message: str = ""


class ProxyListResponse(BaseModel):
    """代理列表响应"""
    total: int
    items: List[ProxyInfo]


class ProxyListRequest(BaseModel):
    """代理列表查询"""
    status: Optional[str] = None               # online/offline/testing
    is_active: Optional[bool] = None
    source: Optional[str] = None               # manual/api/file
    country: Optional[str] = None
    min_quality_score: Optional[float] = None
    keyword: Optional[str] = None              # 搜索IP
    page: int = 1
    page_size: int = 20


class ProxyDeleteRequest(BaseModel):
    """代理删除请求"""
    proxy_ids: List[str]


class ProxyStatusUpdateRequest(BaseModel):
    """代理状态更新请求"""
    is_active: bool


# ==================== 绑定模型 ====================

class BindingInfo(BaseModel):
    """绑定信息"""
    binding_id: str
    account_id: str
    platform: str
    proxy_id: str
    proxy_ip: Optional[str] = None
    proxy_port: Optional[int] = None
    is_sticky: bool = True
    status: str = "active"
    bound_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    rebind_count: int = 0


class BindingCreateRequest(BaseModel):
    """绑定创建请求"""
    account_id: str
    platform: str
    proxy_id: str
    is_sticky: bool = True
    allow_auto_rebind: bool = True


class BindingListResponse(BaseModel):
    """绑定列表响应"""
    total: int
    items: List[BindingInfo]


class BatchBindRequest(BaseModel):
    """批量绑定请求"""
    bindings: List[BindingCreateRequest]


class BatchUnbindRequest(BaseModel):
    """批量解绑请求"""
    account_ids: List[str]
    platform: str


# ==================== 质量指标模型 ====================

class QualityMetrics(BaseModel):
    """质量指标"""
    proxy_id: str
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    p95_response_time: Optional[float] = None
    consecutive_failures: int = 0
    quality_score: float = 50.0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None


class ProxyWithQuality(ProxyInfo):
    """带质量信息的代理"""
    quality: Optional[QualityMetrics] = None


# ==================== 统计模型 ====================

class DailyStats(BaseModel):
    """每日统计"""
    date: str
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0


class ProxyStats(BaseModel):
    """代理统计"""
    proxy_id: str
    today: DailyStats
    week_total: int = 0
    month_total: int = 0


class OverviewStats(BaseModel):
    """总览统计"""
    total_proxies: int = 0
    active_proxies: int = 0
    total_bindings: int = 0
    active_bindings: int = 0
    today_requests: int = 0
    today_success_rate: float = 0.0
    avg_quality_score: float = 0.0


class PlatformStats(BaseModel):
    """平台统计"""
    platform: str
    total_requests: int = 0
    success_requests: int = 0
    success_rate: float = 0.0
    unique_proxies: int = 0
    unique_accounts: int = 0


class StatisticsResponse(BaseModel):
    """统计响应"""
    overview: OverviewStats
    daily_stats: List[DailyStats] = []
    platform_stats: List[PlatformStats] = []


# ==================== 配置模型 ====================

class GlobalSettings(BaseModel):
    """全局设置"""
    enable_proxy: bool = True
    proxy_pool_size: int = 5
    validate_on_get: bool = True
    validate_timeout: int = 10
    enable_binding: bool = True
    binding_sticky: bool = True
    auto_rebind: bool = True
    max_bindings_per_proxy: int = 5
    prefer_similar_region: bool = True


class QualitySettings(BaseModel):
    """质量设置"""
    enabled: bool = True
    sample_window: int = 100
    time_window_hours: int = 24
    min_quality_score: float = 30
    min_requests_for_retire: int = 20
    max_consecutive_failures: int = 10
    auto_retire_enabled: bool = True
    check_interval_seconds: int = 300


class FailoverSettings(BaseModel):
    """故障转移设置"""
    enabled: bool = True
    strategy: str = "circuit_breaker"
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    cb_failure_threshold: int = 5
    cb_recovery_timeout: int = 60


class ProxySettings(BaseModel):
    """代理设置"""
    global_settings: GlobalSettings = Field(default_factory=GlobalSettings)
    quality: QualitySettings = Field(default_factory=QualitySettings)
    failover: FailoverSettings = Field(default_factory=FailoverSettings)


class SourceConfig(BaseModel):
    """代理源配置"""
    name: str
    enabled: bool = False
    priority: int = 1
    # 通用
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    # 本地文件
    file_path: Optional[str] = None
    auto_reload: bool = True
    default_protocol: str = "http"


class CustomApiSourceConfig(SourceConfig):
    """自定义API源配置"""
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    response_type: str = "json"
    data_path: str = ""
    field_mapping: Dict[str, str] = Field(default_factory=dict)


class SourcesConfig(BaseModel):
    """代理源配置"""
    sources: List[SourceConfig] = []


# ==================== 通用响应 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None

