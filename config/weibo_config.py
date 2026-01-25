# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/weibo_config.py
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


# 微博平台配置

# 搜索类型，具体的枚举值在media_platform/weibo/field.py中
WEIBO_SEARCH_TYPE = "default"

# 指定微博ID列表
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]

# 指定微博用户ID列表
WEIBO_CREATOR_ID_LIST = [
    "5756404150",
    # ........................
]

# 指定微博VIP创作者ID列表（用于爬取VIP专属内容）
WEIBO_VIP_CREATOR_ID_LIST = [
    "7948230240",
    # ........................
]

# VIP内容类型配置
# 0: 专属内容, 1: 专属直播, 2: 付费问答, 3: 付费文章
WEIBO_VIP_CONTENT_TYPE = 0

# VIP内容Tab类型配置
WEIBO_VIP_TAB_TYPE = 0

# 是否开启微博爬取全文的功能，默认开启
# 如果开启的话会增加被风控的概率，相当于一个关键词搜索请求会再遍历所有帖子的时候，再请求一次帖子详情
ENABLE_WEIBO_FULL_TEXT = True

# ==================== VIP内容 Poster 下载配置 ====================
# 是否开启VIP内容poster图片下载，默认开启
ENABLE_VIP_POSTER_DOWNLOAD = True

# Poster保存方式: "local" 保存到本地, "oss" 上传到阿里云OSS, "both" 同时保存
VIP_POSTER_SAVE_MODE = "oss"

# ==================== 腾讯云 COS 配置 ====================
# 腾讯云 COS SecretId
COS_SECRET_ID = "REMOVED_SECRET_ID"

# 腾讯云 COS SecretKey
COS_SECRET_KEY = "REMOVED_SECRET_KEY"

# COS Region (例如: ap-shanghai, ap-beijing, ap-guangzhou)
COS_REGION = "ap-shanghai"

# COS Bucket名称
COS_BUCKET_NAME = "YOUR_BUCKET_NAME"

# COS存储路径前缀 (例如: vip_posters/)
COS_PATH_PREFIX = "vip_posters/"
