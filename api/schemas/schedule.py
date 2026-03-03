"""
定时调度相关数据模型
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class TriggerType(str, Enum):
    """触发类型"""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"


class ScheduleStatus(str, Enum):
    """调度状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    FINISHED = "finished"


class ScheduleConfig(BaseModel):
    """调度中嵌入的任务配置（复用 TaskConfig 结构）"""
    platform: str
    crawler_type: str = "search"
    keywords: Optional[List[str]] = None
    creator_ids: Optional[List[str]] = None
    note_urls: Optional[List[str]] = None
    max_notes: int = 100
    enable_comments: bool = False
    max_comments_per_note: int = 20
    enable_media: bool = False
    concurrency: int = 3
    crawl_interval: float = 1.0
    account_id: Optional[str] = None
    login_type: Optional[str] = "cookie"
    cookies: Optional[str] = None
    save_option: str = "json"
    enable_anti_detect: bool = False
    anti_detect_config: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class Schedule(BaseModel):
    """调度实体"""
    schedule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schedule_name: str
    platform: str
    crawler_type: str = "search"
    task_config: ScheduleConfig

    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    timezone: str = "Asia/Shanghai"

    enabled: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    total_runs: int = 0

    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    created_by: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ========== 请求/响应模型 ==========

class ScheduleCreateRequest(BaseModel):
    """创建调度请求"""
    schedule_name: str = Field(..., min_length=1, max_length=200)
    task_config: ScheduleConfig

    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = Field(default=None, ge=60)
    timezone: str = "Asia/Shanghai"

    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None


class ScheduleUpdateRequest(BaseModel):
    """更新调度请求"""
    schedule_name: Optional[str] = Field(default=None, max_length=200)
    task_config: Optional[ScheduleConfig] = None

    trigger_type: Optional[TriggerType] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = Field(default=None, ge=60)
    timezone: Optional[str] = None

    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None


class ScheduleResponse(BaseModel):
    """调度详情响应"""
    schedule_id: str
    schedule_name: str
    platform: str
    crawler_type: str
    task_config: ScheduleConfig

    trigger_type: str
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    timezone: str

    enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    total_runs: int

    webhook_url: Optional[str]

    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]


class ScheduleListResponse(BaseModel):
    """调度列表响应"""
    schedules: List[ScheduleResponse]
    total: int
