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


class WeChatException(Exception):
    """微信公众号爬虫基础异常类"""
    pass


class DataFetchError(WeChatException):
    """数据获取错误"""
    pass


class LoginError(WeChatException):
    """登录错误"""
    pass


class TokenExpiredError(WeChatException):
    """Token过期错误"""
    pass


class AccountNotFoundError(WeChatException):
    """公众号未找到错误"""
    pass


class ArticleNotFoundError(WeChatException):
    """文章未找到错误"""
    pass


class RateLimitError(WeChatException):
    """频率限制错误"""
    pass


class InvalidCredentialsError(WeChatException):
    """凭证无效错误"""
    pass

