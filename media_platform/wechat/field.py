# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
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


class LoginType(Enum):
    """登录类型"""
    MP_QRCODE = "mp_qrcode"  # 公众号后台扫码登录
    QRCODE = "qrcode"  # 微信APP扫码登录
    COOKIE = "cookie"  # Cookie登录


class CrawlerType(Enum):
    """爬取类型"""
    SEARCH = "search"  # 搜索公众号
    DETAIL = "detail"  # 指定文章详情
    CREATOR = "creator"  # 指定公众号主页
    KEYWORD_ARTICLE = "keyword_article"  # 公众号内搜索关键词文章


class ArticleType(Enum):
    """文章类型"""
    NORMAL = 1  # 普通图文
    VIDEO = 2  # 视频
    IMAGE = 3  # 图片
    TEXT = 4  # 文本

