"""
任务相关数据模型
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"      # 执行完成
    FAILED = "failed"            # 执行失败
    CANCELLED = "cancelled"      # 已取消


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


class TaskConfig(BaseModel):
    """任务配置"""
    # 基本配置
    platform: str                                       # xhs/dy/bili/wb/wechat/ks/tieba/zhihu
    crawler_type: str = "search"                        # search/creator/detail/creator_vip/album
    
    # 搜索配置
    keywords: Optional[List[str]] = None                # 搜索关键词列表
    
    # 创作者配置
    creator_ids: Optional[List[str]] = None             # 创作者 ID 或 URL 列表
    
    # 详情配置
    note_urls: Optional[List[str]] = None               # 笔记/视频 URL 列表
    
    # 爬取数量配置
    max_notes: int = 100                                # 最大爬取笔记数
    enable_comments: bool = False                       # 是否爬取评论
    max_comments_per_note: int = 20                     # 每个笔记最大评论数
    enable_media: bool = False                          # 是否下载图片/视频
    
    # 执行配置
    concurrency: int = 3                                # 并发数
    crawl_interval: float = 1.0                         # 请求间隔（秒）
    
    # 登录配置
    login_type: Optional[str] = "cookie"                # cookie/qrcode
    cookies: Optional[str] = None                       # Cookie 字符串
    
    # 存储配置
    save_option: str = "json"                           # json/csv/excel/db/sqlite
    
    # 可扩展字段
    extra: Dict[str, Any] = Field(default_factory=dict)


class TaskProgress(BaseModel):
    """任务进度"""
    current: int = 0
    total: int = 0
    percentage: int = 0
    items_crawled: int = 0
    comments_crawled: int = 0


class TaskResult(BaseModel):
    """任务结果"""
    success: bool = False
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    statistics: Dict[str, Any] = Field(default_factory=dict)


class TaskMetadata(BaseModel):
    """任务元数据"""
    sign_server_used: bool = False
    execution_node: Optional[str] = None       # 分布式时的执行节点
    resource_usage: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """任务实体"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    task_name: Optional[str] = None
    
    # 状态
    status: TaskStatus = TaskStatus.PENDING
    priority: int = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    idempotency_key: Optional[str] = None      # 幂等键
    cancel_requested: bool = False             # 取消标记
    
    # 时间
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    
    # 详情
    config: TaskConfig
    progress: TaskProgress = Field(default_factory=TaskProgress)
    result: TaskResult = Field(default_factory=TaskResult)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    
    # 版本号（用于乐观锁）
    version: int = 0
    
    class Config:
        use_enum_values = True


class TaskLease(BaseModel):
    """任务租约（用于 reserve/ack/nack）"""
    lease_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    worker_id: str
    acquired_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def create(cls, task_id: str, worker_id: str, lease_seconds: int = 300) -> "TaskLease":
        """创建租约"""
        now = datetime.utcnow()
        return cls(
            task_id=task_id,
            worker_id=worker_id,
            acquired_at=now,
            expires_at=now + timedelta(seconds=lease_seconds)
        )


# ========== 请求/响应模型 ==========

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    task_name: Optional[str] = None
    config: TaskConfig
    priority: int = TaskPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class TaskListRequest(BaseModel):
    """任务列表查询"""
    status: Optional[TaskStatus] = None
    platform: Optional[str] = None
    page: int = 1
    page_size: int = 20


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[Task]
    total: int
    page: int
    page_size: int


class TaskStatsResponse(BaseModel):
    """任务统计响应"""
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0

