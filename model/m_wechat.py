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

from pydantic import BaseModel, Field
from typing import Optional


class WeChatAccount(BaseModel):
    """微信公众号信息"""
    fakeid: str = Field(title="公众号fakeid")
    nickname: str = Field(title="公众号名称")
    alias: str = Field(default="", title="公众号别名")
    round_head_img: str = Field(default="", title="公众号头像")
    service_type: int = Field(default=0, title="公众号类型")


class WeChatArticle(BaseModel):
    """微信文章信息"""
    article_id: str = Field(title="文章ID")
    title: str = Field(title="文章标题")
    link: str = Field(title="文章链接")
    cover: str = Field(default="", title="文章封面")
    digest: str = Field(default="", title="文章摘要")
    create_time: int = Field(default=0, title="创建时间")
    update_time: int = Field(default=0, title="更新时间")
    author: str = Field(default="", title="作者")
    fakeid: str = Field(default="", title="所属公众号fakeid")
    account_name: str = Field(default="", title="所属公众号名称")
    content: str = Field(default="", title="文章内容HTML")
    read_num: int = Field(default=0, title="阅读量")
    like_num: int = Field(default=0, title="在看数")
    old_like_num: int = Field(default=0, title="点赞数（旧版）")
    share_num: int = Field(default=0, title="分享数")
    comment_count: int = Field(default=0, title="评论数")


class WeChatComment(BaseModel):
    """微信文章评论"""
    comment_id: str = Field(title="评论ID")
    content: str = Field(title="评论内容")
    create_time: int = Field(default=0, title="评论时间")
    like_num: int = Field(default=0, title="点赞数")
    nick_name: str = Field(default="", title="评论者昵称")
    logo_url: str = Field(default="", title="评论者头像")
    article_id: str = Field(default="", title="所属文章ID")
    reply_list: list = Field(default_factory=list, title="回复列表")


class WeChatArticleUrl(BaseModel):
    """微信文章URL信息"""
    biz: str = Field(title="公众号__biz参数")
    mid: str = Field(default="", title="文章mid")
    idx: str = Field(default="", title="文章idx")
    sn: str = Field(default="", title="文章sn")

