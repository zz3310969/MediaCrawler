# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/schemas/crawler.py
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

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel


class PlatformEnum(str, Enum):
    """Supported media platforms"""
    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    WECHAT = "wechat"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class LoginTypeEnum(str, Enum):
    """Login method"""
    QRCODE = "qrcode"
    PHONE = "phone"
    COOKIE = "cookie"
    MP_QRCODE = "mp_qrcode"  # WeChat MP backend login


class CrawlerTypeEnum(str, Enum):
    """Crawler type"""
    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"
    CREATOR_VIP = "creator_vip"  # VIP exclusive content from creators (Weibo only)
    ALBUM = "album"  # WeChat album mode


class SaveDataOptionEnum(str, Enum):
    """Data save option"""
    CSV = "csv"
    DB = "db"
    JSON = "json"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    EXCEL = "excel"


class ExportFormatEnum(str, Enum):
    """Export format options"""
    HTML = "html"
    MARKDOWN = "markdown"
    TXT = "txt"
    DOCX = "docx"
    JSON = "json"
    EXCEL = "excel"


class CrawlerStartRequest(BaseModel):
    """Crawler start request"""
    platform: PlatformEnum
    login_type: LoginTypeEnum = LoginTypeEnum.QRCODE
    crawler_type: CrawlerTypeEnum = CrawlerTypeEnum.SEARCH
    keywords: str = ""  # Keywords for search mode
    specified_ids: str = ""  # Post/video ID list for detail mode, comma-separated
    creator_ids: str = ""  # Creator ID list for creator mode, comma-separated
    vip_creator_ids: str = ""  # VIP creator ID list for creator_vip mode (Weibo only), comma-separated
    start_page: int = 1
    enable_comments: bool = True
    enable_sub_comments: bool = False
    save_option: SaveDataOptionEnum = SaveDataOptionEnum.JSON
    cookies: str = ""
    headless: bool = False
    # 增量爬取配置
    enable_incremental: bool = False  # 是否启用增量爬取（只爬取新内容）
    incremental_early_stop: int = 3  # 早停阈值（连续N条已存在内容就停止）
    
    # 微信专用配置
    wechat_enable_content: bool = False  # 是否下载文章HTML内容
    wechat_enable_reading_stats: bool = False  # 是否获取阅读量
    wechat_enable_export: bool = False  # 是否启用导出
    wechat_export_format: Optional[str] = "html"  # 导出格式
    wechat_album_ids: str = ""  # 合集ID列表，用于album模式
    wechat_credentials_uin: str = ""  # 微信凭证 uin
    wechat_credentials_key: str = ""  # 微信凭证 key
    wechat_credentials_pass_ticket: str = ""  # 微信凭证 pass_ticket
    wechat_token: str = ""  # 微信后台 token
    
    # 仅登录模式
    login_only: bool = False  # 是否只登录获取Cookie/Token，不进行数据爬取


class CrawlerStatusResponse(BaseModel):
    """Crawler status response"""
    status: Literal["idle", "running", "stopping", "error"]
    platform: Optional[str] = None
    crawler_type: Optional[str] = None
    started_at: Optional[str] = None
    error_message: Optional[str] = None
    # 进度信息
    progress: Optional[dict] = None  # 包含 current, total, percentage 等
    new_cookies: Optional[str] = None  # 登录成功后获取的新Cookie
    new_token: Optional[str] = None  # 登录成功后获取的新Token
    qrcode_img: Optional[str] = None  # 扫码登录的二维码 (base64)


class WeChatProgressInfo(BaseModel):
    """WeChat crawler progress information"""
    articles_crawled: int = 0
    articles_total: int = 0
    comments_crawled: int = 0
    resources_downloaded: int = 0
    exports_completed: int = 0
    current_account: Optional[str] = None
    current_album: Optional[str] = None


class LogEntry(BaseModel):
    """Log entry"""
    id: int
    timestamp: str
    level: Literal["info", "warning", "error", "success", "debug"]
    message: str


class DataFileInfo(BaseModel):
    """Data file information"""
    name: str
    path: str
    size: int
    modified_at: str
    record_count: Optional[int] = None
