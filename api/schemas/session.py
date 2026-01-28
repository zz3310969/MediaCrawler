"""
会话相关数据模型
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import secrets


class SessionQuota(BaseModel):
    """用户配额"""
    max_concurrent_tasks: int = 3
    max_daily_tasks: int = 100
    used_daily_tasks: int = 0
    quota_reset_at: datetime = Field(default_factory=datetime.utcnow)
    
    def can_create_task(self) -> bool:
        """检查是否可以创建新任务"""
        # 检查是否需要重置每日配额
        now = datetime.utcnow()
        if now.date() > self.quota_reset_at.date():
            return True  # 新的一天，配额会被重置
        return self.used_daily_tasks < self.max_daily_tasks


class SessionPreferences(BaseModel):
    """用户偏好"""
    default_platform: str = "xhs"
    default_save_option: str = "csv"
    # cookie 引用（实际 cookie 存储在 storage 中）
    cookie_refs: Dict[str, str] = Field(default_factory=dict)


class Session(BaseModel):
    """会话实体"""
    session_id: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    user_id: Optional[str] = None              # 可选，匿名时为空
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    preferences: SessionPreferences = Field(default_factory=SessionPreferences)
    quota: SessionQuota = Field(default_factory=SessionQuota)
    
    # 安全相关
    user_agent_hash: Optional[str] = None      # 绑定 UA 指纹
    ip_prefix: Optional[str] = None            # 绑定 IP 段（可选）
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """检查会话是否有效"""
        return not self.is_expired()
    
    def refresh(self, extend_hours: int = 24) -> None:
        """刷新会话过期时间"""
        self.expires_at = datetime.utcnow() + timedelta(hours=extend_hours)
        self.last_active = datetime.utcnow()
    
    def reset_daily_quota(self) -> None:
        """重置每日配额"""
        self.quota.used_daily_tasks = 0
        self.quota.quota_reset_at = datetime.utcnow()
    
    @classmethod
    def create(
        cls,
        user_id: Optional[str] = None,
        expire_hours: int = 24,
        **kwargs
    ) -> "Session":
        """创建新会话"""
        now = datetime.utcnow()
        return cls(
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(hours=expire_hours),
            last_active=now,
            **kwargs
        )


class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    user_id: Optional[str] = None
    expire_hours: int = 24


class SessionResponse(BaseModel):
    """会话响应（不含敏感信息）"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    expires_at: datetime
    quota: SessionQuota


class SessionUpdateRequest(BaseModel):
    """更新会话请求"""
    preferences: Optional[SessionPreferences] = None

