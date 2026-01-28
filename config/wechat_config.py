# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 微信公众号爬虫配置

# ==================== 爬取类型配置 ====================
# 爬取类型
# search: 搜索公众号并爬取文章
# detail: 指定文章链接列表爬取详情
# creator: 指定公众号主页爬取所有文章
# keyword_article: 在公众号内搜索关键词文章
CRAWLER_TYPE = "search"

# ==================== 搜索模式配置 ====================
# 公众号搜索关键词（用于 search 模式）
# 多个关键词用英文逗号分隔
WECHAT_ACCOUNT_KEYWORDS = ["Python", "编程"]

# ==================== 创作者模式配置 ====================
# 指定公众号 fakeid 列表（用于 creator 模式）
# fakeid 可以从公众号主页URL中获取
# 例如：https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=MzAwNDk4NjkzNw==
# 其中 MzAwNDk4NjkzNw== 就是 fakeid（__biz参数）
WECHAT_ACCOUNT_IDS = [
    # "MzAwNDk4NjkzNw==",
    # "MjM5MjAxMDU2MA==",
]

# ==================== 详情模式配置 ====================
# 指定文章链接列表（用于 detail 模式）
WECHAT_ARTICLE_URLS = [
    # "https://mp.weixin.qq.com/s/xxxxx",
]

# ==================== 合集模式配置 ====================
# 指定合集ID列表（用于 album 模式）
# 格式1: {"biz": "公众号biz", "album_id": "合集ID"}
# 格式2: "公众号biz:合集ID"
WECHAT_ALBUM_IDS = [
    # {"biz": "MzAwNDk4NjkzNw==", "album_id": "1234567890"},
    # "MzAwNDk4NjkzNw==:1234567890",
]

# 是否爬取公众号的所有合集（与 WECHAT_ACCOUNT_IDS 配合使用）
ENABLE_CRAWL_ALL_ALBUMS = False

# 每个合集最大爬取文章数
MAX_ARTICLES_PER_ALBUM = 100

# ==================== 评论和统计配置 ====================
# 是否获取评论（需要 credentials 凭证）
ENABLE_GET_COMMENTS = True

# 是否获取阅读量和点赞数（需要 credentials 凭证）
ENABLE_GET_READING_STATS = True

# Credentials 凭证配置（用于获取评论和阅读量）
# 需要通过抓包获取：uin, key, pass_ticket
# 获取方法：
# 1. 在手机微信中打开任意公众号文章
# 2. 使用抓包工具（如Charles、Fiddler）抓取网络请求
# 3. 找到包含这些参数的请求，复制到这里
WECHAT_CREDENTIALS = {
    "uin": "",  # 用户uin
    "key": "",  # 认证key
    "pass_ticket": "",  # pass_ticket
}

# ==================== 爬取控制配置 ====================
# 每个公众号最大爬取文章数（0 表示不限制，获取全部文章）
MAX_ARTICLES_PER_ACCOUNT = 0

# 文章列表分页大小
ARTICLE_LIST_PAGE_SIZE = 10

# ==================== 增量爬取配置 ====================
# 是否启用增量爬取（断点续爬）
# 启用后，会自动跳过已爬取的文章，只获取新文章
# 注意：此配置会被 API 请求中的 enable_incremental 参数覆盖
ENABLE_WECHAT_INCREMENTAL = False  # 默认关闭，通过 API 参数控制

# 早停阈值：连续 N 条文章已存在时停止爬取
# 建议值：3-5，太小可能误判（中间有删除的文章），太大影响效率
WECHAT_EARLY_STOP_THRESHOLD = 5

# 是否爬取文章全文内容（HTML）
ENABLE_GET_ARTICLE_CONTENT = False

# 文章内容爬取延迟（秒）
ARTICLE_CONTENT_CRAWL_DELAY = 2

# 是否下载文章资源（图片、视频、音频）
ENABLE_DOWNLOAD_RESOURCES = False

# ==================== 内容存储优化配置 ====================
# 是否将文章HTML内容存储到本地文件（而非数据库）
# 启用后，数据库只保存文件路径，大幅减少数据库体积
# 内容文件存储路径：data/wechat/content/{fakeid}/{article_id}.html.gz
ENABLE_CONTENT_FILE_STORAGE = True

# 内容文件存储根目录
CONTENT_STORAGE_BASE_DIR = "data"

# 是否启用gzip压缩（推荐开启，可节省60-80%存储空间）
ENABLE_CONTENT_COMPRESSION = True

# ==================== 导出配置 ====================
# 是否启用导出功能
ENABLE_EXPORT = False

# 导出格式：html, markdown, txt, docx
# 可以是单个格式或多个格式的列表
EXPORT_FORMAT = "html"

# 导出目录
EXPORT_PATH = "data/wechat_exports"

# HTML导出时是否包含评论
EXPORT_HTML_INCLUDE_COMMENTS = True

# Markdown/DOCX导出时是否包含图片
EXPORT_INCLUDE_IMAGES = True

# ==================== 登录配置 ====================
# 登录模式
# browser: 浏览器自动化登录（依赖 Playwright，较重，可能不稳定）
# api: 纯 API 模拟登录（推荐，轻量，稳定，无需浏览器界面）
LOGIN_MODE = "api"

# 登录类型
# mp_qrcode: 公众号后台扫码登录（推荐，功能最全）
# qrcode: 微信APP扫码登录（功能受限）
# cookie: Cookie登录
LOGIN_TYPE = "mp_qrcode"

# Cookie字符串（用于 cookie 登录）
# 格式：key1=value1; key2=value2; ...
COOKIES = ""
