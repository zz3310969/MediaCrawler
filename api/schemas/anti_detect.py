"""
反爬增强相关数据模型
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class AntiDetectConfig(BaseModel):
    """反爬增强配置"""
    # 功能开关
    enable_fingerprint: bool = True              # 启用浏览器指纹
    enable_rate_limit: bool = True               # 启用智能限速
    enable_human_behavior: bool = True           # 启用人类行为模拟
    enable_account_health: bool = True           # 启用账号健康管理
    enable_binding: bool = True                  # 启用账号-代理-指纹绑定

    # 指纹配置
    fingerprint_platform_hint: Optional[str] = None  # 平台提示: mac/windows/linux

    # 限速配置
    rate_limit_min_interval: float = 3.0         # 最小请求间隔（秒）
    rate_limit_max_interval: float = 10.0        # 最大请求间隔（秒）
    rate_limit_hourly_limit: int = 150           # 每小时最大请求数
    rate_limit_daily_limit: int = 1500           # 每天最大请求数

    # 账号健康配置
    account_cooling_threshold: float = 70.0      # 冷却阈值（风险评分）
    account_warning_threshold: float = 50.0      # 警告阈值（风险评分）


class AccountHealthStatus(BaseModel):
    """账号健康状态"""
    account_id: str
    platform: str
    total_requests: int = 0
    failed_requests: int = 0
    captcha_count: int = 0
    risk_score: float = 0.0
    status: str = "active"  # active/cooling/warning/banned
    last_request_at: Optional[datetime] = None
    cooling_until: Optional[datetime] = None
    bound_proxy_id: Optional[str] = None
    bound_fingerprint_id: Optional[str] = None


class BindingInfo(BaseModel):
    """绑定信息"""
    account_id: str
    platform: str
    proxy_id: Optional[str] = None
    fingerprint_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AntiDetectStats(BaseModel):
    """反爬增强统计"""
    platform: str

    # 账号健康统计
    total_accounts: int = 0
    active_accounts: int = 0
    cooling_accounts: int = 0
    warning_accounts: int = 0
    banned_accounts: int = 0
    avg_risk_score: float = 0.0

    # 绑定统计
    total_bindings: int = 0
    with_proxy: int = 0
    with_fingerprint: int = 0
    complete_bindings: int = 0

    # 限速统计
    total_requests: int = 0
    hourly_requests: int = 0
    daily_requests: int = 0
    hourly_limit: int = 0
    daily_limit: int = 0


class AccountHealthListResponse(BaseModel):
    """账号健康列表响应"""
    accounts: List[AccountHealthStatus]
    total: int
    page: int
    page_size: int


class BindingListResponse(BaseModel):
    """绑定列表响应"""
    bindings: List[BindingInfo]
    total: int
    page: int
    page_size: int
