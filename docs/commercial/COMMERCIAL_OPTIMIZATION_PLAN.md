# MediaCrawler 商业化优化方案

> 基于现有项目的深度分析，提供从 Demo 级别到商业级系统的完整升级路径。
>
> 生成日期：2025-01-01

---

## 目录

1. [项目现状评估](#1-项目现状评估)
2. [架构优化方案](#2-架构优化方案)
3. [性能优化方案](#3-性能优化方案)
4. [反爬增强方案](#4-反爬增强方案)
5. [前端交互优化](#5-前端交互优化)
6. [监控与可观测性](#6-监控与可观测性)
7. [实施路线图](#7-实施路线图)

---

## 1. 项目现状评估

### 1.1 整体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | 4/5 | 模块化良好，但缺乏分布式支持 |
| 代码质量 | 4/5 | 规范统一，类型注解到位 |
| 数据库设计 | 3/5 | 支持多种存储，但缺少索引优化和分表 |
| API 层 | 3/5 | FastAPI 基础完善，缺乏认证和限流 |
| 前端实现 | 3/5 | React+TS 技术栈合理，交互待优化 |
| 代理系统 | 5/5 | 完整的代理池+质量评估+故障转移 |
| 多任务系统 | 3/5 | 基础功能完成，需分布式升级 |
| 配置管理 | 3/5 | Python 模块级配置，需升级为环境变量+Pydantic |

### 1.2 核心优势

- **多平台覆盖全面**：7大主流平台统一接口
- **Playwright 自动化成熟**：免逆向的登录态管理
- **代理系统完善**：多供应商+质量评估+自动故障转移
- **断点续爬**：支持中断恢复，生产必备
- **CDP 模式**：利用用户浏览器绕过检测

### 1.3 需要提升的方面

- **分布式架构**：当前单机运行，无法水平扩展
- **安全性**：缺乏数据加密、API 认证
- **监控告警**：没有系统级监控和告警
- **自动化测试**：测试覆盖率不足
- **配置管理**：硬编码配置，不适合多环境部署

---

## 2. 架构优化方案

### 2.1 当前架构 vs 目标架构

**当前架构（单体）**：
```
用户 -> WebUI -> FastAPI -> 单进程爬虫 -> 数据库
```

**目标架构（分布式微服务）**：
```
                    +---------------+
                    |    Nginx      |
                    |   反向代理     |
                    +-------+-------+
                            |
              +-------------+-------------+
              |             |             |
        +-----+----+ +-----+-----+ +----+------+
        |  WebUI   | |   API     | | WebSocket |
        |  静态资源 | | Gateway   | |  Server   |
        +----------+ +-----+-----+ +----+------+
                            |            |
                    +-------+------------+-----+
                    |       消息队列             |
                    |    Redis / RabbitMQ       |
                    +-------+------------+-----+
                            |            |
              +-------------+--+  +------+----------+
              |  Worker 集群    |  |  调度器 Scheduler |
              |  (Celery)      |  |  (Beat/APScheduler)|
              |  +----------+  |  +-----------------+
              |  | Worker 1 |  |
              |  | Worker 2 |  |
              |  | Worker N |  |
              |  +----------+  |
              +--------+-------+
                       |
         +-------------+-------------+
         |             |             |
    +----+---+   +-----+--+   +-----+--+
    | MySQL  |   | Redis  |   |  S3/   |
    | 主从    |   | Cache  |   | MinIO  |
    +--------+   +--------+   +--------+
```

### 2.2 分布式任务队列实现

使用 Celery + Redis 替代当前的单进程任务执行：

```python
# crawler/task_queue.py
"""分布式任务队列 - 基于 Celery"""

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

# Celery 实例配置
celery_app = Celery(
    "mediacrawler",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 并发控制
    worker_concurrency=4,
    worker_prefetch_multiplier=1,

    # 任务超时
    task_soft_time_limit=3600,   # 1小时软超时
    task_time_limit=3900,        # 1小时5分硬超时

    # 重试策略
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 任务路由
    task_routes={
        "crawler.tasks.crawl_search": {"queue": "crawl"},
        "crawler.tasks.crawl_detail": {"queue": "crawl"},
        "crawler.tasks.crawl_creator": {"queue": "crawl_heavy"},
        "crawler.tasks.export_data": {"queue": "export"},
    },

    # 限流
    task_annotations={
        "crawler.tasks.crawl_search": {"rate_limit": "10/m"},
        "crawler.tasks.crawl_detail": {"rate_limit": "30/m"},
    },
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def crawl_search(self, task_id: str, platform: str, keywords: list, config: dict):
    """搜索爬取任务"""
    try:
        from media_platform import CrawlerFactory
        crawler = CrawlerFactory.create(platform)
        crawler.configure(config)
        results = crawler.search(keywords)
        return {"task_id": task_id, "status": "success", "count": len(results)}
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=3)
def crawl_detail(self, task_id: str, platform: str, note_ids: list, config: dict):
    """详情爬取任务"""
    try:
        from media_platform import CrawlerFactory
        crawler = CrawlerFactory.create(platform)
        crawler.configure(config)
        results = crawler.get_details(note_ids)
        return {"task_id": task_id, "status": "success", "count": len(results)}
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
```

### 2.3 配置管理升级

从 Python 模块级配置升级为 Pydantic Settings：

```python
# config/settings.py
"""基于 Pydantic 的配置管理"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=3306, env="DB_PORT")
    username: str = Field(default="root", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    database: str = Field(default="mediacrawler", env="DB_NAME")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")

    @property
    def url(self) -> str:
        return f"mysql+asyncmy://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    class Config:
        env_prefix = "DB_"


class RedisSettings(BaseSettings):
    """Redis 配置"""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    cache_db: int = Field(default=0, env="REDIS_CACHE_DB")
    queue_db: int = Field(default=1, env="REDIS_QUEUE_DB")
    session_db: int = Field(default=2, env="REDIS_SESSION_DB")

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}"


class CrawlerSettings(BaseSettings):
    """爬虫配置"""
    max_concurrency: int = Field(default=5, env="CRAWLER_MAX_CONCURRENCY")
    request_timeout: int = Field(default=30, env="CRAWLER_REQUEST_TIMEOUT")
    retry_times: int = Field(default=3, env="CRAWLER_RETRY_TIMES")
    retry_delay: int = Field(default=5, env="CRAWLER_RETRY_DELAY")
    headless: bool = Field(default=True, env="CRAWLER_HEADLESS")
    user_data_dir: str = Field(default="./browser_data", env="CRAWLER_USER_DATA_DIR")
    platforms: List[str] = Field(
        default=["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"],
        env="CRAWLER_PLATFORMS"
    )


class SecuritySettings(BaseSettings):
    """安全配置"""
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    allowed_origins: List[str] = Field(default=["http://localhost:5173"], env="ALLOWED_ORIGINS")
    rate_limit: str = Field(default="100/minute", env="RATE_LIMIT")


class AppSettings(BaseSettings):
    """应用主配置"""
    env: Environment = Field(default=Environment.DEVELOPMENT, env="APP_ENV")
    debug: bool = Field(default=False, env="APP_DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    crawler: CrawlerSettings = CrawlerSettings()
    security: SecuritySettings = SecuritySettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = AppSettings()
```

### 2.4 API 网关增强

```python
# api/middleware.py
"""API 中间件 - 认证、限流、日志"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import hashlib
import hmac
from collections import defaultdict
from datetime import datetime


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API 限流中间件 - 令牌桶算法"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()

        # 清理过期记录
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if now - t < self.window_seconds
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too Many Requests",
                    "retry_after": self.window_seconds,
                    "limit": self.max_requests,
                }
            )

        self.requests[client_ip].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_requests - len(self.requests[client_ip])
        )
        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件"""

    WHITELIST_PATHS = {"/health", "/docs", "/openapi.json", "/api/v1/auth/login"}

    def __init__(self, app, api_keys: set):
        super().__init__(app)
        self.api_keys = api_keys

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.WHITELIST_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in self.api_keys:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "client_ip": request.client.host,
        }
        # 使用结构化日志输出
        import structlog
        logger = structlog.get_logger()
        logger.info("api_request", **log_data)

        response.headers["X-Process-Time"] = str(process_time)
        return response
```

---

## 3. 性能优化方案

### 3.1 数据库优化

#### 3.1.1 索引优化

```sql
-- 内容表索引
CREATE INDEX idx_content_platform_created ON content(platform, created_at);
CREATE INDEX idx_content_keyword ON content(keyword);
CREATE INDEX idx_content_note_id ON content(note_id);
CREATE INDEX idx_content_user_id ON content(user_id);

-- 评论表索引
CREATE INDEX idx_comment_note_id ON comment(note_id);
CREATE INDEX idx_comment_created ON comment(created_at);
CREATE INDEX idx_comment_parent ON comment(parent_comment_id);

-- 创作者表索引
CREATE INDEX idx_creator_platform ON creator(platform);
CREATE INDEX idx_creator_user_id ON creator(user_id);
CREATE UNIQUE INDEX idx_creator_platform_user ON creator(platform, user_id);
```

#### 3.1.2 读写分离

```python
# database/connection.py
"""数据库读写分离"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


class DatabaseManager:
    """数据库管理器 - 支持读写分离"""

    def __init__(self, write_url: str, read_urls: list[str]):
        # 写库（主库）
        self.write_engine = create_async_engine(
            write_url,
            pool_size=20,
            max_overflow=10,
            pool_recycle=3600,
            echo=False,
        )

        # 读库（从库）- 轮询负载均衡
        self.read_engines = [
            create_async_engine(
                url,
                pool_size=30,
                max_overflow=20,
                pool_recycle=3600,
                echo=False,
            )
            for url in read_urls
        ]
        self._read_index = 0

    def _get_read_engine(self):
        """轮询选择读库"""
        engine = self.read_engines[self._read_index % len(self.read_engines)]
        self._read_index += 1
        return engine

    def get_write_session(self) -> AsyncSession:
        Session = sessionmaker(self.write_engine, class_=AsyncSession, expire_on_commit=False)
        return Session()

    def get_read_session(self) -> AsyncSession:
        engine = self._get_read_engine()
        Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return Session()
```

#### 3.1.3 分表策略

```python
# database/sharding.py
"""按月分表策略"""

from datetime import datetime
from sqlalchemy import Table, MetaData


class MonthlySharding:
    """按月自动分表"""

    def __init__(self, base_table_name: str, metadata: MetaData):
        self.base_table_name = base_table_name
        self.metadata = metadata
        self._tables = {}

    def get_table(self, date: datetime = None) -> Table:
        if date is None:
            date = datetime.now()
        suffix = date.strftime("%Y%m")
        table_name = f"{self.base_table_name}_{suffix}"

        if table_name not in self._tables:
            base_table = self.metadata.tables[self.base_table_name]
            new_table = base_table.tometadata(
                self.metadata, name=table_name
            )
            self._tables[table_name] = new_table

        return self._tables[table_name]

    def get_tables_for_range(self, start: datetime, end: datetime) -> list[Table]:
        """获取时间范围内的所有分表"""
        tables = []
        current = start.replace(day=1)
        while current <= end:
            tables.append(self.get_table(current))
            month = current.month + 1
            year = current.year
            if month > 12:
                month = 1
                year += 1
            current = current.replace(year=year, month=month)
        return tables
```

### 3.2 多级缓存

```python
# cache/manager.py
"""多级缓存管理器"""

import json
import hashlib
from typing import Optional, Any
from functools import wraps
import redis.asyncio as redis
from cachetools import TTLCache


class CacheManager:
    """L1(内存) + L2(Redis) 多级缓存"""

    def __init__(self, redis_url: str, l1_maxsize: int = 1000, l1_ttl: int = 60):
        self.l1_cache = TTLCache(maxsize=l1_maxsize, ttl=l1_ttl)
        self.redis = redis.from_url(redis_url)
        self.default_ttl = 300  # Redis 默认 5 分钟

    async def get(self, key: str) -> Optional[Any]:
        # L1: 内存缓存
        if key in self.l1_cache:
            return self.l1_cache[key]

        # L2: Redis 缓存
        value = await self.redis.get(key)
        if value:
            data = json.loads(value)
            self.l1_cache[key] = data  # 回填 L1
            return data

        return None

    async def set(self, key: str, value: Any, ttl: int = None):
        ttl = ttl or self.default_ttl
        serialized = json.dumps(value, ensure_ascii=False, default=str)

        # 同时写入 L1 和 L2
        self.l1_cache[key] = value
        await self.redis.setex(key, ttl, serialized)

    async def delete(self, key: str):
        self.l1_cache.pop(key, None)
        await self.redis.delete(key)

    async def clear_pattern(self, pattern: str):
        """按模式清除缓存"""
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)
        # 清除 L1
        self.l1_cache.clear()


def cached(key_prefix: str, ttl: int = 300):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hashlib.md5(str(args) + str(kwargs)).hexdigest()[:8]}"
            cache_mgr = kwargs.get("cache") or getattr(args[0], "cache", None)

            if cache_mgr:
                cached_value = await cache_mgr.get(cache_key)
                if cached_value is not None:
                    return cached_value

            result = await func(*args, **kwargs)

            if cache_mgr and result is not None:
                await cache_mgr.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
```

### 3.3 异步优化

```python
# crawler/async_pool.py
"""异步爬取连接池"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext


class BrowserPool:
    """浏览器实例池 - 复用浏览器上下文"""

    def __init__(self, max_size: int = 5, headless: bool = True):
        self.max_size = max_size
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._contexts: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)
        self._playwright = None

    async def init(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-first-run",
            ]
        )
        # 预创建上下文
        for _ in range(self.max_size):
            ctx = await self._create_context()
            await self._contexts.put(ctx)

    async def _create_context(self) -> BrowserContext:
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        # 注入反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = { runtime: {} };
        """)
        return context

    @asynccontextmanager
    async def acquire(self):
        async with self._semaphore:
            context = await self._contexts.get()
            try:
                yield context
            finally:
                # 清理 cookies 后归还
                await context.clear_cookies()
                await self._contexts.put(context)

    async def close(self):
        while not self._contexts.empty():
            ctx = await self._contexts.get()
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
```

---

## 4. 反爬增强方案

### 4.1 浏览器指纹管理

```python
# anti_detect/fingerprint.py
"""浏览器指纹随机化"""

import random
import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class BrowserFingerprint:
    """浏览器指纹"""
    user_agent: str = ""
    viewport_width: int = 1920
    viewport_height: int = 1080
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0
    platform: str = "MacIntel"
    language: str = "zh-CN"
    languages: List[str] = field(default_factory=lambda: ["zh-CN", "zh", "en"])
    timezone: str = "Asia/Shanghai"
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    canvas_hash: str = ""


class FingerprintGenerator:
    """指纹生成器"""

    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    VIEWPORTS = [
        (1920, 1080), (1366, 768), (1536, 864),
        (1440, 900), (1280, 720), (2560, 1440),
    ]

    WEBGL_CONFIGS = [
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA GeForce GTX 1080)"),
        ("Google Inc. (Intel)", "ANGLE (Intel UHD Graphics 630)"),
        ("Google Inc. (AMD)", "ANGLE (AMD Radeon Pro 5500M)"),
    ]

    @classmethod
    def generate(cls) -> BrowserFingerprint:
        ua = random.choice(cls.USER_AGENTS)
        vw, vh = random.choice(cls.VIEWPORTS)
        webgl = random.choice(cls.WEBGL_CONFIGS)

        platform = "MacIntel" if "Mac" in ua else "Win32" if "Windows" in ua else "Linux x86_64"

        return BrowserFingerprint(
            user_agent=ua,
            viewport_width=vw,
            viewport_height=vh,
            screen_width=vw + random.randint(0, 200),
            screen_height=vh + random.randint(0, 150),
            color_depth=random.choice([24, 32]),
            pixel_ratio=random.choice([1.0, 1.25, 1.5, 2.0]),
            platform=platform,
            webgl_vendor=webgl[0],
            webgl_renderer=webgl[1],
        )

    @classmethod
    def to_init_script(cls, fp: BrowserFingerprint) -> str:
        return f"""
        // 覆盖 navigator 属性
        Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
        Object.defineProperty(navigator, 'platform', {{get: () => '{fp.platform}'}});
        Object.defineProperty(navigator, 'language', {{get: () => '{fp.language}'}});
        Object.defineProperty(navigator, 'languages', {{get: () => {json.dumps(fp.languages)}}});
        Object.defineProperty(screen, 'width', {{get: () => {fp.screen_width}}});
        Object.defineProperty(screen, 'height', {{get: () => {fp.screen_height}}});
        Object.defineProperty(screen, 'colorDepth', {{get: () => {fp.color_depth}}});
        window.devicePixelRatio = {fp.pixel_ratio};

        // 覆盖 WebGL
        const origGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return '{fp.webgl_vendor}';
            if (param === 37446) return '{fp.webgl_renderer}';
            return origGetParameter.call(this, param);
        }};

        // Chrome 对象
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
        }};

        // 插件伪装
        Object.defineProperty(navigator, 'plugins', {{
            get: () => {{
                const plugins = [
                    {{name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'}},
                    {{name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'}},
                    {{name: 'Native Client', filename: 'internal-nacl-plugin'}},
                ];
                plugins.length = 3;
                return plugins;
            }}
        }});
        """
```

### 4.2 智能限速器

```python
# anti_detect/rate_limiter.py
"""智能限速 - 模拟人类行为模式"""

import asyncio
import random
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """限速配置"""
    min_interval: float = 2.0       # 最小请求间隔（秒）
    max_interval: float = 8.0       # 最大请求间隔（秒）
    burst_probability: float = 0.1  # 快速连续请求的概率
    pause_probability: float = 0.05 # 长时间停顿的概率
    pause_duration: tuple = (30, 120)  # 停顿时长范围（秒）
    hourly_limit: int = 200         # 每小时最大请求数
    daily_limit: int = 2000         # 每天最大请求数


class SmartRateLimiter:
    """智能限速器 - 模拟人类浏览节奏"""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._last_request_time = 0
        self._hourly_requests = deque()
        self._daily_requests = deque()
        self._request_count = 0

    def _clean_old_records(self):
        now = time.time()
        # 清理超过1小时的记录
        while self._hourly_requests and now - self._hourly_requests[0] > 3600:
            self._hourly_requests.popleft()
        # 清理超过1天的记录
        while self._daily_requests and now - self._daily_requests[0] > 86400:
            self._daily_requests.popleft()

    async def wait(self):
        """等待到合适的时机再发送请求"""
        self._clean_old_records()

        # 检查频率限制
        if len(self._hourly_requests) >= self.config.hourly_limit:
            wait_time = 3600 - (time.time() - self._hourly_requests[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        if len(self._daily_requests) >= self.config.daily_limit:
            wait_time = 86400 - (time.time() - self._daily_requests[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        # 计算等待时间
        now = time.time()
        elapsed = now - self._last_request_time

        # 模拟人类行为
        if random.random() < self.config.pause_probability:
            # 偶尔长时间停顿（模拟离开、思考）
            pause = random.uniform(*self.config.pause_duration)
            await asyncio.sleep(pause)
        elif random.random() < self.config.burst_probability:
            # 偶尔快速连续请求（模拟快速浏览）
            delay = random.uniform(0.5, self.config.min_interval)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        else:
            # 正常的随机间隔
            delay = random.uniform(self.config.min_interval, self.config.max_interval)
            # 添加高斯噪声使间隔更自然
            delay += random.gauss(0, 0.5)
            delay = max(self.config.min_interval, delay)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)

        # 记录请求
        now = time.time()
        self._last_request_time = now
        self._hourly_requests.append(now)
        self._daily_requests.append(now)
        self._request_count += 1
```

### 4.3 人类行为模拟

```python
# anti_detect/human_behavior.py
"""人类行为模拟器"""

import asyncio
import random
import math
from playwright.async_api import Page


class HumanBehaviorSimulator:
    """模拟真实用户操作行为"""

    @staticmethod
    async def human_scroll(page: Page, direction: str = "down", distance: int = None):
        """模拟人类滚动 - 非线性速度"""
        if distance is None:
            distance = random.randint(300, 800)

        steps = random.randint(5, 15)
        total_scrolled = 0

        for i in range(steps):
            # 非线性滚动：开始快、中间慢、结束快
            progress = i / steps
            speed_factor = 0.5 + math.sin(progress * math.pi) * 0.5
            step_distance = int(distance / steps * (0.5 + speed_factor))

            if direction == "down":
                await page.mouse.wheel(0, step_distance)
            else:
                await page.mouse.wheel(0, -step_distance)

            total_scrolled += step_distance
            await asyncio.sleep(random.uniform(0.02, 0.08))

        # 滚动后的短暂停顿
        await asyncio.sleep(random.uniform(0.3, 1.0))

    @staticmethod
    async def human_move_to(page: Page, x: int, y: int):
        """模拟人类鼠标移动 - 贝塞尔曲线路径"""
        current = await page.evaluate("() => ({x: window.mouseX || 0, y: window.mouseY || 0})")
        start_x, start_y = current.get("x", 0), current.get("y", 0)

        # 生成贝塞尔曲线控制点
        cp1_x = start_x + (x - start_x) * random.uniform(0.2, 0.4)
        cp1_y = start_y + random.randint(-100, 100)
        cp2_x = start_x + (x - start_x) * random.uniform(0.6, 0.8)
        cp2_y = y + random.randint(-100, 100)

        steps = random.randint(20, 40)
        for i in range(steps + 1):
            t = i / steps
            # 三次贝塞尔曲线
            px = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * x
            py = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * y
            await page.mouse.move(px, py)
            # 速度变化：中间快两端慢
            delay = 0.005 + 0.02 * (1 - math.sin(t * math.pi))
            await asyncio.sleep(delay)

    @staticmethod
    async def human_click(page: Page, selector: str):
        """模拟人类点击"""
        element = await page.query_selector(selector)
        if not element:
            return

        box = await element.bounding_box()
        if not box:
            return

        # 点击位置随机偏移（不总是点正中间）
        x = box["x"] + box["width"] * random.uniform(0.2, 0.8)
        y = box["y"] + box["height"] * random.uniform(0.2, 0.8)

        await HumanBehaviorSimulator.human_move_to(page, int(x), int(y))
        await asyncio.sleep(random.uniform(0.05, 0.15))  # 移动到位后的犹豫
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.12))   # 按下时长
        await page.mouse.up()
        await asyncio.sleep(random.uniform(0.1, 0.3))     # 点击后停顿

    @staticmethod
    async def human_type(page: Page, selector: str, text: str):
        """模拟人类打字 - 变速输入"""
        await HumanBehaviorSimulator.human_click(page, selector)
        await asyncio.sleep(random.uniform(0.3, 0.8))  # 开始打字前的停顿

        for char in text:
            await page.keyboard.press(char)
            # 打字速度变化
            if char == " ":
                delay = random.uniform(0.1, 0.3)  # 空格后稍微停顿
            elif random.random() < 0.05:
                delay = random.uniform(0.3, 0.8)  # 偶尔的较长停顿（思考）
            else:
                delay = random.uniform(0.05, 0.15)  # 正常打字速度
            await asyncio.sleep(delay)

    @staticmethod
    async def random_browse(page: Page, duration: float = 5.0):
        """随机浏览行为 - 模拟用户阅读页面"""
        end_time = asyncio.get_event_loop().time() + duration

        while asyncio.get_event_loop().time() < end_time:
            action = random.choices(
                ["scroll", "move", "pause", "read"],
                weights=[0.3, 0.2, 0.2, 0.3],
                k=1
            )[0]

            if action == "scroll":
                direction = random.choice(["down", "down", "down", "up"])  # 更偏向向下
                await HumanBehaviorSimulator.human_scroll(page, direction)
            elif action == "move":
                x = random.randint(100, 1200)
                y = random.randint(100, 800)
                await HumanBehaviorSimulator.human_move_to(page, x, y)
            elif action == "pause":
                await asyncio.sleep(random.uniform(1.0, 3.0))
            elif action == "read":
                # 模拟阅读：小幅滚动+长停顿
                await HumanBehaviorSimulator.human_scroll(page, "down", random.randint(50, 200))
                await asyncio.sleep(random.uniform(2.0, 5.0))
```

### 4.4 账号健康管理

```python
# anti_detect/account_health.py
"""账号健康度管理"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class AccountStatus(Enum):
    ACTIVE = "active"
    COOLING = "cooling"      # 冷却中
    WARNING = "warning"      # 警告
    BANNED = "banned"        # 封禁
    RETIRED = "retired"      # 退役


@dataclass
class AccountHealth:
    """账号健康状态"""
    account_id: str
    platform: str
    status: AccountStatus = AccountStatus.ACTIVE
    total_requests: int = 0
    failed_requests: int = 0
    captcha_count: int = 0
    last_request_time: float = 0
    cooling_until: float = 0
    daily_request_count: int = 0
    daily_reset_time: float = field(default_factory=time.time)
    risk_score: float = 0.0  # 0-100, 越高风险越大

    def record_request(self, success: bool):
        now = time.time()
        # 每日重置
        if now - self.daily_reset_time > 86400:
            self.daily_request_count = 0
            self.daily_reset_time = now

        self.total_requests += 1
        self.daily_request_count += 1
        self.last_request_time = now

        if not success:
            self.failed_requests += 1

        self._update_risk_score()

    def record_captcha(self):
        self.captcha_count += 1
        self.risk_score = min(100, self.risk_score + 15)
        self._maybe_cool_down()

    def _update_risk_score(self):
        # 基于失败率
        if self.total_requests > 10:
            fail_rate = self.failed_requests / self.total_requests
            self.risk_score = max(self.risk_score, fail_rate * 100)

        # 基于日请求量
        if self.daily_request_count > 500:
            self.risk_score = min(100, self.risk_score + 5)

        self._maybe_cool_down()

    def _maybe_cool_down(self):
        if self.risk_score > 70:
            self.status = AccountStatus.COOLING
            self.cooling_until = time.time() + 3600  # 冷却1小时
        elif self.risk_score > 50:
            self.status = AccountStatus.WARNING


class AccountPool:
    """账号池管理"""

    def __init__(self):
        self._accounts: Dict[str, AccountHealth] = {}

    def add_account(self, account_id: str, platform: str):
        key = f"{platform}:{account_id}"
        self._accounts[key] = AccountHealth(account_id=account_id, platform=platform)

    def get_best_account(self, platform: str) -> Optional[AccountHealth]:
        """获取最佳可用账号（风险最低）"""
        now = time.time()
        candidates = []

        for key, health in self._accounts.items():
            if not key.startswith(f"{platform}:"):
                continue
            if health.status == AccountStatus.BANNED:
                continue
            if health.status == AccountStatus.COOLING and now < health.cooling_until:
                continue
            # 冷却结束，恢复状态
            if health.status == AccountStatus.COOLING and now >= health.cooling_until:
                health.status = AccountStatus.ACTIVE
                health.risk_score = max(0, health.risk_score - 20)

            candidates.append(health)

        if not candidates:
            return None

        # 选择风险最低的
        return min(candidates, key=lambda a: a.risk_score)
```

---

## 5. 前端交互优化

### 5.1 状态管理升级

```typescript
// frontend/src/stores/crawlerStore.ts
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface CrawlTask {
  id: string
  platform: string
  keyword: string
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed'
  progress: number
  totalItems: number
  crawledItems: number
  startTime: string
  estimatedEndTime?: string
  error?: string
}

interface CrawlerState {
  tasks: CrawlTask[]
  activePlatform: string
  isConnected: boolean

  // Actions
  addTask: (task: CrawlTask) => void
  updateTask: (id: string, updates: Partial<CrawlTask>) => void
  removeTask: (id: string) => void
  setActivePlatform: (platform: string) => void
  setConnected: (connected: boolean) => void
}

export const useCrawlerStore = create<CrawlerState>()(
  devtools(
    persist(
      (set) => ({
        tasks: [],
        activePlatform: 'xhs',
        isConnected: false,

        addTask: (task) =>
          set((state) => ({ tasks: [...state.tasks, task] })),

        updateTask: (id, updates) =>
          set((state) => ({
            tasks: state.tasks.map((t) =>
              t.id === id ? { ...t, ...updates } : t
            ),
          })),

        removeTask: (id) =>
          set((state) => ({
            tasks: state.tasks.filter((t) => t.id !== id),
          })),

        setActivePlatform: (platform) =>
          set({ activePlatform: platform }),

        setConnected: (connected) =>
          set({ isConnected: connected }),
      }),
      { name: 'crawler-store' }
    )
  )
)
```

### 5.2 实时进度 WebSocket

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react'
import { useCrawlerStore } from '../stores/crawlerStore'

interface WSMessage {
  type: 'task_progress' | 'task_status' | 'system_alert' | 'heartbeat'
  data: any
}

export function useCrawlerWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<number>()
  const { updateTask, setConnected } = useCrawlerStore()

  const connect = useCallback(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/crawler`)

    ws.onopen = () => {
      setConnected(true)
      console.log('[WS] Connected')
    }

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data)

      switch (msg.type) {
        case 'task_progress':
          updateTask(msg.data.task_id, {
            progress: msg.data.progress,
            crawledItems: msg.data.crawled_items,
            estimatedEndTime: msg.data.estimated_end_time,
          })
          break

        case 'task_status':
          updateTask(msg.data.task_id, {
            status: msg.data.status,
            error: msg.data.error,
          })
          break

        case 'system_alert':
          // 系统通知
          console.warn('[System Alert]', msg.data.message)
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // 自动重连，指数退避
      reconnectTimer.current = window.setTimeout(() => {
        connect()
      }, 3000)
    }

    wsRef.current = ws
  }, [updateTask, setConnected])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((type: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }))
    }
  }, [])

  return { sendMessage }
}
```

### 5.3 数据可视化仪表盘

```typescript
// frontend/src/components/Dashboard.tsx
import React from 'react'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts'

interface DashboardProps {
  stats: {
    totalCrawled: number
    todayCrawled: number
    successRate: number
    activeTasks: number
    platformDistribution: { name: string; value: number }[]
    dailyTrend: { date: string; count: number; success: number }[]
  }
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658']

export const Dashboard: React.FC<DashboardProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-6">
      {/* 统计卡片 */}
      <StatCard title="总采集量" value={stats.totalCrawled.toLocaleString()} trend="+12%" />
      <StatCard title="今日采集" value={stats.todayCrawled.toLocaleString()} trend="+5%" />
      <StatCard title="成功率" value={`${stats.successRate}%`} trend="+2%" />
      <StatCard title="活跃任务" value={stats.activeTasks.toString()} />

      {/* 采集趋势图 */}
      <div className="col-span-1 md:col-span-2 lg:col-span-3 bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">采集趋势</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={stats.dailyTrend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="count" stroke="#8884d8" fill="#8884d8" fillOpacity={0.3} name="总量" />
            <Area type="monotone" dataKey="success" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.3} name="成功" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 平台分布饼图 */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">平台分布</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={stats.platformDistribution}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={5}
              dataKey="value"
            >
              {stats.platformDistribution.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const StatCard: React.FC<{title: string; value: string; trend?: string}> = ({ title, value, trend }) => (
  <div className="bg-white rounded-lg shadow p-4">
    <p className="text-sm text-gray-500">{title}</p>
    <p className="text-2xl font-bold mt-1">{value}</p>
    {trend && <p className="text-sm text-green-500 mt-1">{trend}</p>}
  </div>
)
```

---

## 6. 监控与可观测性

### 6.1 Prometheus 指标采集

```python
# monitoring/metrics.py
"""Prometheus 指标定义"""

from prometheus_client import Counter, Histogram, Gauge, Info


# 爬取指标
CRAWL_REQUESTS_TOTAL = Counter(
    "crawl_requests_total",
    "Total crawl requests",
    ["platform", "type", "status"]
)

CRAWL_DURATION = Histogram(
    "crawl_duration_seconds",
    "Crawl request duration",
    ["platform", "type"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)

CRAWL_ITEMS_SCRAPED = Counter(
    "crawl_items_scraped_total",
    "Total items scraped",
    ["platform", "content_type"]
)

# 系统指标
ACTIVE_WORKERS = Gauge(
    "active_workers",
    "Number of active crawler workers"
)

TASK_QUEUE_SIZE = Gauge(
    "task_queue_size",
    "Number of tasks in queue",
    ["queue_name"]
)

PROXY_POOL_SIZE = Gauge(
    "proxy_pool_size",
    "Number of available proxies",
    ["provider", "status"]
)

ACCOUNT_POOL_SIZE = Gauge(
    "account_pool_size",
    "Number of available accounts",
    ["platform", "status"]
)

# 错误指标
ERROR_TOTAL = Counter(
    "error_total",
    "Total errors",
    ["platform", "error_type"]
)

CAPTCHA_TOTAL = Counter(
    "captcha_total",
    "Total captcha encounters",
    ["platform"]
)

# 数据库指标
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation", "table"]
)

DB_CONNECTION_POOL = Gauge(
    "db_connection_pool",
    "Database connection pool status",
    ["status"]  # active, idle, overflow
)

# 系统信息
SYSTEM_INFO = Info(
    "mediacrawler",
    "MediaCrawler system information"
)
```

### 6.2 Grafana 仪表盘配置

```json
{
  "dashboard": {
    "title": "MediaCrawler Monitor",
    "panels": [
      {
        "title": "爬取成功率",
        "type": "gauge",
        "targets": [{
          "expr": "sum(rate(crawl_requests_total{status='success'}[5m])) / sum(rate(crawl_requests_total[5m])) * 100"
        }],
        "thresholds": [
          {"value": 90, "color": "green"},
          {"value": 70, "color": "yellow"},
          {"value": 0, "color": "red"}
        ]
      },
      {
        "title": "各平台 QPS",
        "type": "graph",
        "targets": [{
          "expr": "sum(rate(crawl_requests_total[1m])) by (platform)",
          "legendFormat": "{{platform}}"
        }]
      },
      {
        "title": "请求延迟分布",
        "type": "heatmap",
        "targets": [{
          "expr": "sum(rate(crawl_duration_seconds_bucket[5m])) by (le, platform)"
        }]
      },
      {
        "title": "代理池状态",
        "type": "stat",
        "targets": [{
          "expr": "proxy_pool_size{status='available'}"
        }]
      },
      {
        "title": "错误趋势",
        "type": "graph",
        "targets": [{
          "expr": "sum(rate(error_total[5m])) by (error_type)",
          "legendFormat": "{{error_type}}"
        }]
      },
      {
        "title": "验证码触发",
        "type": "graph",
        "targets": [{
          "expr": "sum(rate(captcha_total[1h])) by (platform)"
        }]
      }
    ]
  }
}
```

### 6.3 Sentry 错误追踪集成

```python
# monitoring/sentry_setup.py
"""Sentry 错误追踪配置"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration


def init_sentry(dsn: str, environment: str = "production"):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.2,  # 20% 的请求做性能追踪
        profiles_sample_rate=0.1,  # 10% 的请求做性能分析
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        # 过滤敏感数据
        before_send=_filter_sensitive_data,
        # 自定义标签
        release="mediacrawler@1.0.0",
    )


def _filter_sensitive_data(event, hint):
    """过滤敏感数据"""
    if "request" in event:
        headers = event["request"].get("headers", {})
        # 移除敏感 header
        for key in ["Cookie", "Authorization", "X-API-Key"]:
            headers.pop(key, None)
    return event


# 使用示例
def capture_crawl_error(platform: str, error: Exception, context: dict = None):
    """捕获爬取错误"""
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("platform", platform)
        scope.set_tag("error_type", type(error).__name__)
        if context:
            scope.set_context("crawl_context", context)
        sentry_sdk.capture_exception(error)
```

### 6.4 告警规则

```yaml
# monitoring/alert_rules.yml
groups:
  - name: MediaCrawler Alerts
    rules:
      # 爬取成功率低于 80%
      - alert: LowCrawlSuccessRate
        expr: |
          sum(rate(crawl_requests_total{status="success"}[10m]))
          / sum(rate(crawl_requests_total[10m])) < 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "爬取成功率低于 80%"
          description: "当前成功率: {{ $value | humanizePercentage }}"

      # 验证码频率过高
      - alert: HighCaptchaRate
        expr: sum(rate(captcha_total[30m])) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "验证码触发频率过高"
          description: "30 分钟内触发 {{ $value }} 次验证码"

      # 代理池可用数量过低
      - alert: LowProxyPoolSize
        expr: proxy_pool_size{status="available"} < 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "可用代理数量不足"
          description: "当前可用代理: {{ $value }}"

      # Worker 异常退出
      - alert: WorkerDown
        expr: active_workers < 2
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "活跃 Worker 数量不足"
          description: "当前活跃 Worker: {{ $value }}"

      # 任务队列积压
      - alert: TaskQueueBacklog
        expr: task_queue_size > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "任务队列积压"
          description: "队列 {{ $labels.queue_name }} 积压 {{ $value }} 个任务"

      # 数据库连接池耗尽
      - alert: DBConnectionPoolExhausted
        expr: db_connection_pool{status="active"} / (db_connection_pool{status="active"} + db_connection_pool{status="idle"}) > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接池即将耗尽"
```

---

## 7. 实施路线图

### 第一阶段：基础加固（2-3 周）

| 任务 | 优先级 | 预估工时 |
|------|--------|---------|
| Pydantic 配置管理重构 | P0 | 3天 |
| 数据库索引优化 | P0 | 1天 |
| API 认证 + 限流中间件 | P0 | 2天 |
| 结构化日志 | P1 | 1天 |
| Docker 容器化 | P1 | 2天 |
| 单元测试补充（核心模块） | P1 | 3天 |

### 第二阶段：反爬增强（2-3 周）

| 任务 | 优先级 | 预估工时 |
|------|--------|---------|
| 浏览器指纹随机化 | P0 | 3天 |
| 智能限速器 | P0 | 2天 |
| 人类行为模拟器 | P0 | 3天 |
| 账号健康度管理 | P1 | 2天 |
| 代理质量评估增强 | P1 | 2天 |

### 第三阶段：分布式升级（3-4 周）

| 任务 | 优先级 | 预估工时 |
|------|--------|---------|
| Celery 分布式任务队列 | P0 | 5天 |
| Redis 多级缓存 | P0 | 3天 |
| 数据库读写分离 | P1 | 3天 |
| 分表策略实现 | P1 | 2天 |
| 浏览器实例池 | P1 | 2天 |
| WebSocket 实时通信 | P1 | 3天 |

### 第四阶段：前端升级 + 监控（2-3 周）

| 任务 | 优先级 | 预估工时 |
|------|--------|---------|
| Zustand 状态管理迁移 | P0 | 2天 |
| 数据可视化仪表盘 | P0 | 3天 |
| Prometheus 指标采集 | P0 | 2天 |
| Grafana 仪表盘 | P1 | 2天 |
| Sentry 错误追踪 | P1 | 1天 |
| 告警规则配置 | P1 | 1天 |

---

## 技术栈对比总结

### 后端

| 组件 | 当前 | 升级目标 |
|------|------|----------|
| 任务队列 | asyncio 单进程 | Celery + Redis |
| 缓存 | 无 | L1内存 + L2 Redis 多级缓存 |
| 配置管理 | Python模块 | Pydantic Settings |
| 日志 | print/logging | 结构化 JSON 日志 (structlog) |
| 监控 | 无 | Prometheus + Grafana |
| 错误追踪 | 无 | Sentry |

### 前端

| 组件 | 当前 | 升级目标 |
|------|------|----------|
| 框架 | React + TypeScript | React + TypeScript (保持) |
| 构建 | Vite | Vite (保持) |
| 样式 | TailwindCSS | TailwindCSS (保持) |
| 组件库 | Radix UI | Radix UI + 扩展 |
| 状态管理 | useState | Zustand |
| 数据请求 | 自定义hooks | TanStack Query |
| 图表 | 无 | Recharts |
| 表格 | 基础 | TanStack Table |

### 运维

| 组件 | 当前 | 升级目标 |
|------|------|----------|
| 容器化 | 无 | Docker + Docker Compose |
| 部署 | 手动 | CI/CD 自动部署 |
| 监控 | 无 | Prometheus + Grafana |
| 日志聚合 | 文件 | ELK Stack (可选) |
| 反向代理 | 无 | Nginx |

---

> 本文档为 MediaCrawler 商业化优化的完整技术方案，排除了支付系统和法律合规模块。
> 建议按阶段逐步推进，优先完成基础加固和反爬增强。
