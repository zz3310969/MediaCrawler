"""
API Key 相关数据模型
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import secrets


class ApiKey(BaseModel):
    """API Key 实体"""
    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key_hash: str
    key_prefix: str
    name: str = ""
    user_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["tasks:*", "schedules:*", "data:*"])
    rate_limit: int = 60
    expires_at: Optional[datetime] = None
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def has_scope(self, required_scope: str) -> bool:
        """检查是否拥有指定权限"""
        for scope in self.scopes:
            if scope == "*":
                return True
            if scope == required_scope:
                return True
            scope_parts = scope.split(":")
            required_parts = required_scope.split(":")
            if len(scope_parts) == 2 and len(required_parts) == 2:
                if scope_parts[0] == required_parts[0] and scope_parts[1] == "*":
                    return True
        return False


class ApiKeyCreateRequest(BaseModel):
    """创建 API Key 请求"""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["tasks:*", "schedules:*", "data:*"])
    rate_limit: int = Field(default=60, ge=1, le=1000)
    expire_days: Optional[int] = Field(default=None, ge=1, le=365)


class ApiKeyCreateResponse(BaseModel):
    """创建 API Key 响应（仅在创建时返回完整 key）"""
    key_id: str
    api_key: str
    name: str
    scopes: List[str]
    rate_limit: int
    expires_at: Optional[datetime]
    created_at: datetime


class ApiKeyInfo(BaseModel):
    """API Key 信息（不含完整 key）"""
    key_id: str
    key_prefix: str
    name: str
    scopes: List[str]
    rate_limit: int
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
