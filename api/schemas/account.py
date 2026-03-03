# -*- coding: utf-8 -*-
"""
爬虫账号相关数据模型
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AccountStatus(str, Enum):
    """账号状态"""
    ACTIVE = "active"          # 正常可用
    INACTIVE = "inactive"      # 已停用
    PENDING = "pending"        # 待验证
    EXPIRED = "expired"        # 已过期


class LoginMethod(str, Enum):
    """登录方式"""
    QRCODE = "qrcode"          # 扫码登录
    COOKIE = "cookie"          # Cookie导入
    PHONE = "phone"            # 手机号登录


class Platform(str, Enum):
    """平台类型"""
    XHS = "xhs"                # 小红书
    DOUYIN = "dy"              # 抖音
    BILIBILI = "bili"          # B站
    WEIBO = "wb"               # 微博
    WECHAT = "wechat"          # 微信公众号
    KUAISHOU = "ks"            # 快手
    TIEBA = "tieba"            # 百度贴吧
    ZHIHU = "zhihu"            # 知乎


# ========== 账号实体 ==========

class AccountBase(BaseModel):
    """账号基础信息"""
    platform: Platform = Field(..., description="平台")
    username: Optional[str] = Field(default="", description="用户名/账号")
    nickname: Optional[str] = Field(default="", description="昵称")
    login_method: LoginMethod = Field(default=LoginMethod.COOKIE, description="登录方式")
    remark: Optional[str] = Field(default="", description="备注")


class AccountCreate(BaseModel):
    """创建账号请求"""
    platform: Platform = Field(..., description="平台")
    username: Optional[str] = Field(default="", description="用户名/账号")
    nickname: Optional[str] = Field(default="", description="昵称")
    login_method: LoginMethod = Field(default=LoginMethod.COOKIE, description="登录方式")
    cookies: Optional[str] = Field(default="", description="Cookie数据")
    remark: Optional[str] = Field(default="", description="备注")


class AccountUpdate(BaseModel):
    """更新账号请求"""
    nickname: Optional[str] = Field(default=None, description="昵称")
    status: Optional[AccountStatus] = Field(default=None, description="状态")
    cookies: Optional[str] = Field(default=None, description="Cookie数据")
    remark: Optional[str] = Field(default=None, description="备注")


class AccountCookieUpdate(BaseModel):
    """更新Cookie请求"""
    cookies: str = Field(..., description="新的Cookie数据")


class Account(BaseModel):
    """账号信息响应"""
    account_id: str = Field(..., description="账号唯一ID")
    platform: str = Field(..., description="平台")
    username: str = Field(default="", description="用户名/账号")
    nickname: str = Field(default="", description="昵称")
    avatar: str = Field(default="", description="头像URL")
    status: str = Field(..., description="状态")
    login_method: str = Field(..., description="登录方式")
    cookie_valid: bool = Field(default=False, description="Cookie是否有效")
    last_used_at: Optional[int] = Field(default=None, description="最后使用时间戳")
    last_validated_at: Optional[int] = Field(default=None, description="最后验证时间戳")
    expires_at: Optional[int] = Field(default=None, description="过期时间戳")
    created_at: int = Field(..., description="创建时间戳")
    remark: str = Field(default="", description="备注")
    
    class Config:
        from_attributes = True


class AccountWithCookie(Account):
    """带Cookie的账号信息（仅管理员可见）"""
    cookies: str = Field(default="", description="Cookie数据")


# ========== 列表查询 ==========

class AccountListRequest(BaseModel):
    """账号列表查询"""
    platform: Optional[Platform] = Field(default=None, description="平台筛选")
    status: Optional[AccountStatus] = Field(default=None, description="状态筛选")
    keyword: Optional[str] = Field(default=None, description="搜索关键词(用户名/昵称)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class AccountListResponse(BaseModel):
    """账号列表响应"""
    items: List[Account] = Field(default_factory=list, description="账号列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


# ========== 批量操作 ==========

class AccountBatchDelete(BaseModel):
    """批量删除账号"""
    account_ids: List[str] = Field(..., min_length=1, description="账号ID列表")


class AccountBatchStatusUpdate(BaseModel):
    """批量更新账号状态"""
    account_ids: List[str] = Field(..., min_length=1, description="账号ID列表")
    status: AccountStatus = Field(..., description="目标状态")


# ========== 登录相关 ==========

class QRCodeLoginInit(BaseModel):
    """扫码登录初始化响应"""
    qrcode_url: str = Field(..., description="二维码图片URL")
    qrcode_key: str = Field(..., description="二维码标识")
    expires_in: int = Field(..., description="过期时间(秒)")


class QRCodeLoginStatus(BaseModel):
    """扫码登录状态查询响应"""
    status: str = Field(..., description="状态: waiting/scanned/confirmed/expired")
    message: str = Field(default="", description="状态消息")
    account_id: Optional[str] = Field(default=None, description="登录成功后的账号ID")


class CookieValidateRequest(BaseModel):
    """Cookie验证请求"""
    platform: Platform = Field(..., description="平台")
    cookies: str = Field(..., description="Cookie数据")


class CookieValidateResponse(BaseModel):
    """Cookie验证响应"""
    valid: bool = Field(..., description="是否有效")
    username: Optional[str] = Field(default=None, description="用户名")
    nickname: Optional[str] = Field(default=None, description="昵称")
    avatar: Optional[str] = Field(default=None, description="头像URL")
    message: str = Field(default="", description="验证消息")


# ========== 统计相关 ==========

class AccountStats(BaseModel):
    """账号统计"""
    total: int = Field(default=0, description="总账号数")
    active: int = Field(default=0, description="正常账号数")
    inactive: int = Field(default=0, description="停用账号数")
    pending: int = Field(default=0, description="待验证账号数")
    expired: int = Field(default=0, description="已过期账号数")
    by_platform: dict = Field(default_factory=dict, description="各平台账号数")


# ========== 通用响应 ==========

class AccountResponse(BaseModel):
    """单个账号响应"""
    success: bool = True
    data: Account


class AccountStatsResponse(BaseModel):
    """账号统计响应"""
    success: bool = True
    data: AccountStats
