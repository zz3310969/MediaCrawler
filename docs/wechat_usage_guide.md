# 微信公众号爬虫使用指南

## 功能概述

MediaCrawler 已完成微信公众号爬虫的核心功能实现，包括：

### ✅ 已实现功能

1. **文章 HTML 内容下载** (P0 核心功能)
   - 下载完整的文章 HTML 内容
   - 自动验证 HTML 内容有效性
   - 检测已删除和审核中的文章
   - 支持配置下载延迟

2. **评论和回复抓取** (P1 重要功能)
   - 分页获取所有评论（精选评论和普通评论）
   - 自动获取评论的所有回复
   - 支持大量评论的高效抓取
   - 保存评论者信息和点赞数

3. **阅读量和元数据统计** (P1 重要功能)
   - 从 HTML 中提取阅读量
   - 提取点赞数、转发数等统计数据
   - 支持多种数字格式（如 "10w+", "1000+"）

4. **数据库存储支持** (P0 核心功能)
   - MySQL/PostgreSQL 数据库存储
   - SQLite 数据库存储
   - CSV、JSON、Excel 文件存储
   - 完整的数据表结构设计

## 快速开始

### 1. 安装依赖

```bash
# 进入项目目录
cd MediaCrawler

# 使用 uv 安装依赖（推荐）
uv sync

# 或者使用 pip
pip install -r requirements.txt
pip install beautifulsoup4  # 新增依赖

# 安装浏览器驱动
uv run playwright install
```

### 2. 配置文件

编辑 `config/wechat_config.py` 配置文件：

```python
# 爬取类型
CRAWLER_TYPE = "search"  # search/detail/creator

# 搜索关键词
WECHAT_ACCOUNT_KEYWORDS = ["Python", "AI"]

# 是否下载文章 HTML 内容
ENABLE_GET_ARTICLE_CONTENT = True

# 是否获取评论
ENABLE_GET_COMMENTS = True

# 是否获取阅读量（需要配置 credentials）
ENABLE_GET_READING_STATS = True

# Credentials 配置（用于获取评论和阅读量）
WECHAT_CREDENTIALS = {
    "uin": "your_uin",
    "key": "your_key",
    "pass_ticket": "your_pass_ticket",
}
```

### 3. 配置数据存储

编辑 `config/base_config.py`：

```python
# 数据存储方式
SAVE_DATA_OPTION = "db"  # csv/json/db/sqlite/excel

# 如果使用数据库，配置数据库连接
# 参考 config/db_config.py
```

### 4. 初始化数据库（如果使用数据库存储）

```bash
# SQLite（自动创建）
# 或者手动执行 SQL 脚本
sqlite3 data/media_crawler.db < database/migrations/add_wechat_tables.sql

# MySQL/PostgreSQL
# 手动执行 database/migrations/add_wechat_tables.sql 中的 SQL 语句
```

### 5. 运行爬虫

```bash
# 搜索模式：搜索公众号并爬取文章
uv run main.py --platform wechat --lt mp_qrcode --type search

# 创作者模式：爬取指定公众号的文章
uv run main.py --platform wechat --lt mp_qrcode --type creator

# 通过 WebUI 运行
uv run uvicorn api.main:app --port 8080 --reload
# 访问 http://localhost:8080
```

## 配置说明

### 爬取类型 (CRAWLER_TYPE)

- **search**: 搜索公众号模式
  - 根据关键词搜索公众号
  - 爬取搜索结果中的公众号文章
  - 配置 `WECHAT_ACCOUNT_KEYWORDS`

- **creator**: 指定公众号模式
  - 爬取指定公众号的所有文章
  - 配置 `WECHAT_ACCOUNT_IDS`（fakeid 列表）

- **detail**: 指定文章模式（待实现）
  - 爬取指定文章链接列表
  - 配置 `WECHAT_ARTICLE_URLS`

### 登录方式 (LOGIN_TYPE)

- **mp_qrcode**: 公众号后台扫码登录（推荐）
  - 功能最全，可以搜索公众号
  - 支持获取文章列表
  - 需要有公众号管理权限

- **cookie**: Cookie 登录
  - 使用已有的 Cookie 字符串
  - 配置 `COOKIES` 参数

### 获取 Credentials（用于评论和阅读量）

要获取评论和阅读量数据，需要抓包获取以下参数：

1. 在手机微信中打开任意公众号文章
2. 使用抓包工具（Charles、Fiddler 等）
3. 找到包含 `appmsg_comment` 或 `getappmsgext` 的请求
4. 提取以下参数：
   - `uin`: 用户 ID
   - `key`: 认证密钥
   - `pass_ticket`: 通行票据

配置示例：
```python
WECHAT_CREDENTIALS = {
    "uin": "MTIzNDU2Nzg5MA==",
    "key": "abcdef1234567890",
    "pass_ticket": "xyz123abc456",
}
```

## 数据存储格式

### 文章数据 (wechat_article)

```json
{
  "article_id": "2247484567",
  "title": "文章标题",
  "link": "https://mp.weixin.qq.com/s/xxxxx",
  "cover": "封面图片URL",
  "digest": "文章摘要",
  "create_time": 1704067200,
  "update_time": 1704067200,
  "author": "作者名",
  "fakeid": "MzAwNDk4NjkzNw==",
  "account_name": "公众号名称",
  "content": "<html>...</html>",
  "read_num": 10000,
  "like_num": 500,
  "comment_count": 100
}
```

### 评论数据 (wechat_comment)

```json
{
  "comment_id": "123456789",
  "article_id": "2247484567",
  "content": "评论内容",
  "create_time": 1704067200,
  "like_num": 10,
  "nick_name": "用户昵称",
  "logo_url": "头像URL",
  "reply_list": [
    {
      "reply_id": "987654321",
      "content": "回复内容",
      "nick_name": "回复者昵称",
      "like_num": 5
    }
  ]
}
```

## 性能优化建议

1. **并发控制**
   - 文章内容下载：可以设置较高并发
   - 评论数据获取：建议并发数 ≤ 5（需要 credentials）

2. **延迟配置**
   ```python
   ARTICLE_CONTENT_CRAWL_DELAY = 2  # 文章内容下载延迟（秒）
   CRAWLER_MAX_SLEEP_SEC = 2        # 评论获取延迟（秒）
   ```

3. **数据库索引**
   - 已自动创建必要的索引
   - 大量数据时考虑分区表

4. **代理配置**
   - 支持 IP 代理池
   - 参考 `config/base_config.py` 中的 `ENABLE_IP_PROXY` 配置

## 常见问题

### 1. 登录失败

**问题**: 扫码后无法登录

**解决方案**:
- 确保使用 `mp_qrcode` 登录方式
- 确保账号有公众号管理权限
- 检查网络连接

### 2. 无法获取评论

**问题**: 评论数据为空

**解决方案**:
- 确保配置了正确的 `WECHAT_CREDENTIALS`
- Credentials 可能过期，需要重新抓包获取
- 检查文章是否开启了评论功能

### 3. HTML 内容下载失败

**问题**: content 字段为空

**解决方案**:
- 确保 `ENABLE_GET_ARTICLE_CONTENT = True`
- 检查文章是否被删除或审核中
- 检查网络是否正常

### 4. 阅读量为 0

**问题**: read_num 和 like_num 都是 0

**解决方案**:
- 确保 `ENABLE_GET_READING_STATS = True`
- 需要配置有效的 `WECHAT_CREDENTIALS`
- 阅读量数据需要从带凭证的请求中获取

## 测试验证

运行测试脚本验证功能：

```bash
# 运行微信爬虫测试
uv run python test/test_wechat.py

# 测试数据库连接
uv run python -c "from database.db_session import get_session; import asyncio; asyncio.run(get_session().__aenter__())"
```

## 代码示例

### 基础使用

```python
import asyncio
from media_platform.wechat import WeChatCrawler

async def main():
    crawler = WeChatCrawler()
    await crawler.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### 手动调用 API

```python
from media_platform.wechat.client import WeChatClient
import asyncio

async def test_client():
    client = WeChatClient(
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0...",
            "Cookie": "your_cookie_here",
        },
        playwright_page=None,
        cookie_dict={},
    )
    
    # 设置 token
    client.set_token("your_token_here")
    
    # 搜索公众号
    result = await client.search_account("Python", begin=0, count=5)
    print(result)

if __name__ == "__main__":
    asyncio.run(test_client())
```

## 与 wechat-article-exporter 的对比

### 相同点
- 都支持文章内容下载
- 都支持评论和阅读量获取
- 都使用公众号后台 API

### 差异点
| 功能 | MediaCrawler | wechat-article-exporter |
|------|-------------|-------------------------|
| 定位 | 多平台爬虫工具 | 专注微信公众号 |
| UI | 命令行 + 简单 WebUI | 完整 Web 应用 |
| 导出格式 | CSV/JSON/DB/Excel | HTML/JSON/Excel/MD/DOCX |
| 资源下载 | 待实现 | 完整支持 |
| 使用场景 | 批量数据采集 | 精细化内容管理 |

## 后续优化方向

1. **资源下载功能** (P1)
   - 下载文章中的图片、视频
   - 本地化资源链接
   - 构建离线包

2. **合集支持** (P2)
   - 识别文章所属合集
   - 按合集批量下载

3. **导出格式扩展** (P2)
   - Markdown 导出
   - DOCX 导出
   - HTML 打包导出

4. **增强 WebUI** (P3)
   - 更友好的操作界面
   - 实时进度展示
   - 数据预览功能

## 技术支持

- 项目文档: https://nanmicoder.github.io/MediaCrawler/
- GitHub Issues: https://github.com/NanmiCoder/MediaCrawler/issues
- 微信交流群: 见项目 README

## 更新日志

### v1.0.0 (2026-01-27)

**新增功能**:
- ✅ 文章 HTML 内容下载
- ✅ 完整的评论和回复抓取
- ✅ 阅读量和元数据提取
- ✅ 数据库存储支持（MySQL/PostgreSQL/SQLite）
- ✅ 公众号搜索和指定公众号爬取
- ✅ 公众号后台扫码登录

**技术实现**:
- 基于 Playwright 浏览器自动化
- 使用 BeautifulSoup4 解析 HTML
- SQLAlchemy ORM 数据库操作
- 异步 IO 提升性能

**已知限制**:
- 不支持资源（图片/视频）本地下载
- 不支持合集识别
- 导出格式有限（待扩展 MD/DOCX）
