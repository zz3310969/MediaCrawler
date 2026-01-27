# 微信公众号爬虫 - 实现说明

## 📋 功能概览

已完成 wechat-article-exporter 核心功能向 MediaCrawler 的迁移，当前实现包括：

### ✅ 已实现功能

#### 1. 文章 HTML 内容下载（P0 核心功能）✅
- ✅ 访问文章页面并抓取完整 HTML 内容
- ✅ 验证 HTML 内容有效性（success/deleted/checking/failure）
- ✅ 处理已删除文章和审核中文章
- ✅ 支持配置是否启用内容下载（`ENABLE_GET_ARTICLE_CONTENT`）
- ✅ 可配置下载延迟（`ARTICLE_CONTENT_CRAWL_DELAY`）

#### 2. 评论和回复抓取（P1 重要功能）✅
- ✅ 支持分页获取所有评论（精选评论 + 普通评论）
- ✅ 自动获取评论回复（二级评论）
- ✅ 从 HTML 中提取 comment_id
- ✅ 处理评论分页参数（buffer、continue_flag）
- ✅ 支持获取完整的回复列表
- ✅ 需要配置 credentials（uin、key、pass_ticket）

#### 3. 阅读量和元数据统计（P1 重要功能）✅
- ✅ 从 HTML 中提取阅读量（read_num）
- ✅ 从 HTML 中提取点赞数（like_num）
- ✅ 支持多种数字格式解析（如 "10w+", "1000+"）
- ✅ 在下载文章内容时自动提取统计数据
- ✅ 支持配置是否启用统计数据抓取（`ENABLE_GET_READING_STATS`）

#### 4. 数据库存储支持（P0 核心功能）✅
- ✅ 完整的数据库模型定义
  - `WeChatArticle` - 文章表
  - `WeChatComment` - 评论表
  - `WeChatCommentReply` - 评论回复表
  - `WeChatAccount` - 公众号信息表
- ✅ MySQL/PostgreSQL 存储实现
- ✅ SQLite 存储实现
- ✅ 自动处理新增和更新逻辑

#### 5. 基础爬取功能
- ✅ 搜索公众号（`search_account`）
- ✅ 获取文章列表（`get_article_list`，支持分页）
- ✅ 指定公众号爬取（`get_creators_articles`）
- ✅ 公众号后台扫码登录（`mp_qrcode`）
- ✅ Cookie 登录

#### 6. 多种存储格式
- ✅ CSV 存储
- ✅ JSON 存储
- ✅ Excel 存储
- ✅ 数据库存储（MySQL/PostgreSQL/SQLite）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 添加了 beautifulsoup4 依赖用于 HTML 解析
uv sync
```

### 2. 配置文件

编辑 `config/wechat_config.py`：

```python
# 爬取类型
CRAWLER_TYPE = "search"  # search/detail/creator

# 搜索模式 - 公众号搜索关键词
WECHAT_ACCOUNT_KEYWORDS = ["Python", "编程"]

# 创作者模式 - 指定公众号 fakeid
WECHAT_ACCOUNT_IDS = [
    # "MzAwNDk4NjkzNw==",
]

# 是否获取评论
ENABLE_GET_COMMENTS = True

# 是否获取阅读量
ENABLE_GET_READING_STATS = True

# Credentials 凭证配置（用于获取评论和阅读量）
WECHAT_CREDENTIALS = {
    "uin": "",  # 用户uin
    "key": "",  # 认证key
    "pass_ticket": "",  # pass_ticket
}

# 是否爬取文章全文内容（HTML）
ENABLE_GET_ARTICLE_CONTENT = True

# 文章内容爬取延迟（秒）
ARTICLE_CONTENT_CRAWL_DELAY = 2

# 每个公众号最大爬取文章数
MAX_ARTICLES_PER_ACCOUNT = 100

# 登录类型
LOGIN_TYPE = "mp_qrcode"  # mp_qrcode: 公众号后台扫码登录
```

编辑 `config/base_config.py`：

```python
# 平台选择
PLATFORM = "wechat"

# 存储方式
SAVE_DATA_OPTION = "db"  # csv/json/db/sqlite/excel

# 是否启用评论爬取
ENABLE_GET_COMMENTS = True
```

### 3. 运行爬虫

```bash
# 搜索公众号并爬取文章
uv run main.py --platform wechat --lt mp_qrcode --type search

# 指定公众号爬取
uv run main.py --platform wechat --lt mp_qrcode --type creator

# 使用 WebUI
uv run uvicorn api.main:app --port 8080 --reload
# 然后访问 http://localhost:8080
```

---

## 📂 文件结构

```
media_platform/wechat/
├── __init__.py           # 模块导出
├── core.py               # 核心爬虫类 WeChatCrawler
├── client.py             # API 客户端 WeChatClient
├── login.py              # 登录处理 WeChatLogin
├── field.py              # 字段和枚举定义
├── exception.py          # 异常类定义
├── help.py               # 辅助工具函数
└── README.md             # 本文档

store/wechat/
├── __init__.py           # 存储工厂和接口函数
└── _store_impl.py        # 各种存储实现
    ├── WeChatCsvStoreImplement
    ├── WeChatJsonStoreImplement
    ├── WeChatDbStoreImplement
    ├── WeChatSqliteStoreImplement
    └── WeChatExcelStoreImplement

model/m_wechat.py         # 数据模型定义
config/wechat_config.py   # 微信配置文件
test/test_wechat.py       # 测试文件

database/models.py        # 数据库表定义
├── WeChatArticle        # 文章表
├── WeChatComment        # 评论表
├── WeChatCommentReply   # 回复表
└── WeChatAccount        # 公众号表
```

---

## 🔧 核心实现

### 1. WeChatClient - API 客户端

```python
# 获取文章 HTML
html = await client.get_article_html(article_url, with_credential=True)

# 获取评论（支持分页）
comments = await client.get_comments(
    biz=biz,
    comment_id=comment_id,
    uin=uin,
    key=key,
    pass_ticket=pass_ticket,
    buffer=buffer,  # 分页参数
    limit=100
)

# 获取评论回复
replies = await client.get_comment_replies(
    biz=biz,
    comment_id=comment_id,
    content_id=content_id,
    uin=uin,
    key=key,
    pass_ticket=pass_ticket,
    max_reply_id=max_reply_id
)
```

### 2. WeChatCrawler - 核心爬虫

```python
# 保存文章（包含 HTML 内容和统计数据）
async def save_article(self, article: Dict, fakeid: str, account_name: str):
    # 1. 下载 HTML 内容
    # 2. 提取阅读量和点赞数
    # 3. 保存到存储层
    # 4. 如果启用评论，获取评论
    pass

# 获取所有评论和回复
async def get_article_comments(self, article: Dict):
    # 1. 分页获取所有顶级评论
    # 2. 获取需要更多回复的评论
    # 3. 保存所有评论和回复
    pass
```

### 3. 数据库存储

```python
# 文章存储
await store.store_content({
    "article_id": "xxx",
    "title": "标题",
    "content": "<html>...</html>",  # 完整 HTML
    "read_num": 10000,
    "like_num": 100,
    ...
})

# 评论存储（自动处理回复）
await store.store_comment({
    "comment_id": "xxx",
    "article_id": "xxx",
    "content": "评论内容",
    "reply_list": [...]  # 回复列表
})
```

---

## 📊 数据库表结构

### wechat_article - 文章表
```sql
CREATE TABLE wechat_article (
    id INT PRIMARY KEY AUTO_INCREMENT,
    article_id VARCHAR(128) UNIQUE NOT NULL,
    title TEXT,
    link TEXT,
    cover TEXT,
    digest TEXT,
    create_time BIGINT,
    update_time BIGINT,
    author VARCHAR(255),
    fakeid VARCHAR(128),
    account_name VARCHAR(255),
    content TEXT,  -- HTML 内容
    read_num INT DEFAULT 0,
    like_num INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    source_keyword VARCHAR(255),
    add_ts BIGINT,
    last_modify_ts BIGINT,
    INDEX idx_fakeid_create_time (fakeid, create_time),
    INDEX idx_create_time (create_time)
);
```

### wechat_comment - 评论表
```sql
CREATE TABLE wechat_comment (
    id INT PRIMARY KEY AUTO_INCREMENT,
    comment_id VARCHAR(128) UNIQUE NOT NULL,
    article_id VARCHAR(128),
    content TEXT,
    create_time BIGINT,
    like_num INT DEFAULT 0,
    nick_name VARCHAR(255),
    logo_url TEXT,
    add_ts BIGINT,
    last_modify_ts BIGINT,
    INDEX idx_article_id (article_id),
    INDEX idx_create_time (create_time)
);
```

### wechat_comment_reply - 回复表
```sql
CREATE TABLE wechat_comment_reply (
    id INT PRIMARY KEY AUTO_INCREMENT,
    reply_id VARCHAR(128) UNIQUE NOT NULL,
    comment_id VARCHAR(128),
    article_id VARCHAR(128),
    content TEXT,
    create_time BIGINT,
    like_num INT DEFAULT 0,
    nick_name VARCHAR(255),
    add_ts BIGINT,
    last_modify_ts BIGINT,
    INDEX idx_comment_id (comment_id),
    INDEX idx_article_id (article_id)
);
```

---

## 🔐 获取 Credentials

要获取评论和阅读量，需要配置 credentials：

1. 在手机微信中打开任意公众号文章
2. 使用抓包工具（如 Charles、Fiddler）抓取请求
3. 找到包含以下参数的请求：
   - `uin`: 用户标识
   - `key`: 认证密钥
   - `pass_ticket`: 通行票据
4. 复制到 `config/wechat_config.py` 的 `WECHAT_CREDENTIALS` 中

---

## 🆚 与 wechat-article-exporter 的差异

### 已实现的核心功能

| 功能 | wechat-article-exporter | MediaCrawler | 状态 |
|------|------------------------|--------------|------|
| 搜索公众号 | ✅ | ✅ | 完全实现 |
| 文章列表 | ✅ | ✅ | 完全实现 |
| **文章 HTML 内容** | ✅ | ✅ | **✅ 已实现** |
| **评论抓取（分页）** | ✅ | ✅ | **✅ 已实现** |
| **评论回复** | ✅ | ✅ | **✅ 已实现** |
| **阅读量统计** | ✅ | ✅ | **✅ 已实现** |
| **数据库存储** | ❌ | ✅ | **✅ 已实现** |

### 未实现的功能

| 功能 | 说明 |
|------|------|
| 资源下载 | 图片、视频、音频下载和本地化 |
| 多格式导出 | Markdown、DOCX 格式导出 |
| 合集支持 | 识别和批量下载合集文章 |
| Web UI | 完整的可视化操作界面 |
| 高级过滤 | 按作者、时间、原创标识等过滤 |
| 断点续传 | 下载进度保存和恢复 |

---

## 🎯 使用建议

### 场景1：批量数据采集
使用 MediaCrawler，适合：
- 批量爬取多个公众号数据
- 需要数据库存储
- 自动化定时任务
- 与其他平台数据统一管理

### 场景2：精细化管理
使用 wechat-article-exporter，适合：
- 需要完整的离线包（HTML + 资源）
- 多格式导出需求
- 可视化操作界面
- 合集批量下载

### 场景3：混合使用
- MediaCrawler：初步数据采集和存储
- wechat-article-exporter：二次处理和导出

---

## 🐛 已知问题

1. **微信APP扫码登录未实现**
   - 当前只支持公众号后台扫码登录
   - 如需此功能，需补充实现

2. **资源下载功能缺失**
   - 不支持图片、视频等资源的下载和本地化
   - 如需此功能，建议使用 wechat-article-exporter

---

## 📝 更新日志

### 2025-01-27
- ✅ 实现文章 HTML 内容下载
- ✅ 实现评论和回复分页抓取
- ✅ 实现阅读量和点赞数提取
- ✅ 实现完整的数据库存储支持
- ✅ 添加 BeautifulSoup4 依赖
- ✅ 创建数据库表模型
- ✅ 完成 P0 和 P1 优先级功能

---

## 🤝 贡献

如需添加更多功能，请参考：
- wechat-article-exporter 源码：`/Users/zhengliangtian/Max/workspace/wechat-article-exporter`
- MediaCrawler 其他平台实现：`/Users/zhengliangtian/Max/pyProjects/MediaCrawler/media_platform/`

---

## 📄 许可

遵循 MediaCrawler 项目的 NON-COMMERCIAL LEARNING LICENSE 1.1
仅供学习和研究使用，不得用于商业用途。
