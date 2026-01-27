# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/base_config.py
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

# 基础配置
PLATFORM = "xhs"  # 平台，xhs | dy | ks | bili | wb | tieba | zhihu | wechat
KEYWORDS = "编程副业,编程兼职"  # 关键词搜索配置，以英文逗号分隔
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""
CRAWLER_TYPE = (
    "search"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)
)
# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # kuaidaili | wandouhttp

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
# 小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码
# 抖音如果一直提示失败，打开浏览器看下是否扫码登录之后出现了手机号验证，如果出现了手动过一下再试。
HEADLESS = False

# 仅登录模式
# 设置为True时，只进行登录获取Cookie/Token，不会进行数据爬取
# 适用于 WebUI 的登录功能
LOGIN_ONLY = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用CDP模式 - 使用用户现有的Chrome/Edge浏览器进行爬取，提供更好的反检测能力
# 启用后将自动检测并启动用户的Chrome/Edge浏览器，通过CDP协议进行控制
# 这种方式使用真实的浏览器环境，包括用户的扩展、Cookie和设置，大大降低被检测的风险
ENABLE_CDP_MODE = True

# CDP调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = 9222

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测Chrome/Edge的安装路径
# Windows示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = ""

# CDP模式下是否启用无头模式
# 注意：即使设置为True，某些反检测功能在无头模式下可能效果不佳
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 60

# 是否在程序结束时自动关闭浏览器
# 设置为False可以保持浏览器运行，便于调试
AUTO_CLOSE_BROWSER = True

# 数据保存类型选项配置,支持六种类型：csv、db、json、sqlite、excel、postgres, 最好保存到DB，有排重的功能。
SAVE_DATA_OPTION = "json"  # csv or db or json or sqlite or excel or postgres

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 500

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬媒体模式（包含图片或视频资源），默认不开启爬媒体
ENABLE_GET_MEIDAS = False

# 是否开启爬评论模式, 默认开启爬评论
ENABLE_GET_COMMENTS = True

# 爬取一级评论的数量控制(单视频/帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 是否开启爬二级评论模式, 默认不开启爬二级评论
# 老版本项目使用了 db, 则需参考 schema/tables.sql line 287 增加表字段
ENABLE_GET_SUB_COMMENTS = False

# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = False
# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    "零几": "年份",  # 将“零几”识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# 爬取间隔时间
CRAWLER_MAX_SLEEP_SEC = 2

# ==================== 断点续爬配置 ====================
# 是否启用断点续爬功能
# 启用后，爬虫会自动保存进度，中断后可以从上次位置继续
ENABLE_RESUME_CRAWL = True

# 是否自动恢复上次未完成的任务
# 设置为True时，启动爬虫会自动检测并恢复未完成的任务
# 设置为False时，每次都会开始新任务
AUTO_RESUME_LAST_TASK = True

# 进度保存间隔（每处理N条数据保存一次进度）
# 较小的值更安全但会增加IO开销
PROGRESS_SAVE_INTERVAL = 5

# 进度文件保存目录
PROGRESS_DIR = "./crawl_progress"

# 是否在任务完成后自动清理旧的进度文件
CLEANUP_OLD_PROGRESS = True

# 保留已完成任务进度文件的天数
PROGRESS_KEEP_DAYS = 7

# ==================== 增量爬取配置 ====================
# 是否启用增量爬取（只爬取新增/更新的内容，大幅提升效率）
# 启用后，爬虫会记录上次爬取的位置，下次从该位置继续
# 不同爬取模式使用不同的增量策略：
#   - creator模式: 早停策略（遇到已存在内容自动停止）
#   - search模式: 时间/ID过滤策略
#   - detail模式: 简单去重策略
ENABLE_INCREMENTAL_CRAWL = False

# 创作者模式 - 早停阈值（连续N条已存在的笔记就停止爬取）
# 建议值：3-5，太小可能误判，太大影响效率
CREATOR_EARLY_STOP_THRESHOLD = 3

# 搜索模式 - 时间容差（秒）
# 为了防止遗漏，会向前多爬取一段时间的内容
INCREMENTAL_TIME_TOLERANCE = 3600  # 1小时

# 详情模式 - 是否强制更新已存在的内容（刷新点赞数等动态数据）
INCREMENTAL_UPDATE_EXISTING = True

# 增量元数据存储位置
# db: 保存到数据库（推荐，支持多实例，数据持久化）
# file: 保存到本地JSON文件（简单，单实例使用）
INCREMENTAL_METADATA_STORE = "db"

# ==================== 多账号配置 ====================
# 是否启用多账号模式
# 启用后，爬虫会从账号池中轮换使用账号，提高爬取稳定性
ENABLE_MULTI_ACCOUNT = False

# 账号配置文件目录
# 每个平台的账号配置保存在 {ACCOUNTS_DIR}/{platform}_accounts.json
ACCOUNTS_DIR = "./accounts"

# 账号轮换策略
# round_robin: 轮询 - 按顺序依次使用每个账号
# random: 随机 - 随机选择一个可用账号
# least_used: 最少使用 - 优先使用请求次数最少的账号
ACCOUNT_ROTATION_STRATEGY = "round_robin"

# 账号冷却时间（分钟）
# 当账号被限流时，进入冷却状态的时长
ACCOUNT_COOLING_MINUTES = 30

# 是否在账号被限流时自动切换到下一个账号
AUTO_SWITCH_ON_RATE_LIMIT = True

# 单个账号连续失败多少次后标记为冷却
MAX_CONSECUTIVE_FAILURES = 3

# ==================== IP代理池增强配置 ====================
# 是否为每个账号绑定固定代理
# 启用后，每个账号会使用其配置的专属代理IP
ENABLE_ACCOUNT_PROXY_BINDING = False

# 代理失败重试次数
PROXY_RETRY_COUNT = 3

# 代理验证超时时间（秒）
PROXY_VALIDATE_TIMEOUT = 10

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *
