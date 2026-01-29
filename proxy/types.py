# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/proxy/types.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:18
# @Desc    : Basic types for proxy system
import hashlib
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProxyProtocol(Enum):
    """代理协议类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    
    @classmethod
    def from_string(cls, value: str) -> "ProxyProtocol":
        """从字符串解析协议类型"""
        value = value.lower().replace("://", "")
        for protocol in cls:
            if protocol.value == value:
                return protocol
        return cls.HTTP  # 默认HTTP


class ProviderNameEnum(Enum):
    """代理供应商枚举"""
    KUAI_DAILI_PROVIDER: str = "kuaidaili"
    WANDOU_HTTP_PROVIDER: str = "wandouhttp"
    CUSTOM_API_PROVIDER: str = "custom_api"
    LOCAL_FILE_PROVIDER: str = "local_file"


class ProxySource(Enum):
    """代理来源"""
    KUAIDAILI = "kuaidaili"
    WANDOU = "wandou"
    CUSTOM_API = "custom_api"
    LOCAL_FILE = "local_file"
    MANUAL = "manual"


class ProxyStatus(Enum):
    """代理状态"""
    ACTIVE = "active"           # 正常可用
    INACTIVE = "inactive"       # 不可用
    VALIDATING = "validating"   # 验证中
    EXPIRED = "expired"         # 已过期
    RETIRED = "retired"         # 已淘汰（质量差）


class BindingStatus(Enum):
    """绑定状态"""
    ACTIVE = "active"           # 正常绑定
    EXPIRED = "expired"         # 绑定的代理已过期
    UNBOUND = "unbound"         # 已解绑


class IpInfoModel(BaseModel):
    """统一IP代理模型 - 增强版"""

    ip: str = Field(title="IP地址")
    port: int = Field(title="端口")
    user: str = Field(default="", title="认证用户名")
    password: str = Field(default="", title="认证密码")
    protocol: str = Field(default="http", title="代理协议")
    expired_time_ts: Optional[int] = Field(default=None, title="过期时间戳")
    
    # 扩展字段
    proxy_id: Optional[str] = Field(default=None, title="代理唯一ID")
    source: str = Field(default="unknown", title="代理来源")
    country: str = Field(default="CN", title="国家")
    province: Optional[str] = Field(default=None, title="省份")
    city: Optional[str] = Field(default=None, title="城市")
    isp: Optional[str] = Field(default=None, title="运营商")
    
    @field_validator('protocol', mode='before')
    @classmethod
    def normalize_protocol(cls, v: str) -> str:
        """标准化协议字段"""
        if v is None:
            return "http"
        # 移除 :// 后缀
        return v.lower().replace("://", "")
    
    def model_post_init(self, __context: Any) -> None:
        """初始化后生成proxy_id"""
        if self.proxy_id is None:
            self.proxy_id = self.generate_proxy_id()
    
    def generate_proxy_id(self) -> str:
        """生成代理唯一ID"""
        key = f"{self.ip}:{self.port}:{self.protocol}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def is_expired(self, buffer_seconds: int = 30) -> bool:
        """
        检查代理是否已过期
        Args:
            buffer_seconds: 缓冲时间（秒），提前多少秒认为过期
        Returns:
            bool: True表示已过期或即将过期，False表示仍然有效
        """
        if self.expired_time_ts is None:
            return False
        current_ts = int(time.time())
        return current_ts >= (self.expired_time_ts - buffer_seconds)
    
    def to_url(self) -> str:
        """转换为代理URL格式"""
        protocol = self.protocol.replace("://", "")
        if self.user and self.password:
            return f"{protocol}://{self.user}:{self.password}@{self.ip}:{self.port}"
        return f"{protocol}://{self.ip}:{self.port}"
    
    def to_httpx_proxy(self) -> str:
        """转换为httpx代理格式（支持socks5）"""
        return self.to_url()
    
    def to_playwright_proxy(self) -> Dict[str, Any]:
        """转换为Playwright代理格式"""
        protocol = self.protocol.replace("://", "")
        proxy = {"server": f"{protocol}://{self.ip}:{self.port}"}
        if self.user:
            proxy["username"] = self.user
        if self.password:
            proxy["password"] = self.password
        return proxy
    
    def to_requests_proxy(self) -> Dict[str, str]:
        """转换为requests库代理格式"""
        url = self.to_url()
        return {
            "http": url,
            "https": url,
        }
    
    def get_protocol_enum(self) -> ProxyProtocol:
        """获取协议枚举"""
        return ProxyProtocol.from_string(self.protocol)
    
    def is_socks(self) -> bool:
        """是否为SOCKS代理"""
        protocol = self.protocol.lower().replace("://", "")
        return protocol in ("socks4", "socks5")


class ProxyRegionInfo(BaseModel):
    """代理地区信息（用于相似代理匹配）"""
    proxy_id: str = Field(title="代理ID")
    country: str = Field(default="CN", title="国家")
    province: Optional[str] = Field(default=None, title="省份")
    city: Optional[str] = Field(default=None, title="城市")
    isp: Optional[str] = Field(default=None, title="运营商")
    
    def similarity_score(self, other: "ProxyRegionInfo") -> float:
        """
        计算与另一个代理的地区相似度
        Args:
            other: 另一个代理的地区信息
        Returns:
            float: 相似度分数 (0-1)
        """
        score = 0.0
        if self.country and other.country and self.country == other.country:
            score += 0.2
        if self.province and other.province and self.province == other.province:
            score += 0.3
        if self.city and other.city and self.city == other.city:
            score += 0.3
        if self.isp and other.isp and self.isp == other.isp:
            score += 0.2
        return score


class AccountProxyBinding(BaseModel):
    """账号-代理绑定关系"""
    binding_id: str = Field(title="绑定ID")
    account_id: str = Field(title="账号ID")
    platform: str = Field(title="平台")
    proxy_id: str = Field(title="代理ID")
    
    # 绑定配置
    is_sticky: bool = Field(default=True, title="粘性绑定")
    allow_auto_rebind: bool = Field(default=True, title="允许自动重绑")
    
    # 时间信息
    bound_at: datetime = Field(default_factory=datetime.now, title="绑定时间")
    last_used_at: Optional[datetime] = Field(default=None, title="最后使用时间")
    last_verified_at: Optional[datetime] = Field(default=None, title="最后验证时间")
    
    # 状态
    status: str = Field(default=BindingStatus.ACTIVE.value, title="绑定状态")
    rebind_count: int = Field(default=0, title="重绑次数")
    
    def is_active(self) -> bool:
        """检查绑定是否有效"""
        return self.status == BindingStatus.ACTIVE.value
    
    def mark_used(self) -> None:
        """标记为已使用"""
        self.last_used_at = datetime.now()
    
    def mark_verified(self, success: bool = True) -> None:
        """标记验证结果"""
        self.last_verified_at = datetime.now()
        if not success:
            self.status = BindingStatus.EXPIRED.value


class ProxyQualityMetrics(BaseModel):
    """代理质量指标"""
    proxy_id: str = Field(title="代理ID")
    
    # 请求统计
    total_requests: int = Field(default=0, title="总请求数")
    success_requests: int = Field(default=0, title="成功请求数")
    failed_requests: int = Field(default=0, title="失败请求数")
    timeout_requests: int = Field(default=0, title="超时请求数")
    
    # 响应时间统计（毫秒）
    avg_response_time: float = Field(default=0.0, title="平均响应时间")
    min_response_time: Optional[float] = Field(default=None, title="最小响应时间")
    max_response_time: Optional[float] = Field(default=None, title="最大响应时间")
    p95_response_time: Optional[float] = Field(default=None, title="P95响应时间")
    
    # 稳定性指标
    consecutive_failures: int = Field(default=0, title="连续失败次数")
    consecutive_successes: int = Field(default=0, title="连续成功次数")
    last_success_at: Optional[datetime] = Field(default=None, title="最后成功时间")
    last_failure_at: Optional[datetime] = Field(default=None, title="最后失败时间")
    
    # 更新时间
    updated_at: datetime = Field(default_factory=datetime.now, title="更新时间")
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.success_requests / self.total_requests
    
    @property
    def quality_score(self) -> float:
        """
        计算综合质量评分 (0-100)
        权重: 成功率60% + 响应时间30% + 稳定性10%
        """
        # 成功率得分 (0-60)
        success_score = self.success_rate * 60
        
        # 响应时间得分 (0-30)，响应时间越短得分越高
        if self.avg_response_time <= 0:
            time_score = 30
        elif self.avg_response_time >= 5000:
            time_score = 0
        else:
            time_score = max(0, 30 - (self.avg_response_time / 5000) * 30)
        
        # 稳定性得分 (0-10)，连续失败越多得分越低
        stability_score = max(0, 10 - self.consecutive_failures * 2)
        
        return min(100, success_score + time_score + stability_score)
    
    def record_success(self, response_time_ms: float) -> None:
        """记录成功请求"""
        self.total_requests += 1
        self.success_requests += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_at = datetime.now()
        self._update_response_time(response_time_ms)
        self.updated_at = datetime.now()
    
    def record_failure(self, is_timeout: bool = False) -> None:
        """记录失败请求"""
        self.total_requests += 1
        self.failed_requests += 1
        if is_timeout:
            self.timeout_requests += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_at = datetime.now()
        self.updated_at = datetime.now()
    
    def _update_response_time(self, response_time_ms: float) -> None:
        """更新响应时间统计"""
        if self.min_response_time is None or response_time_ms < self.min_response_time:
            self.min_response_time = response_time_ms
        if self.max_response_time is None or response_time_ms > self.max_response_time:
            self.max_response_time = response_time_ms
        
        # 更新平均响应时间（增量计算）
        if self.success_requests == 1:
            self.avg_response_time = response_time_ms
        else:
            self.avg_response_time = (
                (self.avg_response_time * (self.success_requests - 1) + response_time_ms)
                / self.success_requests
            )


class ProxyUsageRecord(BaseModel):
    """代理使用记录"""
    record_id: str = Field(title="记录ID")
    proxy_id: str = Field(title="代理ID")
    account_id: Optional[str] = Field(default=None, title="账号ID")
    platform: str = Field(title="平台")
    
    # 请求信息
    request_url: Optional[str] = Field(default=None, title="请求URL")
    request_method: str = Field(default="GET", title="请求方法")
    response_code: Optional[int] = Field(default=None, title="响应状态码")
    response_time_ms: float = Field(default=0.0, title="响应时间(ms)")
    
    # 流量统计
    bytes_sent: int = Field(default=0, title="发送字节数")
    bytes_received: int = Field(default=0, title="接收字节数")
    
    # 结果
    success: bool = Field(default=True, title="是否成功")
    error_type: Optional[str] = Field(default=None, title="错误类型")
    error_message: Optional[str] = Field(default=None, title="错误信息")
    
    # 时间
    created_at: datetime = Field(default_factory=datetime.now, title="创建时间")


class ProxyDailyStats(BaseModel):
    """代理每日统计"""
    proxy_id: str = Field(title="代理ID")
    stat_date: str = Field(title="统计日期")  # YYYY-MM-DD
    
    # 请求统计
    total_requests: int = Field(default=0, title="总请求数")
    success_requests: int = Field(default=0, title="成功请求数")
    failed_requests: int = Field(default=0, title="失败请求数")
    
    # 流量统计
    total_bytes_sent: int = Field(default=0, title="总发送字节")
    total_bytes_received: int = Field(default=0, title="总接收字节")
    
    # 响应时间
    avg_response_time: float = Field(default=0.0, title="平均响应时间")
    
    # 使用情况
    unique_accounts: int = Field(default=0, title="独立账号数")
    platforms_used: List[str] = Field(default_factory=list, title="使用的平台")


class PersistedProxy(BaseModel):
    """持久化代理模型"""
    proxy_id: str = Field(title="代理唯一ID")
    ip: str = Field(title="IP地址")
    port: int = Field(title="端口")
    protocol: str = Field(default="http", title="协议")
    username: Optional[str] = Field(default=None, title="用户名")
    password: Optional[str] = Field(default=None, title="密码")
    source: str = Field(title="来源")
    source_name: Optional[str] = Field(default=None, title="来源名称")
    
    # 地区信息
    country: str = Field(default="CN", title="国家")
    province: Optional[str] = Field(default=None, title="省份")
    city: Optional[str] = Field(default=None, title="城市")
    isp: Optional[str] = Field(default=None, title="运营商")
    
    # 状态
    is_active: bool = Field(default=True, title="是否可用")
    is_validated: bool = Field(default=False, title="是否已验证")
    last_validated_at: Optional[datetime] = Field(default=None, title="最后验证时间")
    
    # 时间
    created_at: datetime = Field(default_factory=datetime.now, title="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, title="更新时间")
    expired_at: Optional[datetime] = Field(default=None, title="过期时间")
    
    def to_ip_info_model(self) -> IpInfoModel:
        """转换为IpInfoModel"""
        return IpInfoModel(
            ip=self.ip,
            port=self.port,
            protocol=self.protocol,
            user=self.username or "",
            password=self.password or "",
            expired_time_ts=int(self.expired_at.timestamp()) if self.expired_at else None,
            proxy_id=self.proxy_id,
            source=self.source,
            country=self.country,
            province=self.province,
            city=self.city,
            isp=self.isp,
        )
    
    @classmethod
    def from_ip_info_model(cls, model: IpInfoModel, source: str = "unknown") -> "PersistedProxy":
        """从IpInfoModel创建"""
        return cls(
            proxy_id=model.proxy_id or model.generate_proxy_id(),
            ip=model.ip,
            port=model.port,
            protocol=model.protocol,
            username=model.user if model.user else None,
            password=model.password if model.password else None,
            source=model.source or source,
            country=model.country,
            province=model.province,
            city=model.city,
            isp=model.isp,
            expired_at=datetime.fromtimestamp(model.expired_time_ts) if model.expired_time_ts else None,
        )
