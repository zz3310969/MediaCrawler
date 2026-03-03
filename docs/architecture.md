# 项目架构

## 1. 项目概述

MediaCrawler 是一个多平台自媒体爬虫框架，基于 Python 异步编程 + Playwright 浏览器自动化实现。核心思路是通过浏览器保留登录态，利用 JS 表达式获取签名参数，无需逆向复杂加密算法。

### 支持平台

| 平台 | 代号 | 功能 |
|------|------|------|
| 小红书 | `xhs` | 笔记搜索、详情、创作者 |
| 抖音 | `dy` | 视频搜索、详情、创作者 |
| 快手 | `ks` | 视频搜索、详情、创作者 |
| B站 | `bili` | 视频搜索、详情、UP主 |
| 微博 | `wb` | 微博搜索、详情、博主 |
| 贴吧 | `tieba` | 帖子搜索、详情 |
| 知乎 | `zhihu` | 问答搜索、详情、答主 |
| 微信 | `wechat` | 公众号文章、评论 |

### 三种爬虫模式

| 模式 | 配置值 | 说明 |
|------|--------|------|
| 搜索模式 | `search` | 按关键词搜索内容 |
| 详情模式 | `detail` | 按帖子/视频 ID 获取详情 |
| 创作者模式 | `creator` | 获取指定创作者的所有内容 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                       入口层                             │
│   main.py ─── cmd_arg/ ─── config/                      │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                    核心爬虫层                             │
│   CrawlerFactory → AbstractCrawler                      │
│   ├── XiaoHongShuCrawler (xhs/)                         │
│   ├── DouYinCrawler      (douyin/)                      │
│   ├── KuaishouCrawler    (kuaishou/)                    │
│   ├── BilibiliCrawler    (bilibili/)                    │
│   ├── WeiboCrawler       (weibo/)                       │
│   ├── TieBaCrawler       (tieba/)                       │
│   ├── ZhihuCrawler       (zhihu/)                       │
│   └── WeChatCrawler      (wechat/)                      │
└────────┬───────────┬──────────┬─────────────────────────┘
         │           │          │
┌────────▼──┐ ┌──────▼────┐ ┌──▼──────────────────────────┐
│ API客户端 │ │  数据存储  │ │       基础设施               │
│ *Client   │ │   store/  │ │ Playwright/CDP  proxy/      │
│ 各平台HTTP│ │ CSV/JSON/ │ │ account/        cache/      │
│ 请求封装  │ │ Excel/DB  │ │ anti_detect/    tools/      │
└───────────┘ └───────────┘ └─────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     WebUI 层                             │
│   api/ (FastAPI 后端)  ←→  webui-src/ (React 前端)      │
│   ├── routers/   REST API + WebSocket                   │
│   ├── services/  任务执行、爬虫适配、事件总线             │
│   └── schemas/   请求/响应模型                           │
└─────────────────────────────────────────────────────────┘
```

### 数据流向

```
关键词/ID + 配置
    → 启动浏览器（Playwright 或 CDP）
    → 登录认证（QR码/手机号/Cookie）
    → 搜索/爬取
    → 数据解析（内容 + 评论 + 创作者 + 媒体）
    → 存储（CSV / JSON / Excel / SQLite / MySQL / PostgreSQL / MongoDB）
```

---

## 3. 目录结构

```
MediaCrawler/
├── main.py                  # 程序入口，CrawlerFactory 调度
├── var.py                   # 全局上下文变量
├── pyproject.toml           # 项目配置与依赖
│
├── base/                    # 抽象基类
│   └── base_crawler.py      # AbstractCrawler - 所有爬虫的父类
│
├── config/                  # 配置管理
│   ├── base_config.py       # 核心配置（平台、登录、存储、代理等）
│   ├── db_config.py         # 数据库连接配置
│   ├── anti_detect_config.py
│   └── {platform}_config.py # 各平台独立配置
│
├── media_platform/          # 各平台爬虫实现
│   ├── xhs/                 # 小红书
│   ├── douyin/              # 抖音
│   ├── kuaishou/            # 快手
│   ├── bilibili/            # B站
│   ├── weibo/               # 微博
│   ├── tieba/               # 贴吧
│   ├── zhihu/               # 知乎
│   └── wechat/              # 微信
│   # 每个平台包含: core.py, client.py, login.py, field.py, help.py
│
├── store/                   # 数据存储层
│   ├── excel_store_base.py  # Excel 存储基类
│   └── {platform}/          # 各平台的存储实现
│       └── _store_impl.py   # CSV/JSON/DB/SQLite/MongoDB/Excel 6种实现
│
├── database/                # 数据库层
│   ├── db.py                # 连接管理、连接验证
│   ├── db_session.py        # 会话管理
│   ├── models.py            # 爬虫数据 ORM 模型
│   ├── webui_models.py      # WebUI 相关模型
│   └── migrations/          # 数据库迁移脚本
│
├── proxy/                   # 代理系统
│   ├── proxy_manager.py     # 代理管理器
│   ├── proxy_ip_pool.py     # IP 池
│   ├── providers/           # 代理提供商（快代理、豌豆等）
│   ├── quality/             # 质量评估与自动淘汰
│   ├── failover/            # 故障转移（含熔断器）
│   ├── binding/             # 账号-代理绑定
│   └── persistence/         # 代理持久化存储
│
├── anti_detect/             # 反爬增强
│   ├── fingerprint/         # 浏览器指纹管理
│   ├── rate_limiter/        # 智能限速
│   └── behavior/            # 人类行为模拟
│
├── api/                     # WebUI 后端（FastAPI）
│   ├── main.py              # 应用入口
│   ├── worker_main.py       # Worker 进程入口
│   ├── routers/             # REST API + WebSocket 路由
│   ├── services/            # 业务逻辑（任务执行、爬虫适配）
│   │   ├── crud/            # 数据库 CRUD
│   │   ├── queue/           # 任务队列（内存/Redis）
│   │   ├── event/           # 事件总线
│   │   ├── session/         # 会话管理
│   │   └── storage/         # 任务存储
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── interfaces/          # 抽象接口定义
│   └── middleware/          # 中间件（Session、CORS）
│
├── webui-src/               # WebUI 前端（React + TypeScript + Vite）
│   └── src/
│       ├── pages/           # 页面组件
│       ├── components/      # UI 组件
│       ├── api/             # API 调用层
│       ├── hooks/           # React Hooks
│       └── types/           # TypeScript 类型
│
├── account/                 # 登录态管理
├── cache/                   # 缓存（本地 / Redis）
├── crawler/                 # 进度管理（断点续爬）
├── model/                   # Pydantic 数据模型
├── tools/                   # 工具（浏览器启动、CDP、滑块验证等）
├── cmd_arg/                 # 命令行参数定义
├── libs/                    # JS 脚本（stealth.js 等）
├── skills/                  # 自动化工具（健康检查、统计、发布）
└── docs/                    # 本文档目录
```

---

## 4. 核心设计模式

### 4.1 工厂模式 - CrawlerFactory

`main.py` 中通过平台字符串创建对应的爬虫实例：

```python
class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        # ...
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        return CrawlerFactory.CRAWLERS[platform]()
```

### 4.2 抽象基类 - AbstractCrawler

所有平台爬虫继承 `base/base_crawler.py`，统一接口：

- `start()` - 启动爬虫
- `search()` - 关键词搜索
- `get_specified_notes()` - 按 ID 获取详情
- `get_creators_and_notes()` - 获取创作者内容

基类还封装了：断点续爬（`ProgressManager`）、多账号管理（`AccountPool`）、增量爬取等通用逻辑。

### 4.3 存储工厂

每个平台有独立的 `StoreFactory`，支持 6 种存储后端：

```python
class XhsStoreFactory:
    STORES = {
        "csv": XhsCsvStoreImplement,
        "json": XhsJsonStoreImplement,
        "db": XhsDbStoreImplement,
        "sqlite": XhsSqliteStoreImplement,
        "mongodb": XhsMongoStoreImplement,
        "excel": XhsExcelStoreImplement,
    }
```

### 4.4 CDP 模式

通过 Chrome DevTools Protocol 连接用户已有的 Chrome 浏览器，复用用户的扩展、登录状态和浏览器指纹，提升反检测能力。

### 4.5 WebUI 任务系统

- **REST API** 创建/管理任务
- **TaskExecutor** 执行爬虫任务
- **EventBus** 发布/订阅模式推送任务状态
- **WebSocket** 实时推送进度和日志到前端

---

## 5. 数据模型

### 各平台数据表

| 平台 | 内容表 | 评论表 | 创作者表 |
|------|--------|--------|---------|
| 小红书 | XHSNote | XHSNoteComment | XHSCreator |
| 抖音 | DouyinAweme | DouyinAwemeComment | DyCreator |
| 快手 | KuaishouVideo | KuaishouVideoComment | KsCreator |
| B站 | BilibiliVideo | BilibiliVideoComment | BilibiliUpInfo |
| 微博 | WeiboNote | WeiboNoteComment | WeiboCreator |
| 贴吧 | TiebaNote | TiebaNoteComment | - |
| 知乎 | ZhihuContent | ZhihuContentComment | ZhihuCreator |
| 微信 | WechatArticle | WechatComment | - |

ORM 模型定义在 `database/models.py`，WebUI 相关模型在 `database/webui_models.py`。

---

## 6. 配置体系

所有配置在 `config/base_config.py`，有详细中文注释。关键配置项：

```python
PLATFORM = "xhs"                    # 目标平台
CRAWLER_TYPE = "search"              # 爬虫模式: search / detail / creator
LOGIN_TYPE = "qrcode"                # 登录方式: qrcode / phone / cookie
SAVE_DATA_OPTION = "json"            # 存储方式: csv / json / excel / sqlite / db / postgres / mongodb
ENABLE_GET_COMMENTS = True           # 是否爬取评论
ENABLE_IP_PROXY = False              # 是否启用代理池
ENABLE_CDP_MODE = True               # 是否使用 CDP 模式
ENABLE_RESUME_CRAWL = False          # 是否启用断点续爬
ENABLE_INCREMENTAL_CRAWL = False     # 是否启用增量爬取
HEADLESS = False                     # 是否无头模式
```

各平台有独立配置文件覆盖基础配置，如 `config/xhs_config.py`。

---

## 7. 扩展开发

### 添加新平台

1. 在 `media_platform/` 下创建新目录
2. 实现 `core.py`（继承 `AbstractCrawler`）、`client.py`、`login.py`、`field.py`
3. 在 `config/` 下创建平台配置文件
4. 在 `cmd_arg/arg.py` 添加平台枚举
5. 在 `main.py` 的 `CrawlerFactory.CRAWLERS` 中注册
6. 在 `store/` 下创建存储实现
7. 在 `database/models.py` 添加数据模型

### 添加新存储方式

1. 在 `store/` 下创建存储实现类，继承 `AbstractStore`
2. 实现 `store_content`、`store_comment`、`store_creator` 方法
3. 在各平台的 `StoreFactory.STORES` 中注册

### 添加新代理提供商

1. 在 `proxy/providers/` 下创建代理类，继承 `BaseProxy`
2. 实现 `get_proxy()` 方法
3. 在配置中注册

---

## 8. 环境变量

| 变量 | 说明 |
|------|------|
| `INTEGRATED_WORKER=1` | 爬虫与 API 同进程运行（开发用） |
| `USE_REAL_CRAWLER=1` | WebUI 使用真实爬虫（默认 Mock） |
| `SIGN_SERVER_ENABLED=1` | 启用远程签名服务 |
| `SIGN_SERVER_URL` | 签名服务地址 |
