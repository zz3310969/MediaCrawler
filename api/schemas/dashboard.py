# -*- coding: utf-8 -*-
"""
仪表盘统计相关数据模型
这些数据通过聚合查询实时计算，不需要落库
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== 仪表盘统计 ==========

class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    # 任务统计
    running_tasks: int = Field(default=0, description="运行中任务数")
    running_tasks_change: int = Field(default=0, description="运行中任务变化(与昨日对比)")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    completed_tasks_change: int = Field(default=0, description="已完成任务变化")
    failed_tasks: int = Field(default=0, description="失败任务数")
    pending_tasks: int = Field(default=0, description="等待中任务数")
    
    # 数据统计
    total_data: str = Field(default="0", description="总数据量(格式化显示)")
    total_data_count: int = Field(default=0, description="总数据量(数值)")
    total_data_change: str = Field(default="0", description="数据变化量")
    
    # 代理统计
    active_proxies: int = Field(default=0, description="活跃代理数")
    proxy_health: str = Field(default="0%", description="代理健康率")
    proxy_health_value: float = Field(default=0.0, description="代理健康率数值")
    
    # 账号统计
    active_accounts: int = Field(default=0, description="活跃账号数")
    total_accounts: int = Field(default=0, description="总账号数")


class SystemStatus(BaseModel):
    """系统状态"""
    cpu: float = Field(default=0.0, description="CPU使用率(%)")
    memory: float = Field(default=0.0, description="内存使用率(%)")
    disk: float = Field(default=0.0, description="磁盘使用率(%)")
    network: str = Field(default="0 B/s", description="网络速度")
    uptime: str = Field(default="0s", description="运行时间")


class PlatformStats(BaseModel):
    """平台统计"""
    platform: str = Field(..., description="平台标识")
    platform_name: str = Field(..., description="平台名称")
    task_count: int = Field(default=0, description="任务数")
    data_count: int = Field(default=0, description="数据量")
    account_count: int = Field(default=0, description="账号数")
    trend: str = Field(default="stable", description="趋势: up/down/stable")


# ========== 任务统计 ==========

class TaskStats(BaseModel):
    """任务统计"""
    pending: int = Field(default=0, description="等待中")
    running: int = Field(default=0, description="运行中")
    completed: int = Field(default=0, description="已完成")
    failed: int = Field(default=0, description="已失败")
    cancelled: int = Field(default=0, description="已取消")
    total: int = Field(default=0, description="总数")


class TaskTrend(BaseModel):
    """任务趋势(每日统计)"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    created: int = Field(default=0, description="创建数")
    completed: int = Field(default=0, description="完成数")
    failed: int = Field(default=0, description="失败数")


# ========== 代理统计 ==========

class ProxyStats(BaseModel):
    """代理池统计"""
    total: int = Field(default=0, description="总数")
    online: int = Field(default=0, description="在线数")
    offline: int = Field(default=0, description="离线数")
    testing: int = Field(default=0, description="测试中")
    avg_response_time: float = Field(default=0.0, description="平均响应时间(ms)")
    avg_quality_score: float = Field(default=0.0, description="平均质量评分")
    avg_success_rate: float = Field(default=0.0, description="平均成功率(%)")
    
    # 周环比变化
    weekly_change: Optional[Dict[str, Any]] = Field(default=None, description="周环比变化")


class ProxyQualityMetrics(BaseModel):
    """代理质量指标(聚合计算)"""
    proxy_id: str = Field(..., description="代理ID")
    total_requests: int = Field(default=0, description="总请求数")
    success_requests: int = Field(default=0, description="成功请求数")
    failed_requests: int = Field(default=0, description="失败请求数")
    success_rate: float = Field(default=0.0, description="成功率(%)")
    avg_response_time: float = Field(default=0.0, description="平均响应时间(ms)")
    quality_score: float = Field(default=50.0, description="质量评分")
    consecutive_failures: int = Field(default=0, description="连续失败次数")
    last_success_at: Optional[int] = Field(default=None, description="最后成功时间戳")
    last_failure_at: Optional[int] = Field(default=None, description="最后失败时间戳")


# ========== 账号统计 ==========

class AccountStats(BaseModel):
    """账号统计"""
    total: int = Field(default=0, description="总数")
    active: int = Field(default=0, description="正常")
    inactive: int = Field(default=0, description="停用")
    pending: int = Field(default=0, description="待验证")
    expired: int = Field(default=0, description="已过期")
    by_platform: Dict[str, int] = Field(default_factory=dict, description="各平台数量")


# ========== 数据统计 ==========

class DataStats(BaseModel):
    """爬取数据统计"""
    total: int = Field(default=0, description="总数据量")
    by_platform: Dict[str, int] = Field(default_factory=dict, description="各平台数据量")
    today_count: int = Field(default=0, description="今日新增")
    week_count: int = Field(default=0, description="本周新增")


class DataTrend(BaseModel):
    """数据趋势(每日统计)"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    count: int = Field(default=0, description="数据量")
    platform: Optional[str] = Field(default=None, description="平台(可选)")


# ========== 活动日志 ==========

class ActivityLog(BaseModel):
    """活动日志"""
    log_id: str = Field(..., description="日志ID")
    action: str = Field(..., description="操作类型")
    description: str = Field(..., description="操作描述")
    user_id: Optional[str] = Field(default=None, description="操作用户ID")
    username: Optional[str] = Field(default=None, description="操作用户名")
    target_type: Optional[str] = Field(default=None, description="目标类型")
    target_id: Optional[str] = Field(default=None, description="目标ID")
    created_at: int = Field(..., description="创建时间戳")


# ========== 仪表盘响应 ==========

class DashboardResponse(BaseModel):
    """仪表盘数据响应"""
    stats: DashboardStats = Field(..., description="统计数据")
    system: SystemStatus = Field(..., description="系统状态")
    platform_stats: List[PlatformStats] = Field(default_factory=list, description="各平台统计")
    recent_activities: List[ActivityLog] = Field(default_factory=list, description="最近活动")


class TaskStatsResponse(BaseModel):
    """任务统计响应"""
    success: bool = True
    data: TaskStats


class ProxyStatsResponse(BaseModel):
    """代理统计响应"""
    success: bool = True
    data: ProxyStats


class DataStatsResponse(BaseModel):
    """数据统计响应"""
    success: bool = True
    data: DataStats


class TrendResponse(BaseModel):
    """趋势数据响应"""
    success: bool = True
    data: List[Dict[str, Any]] = Field(default_factory=list, description="趋势数据")


# ========== 通用统计查询参数 ==========

class StatsQueryParams(BaseModel):
    """统计查询参数"""
    start_date: Optional[str] = Field(default=None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="结束日期 YYYY-MM-DD")
    platform: Optional[str] = Field(default=None, description="平台筛选")
    granularity: str = Field(default="day", description="粒度: day/week/month")
