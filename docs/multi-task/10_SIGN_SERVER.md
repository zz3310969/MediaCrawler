# 10. 签名服务集成文档

> 模块: SignSrv 对接  
> Phase: 4  
> 预估工期: 2 天  
> 相关仓库: `MediaCrawlerPro-SignSrv`

---

## 一、模块职责

签名服务集成负责：
1. **接口对接**：调用 SignSrv 获取请求签名
2. **Client 改造**：XHS/Douyin/Bilibili/Zhihu 客户端支持远程签名
3. **降级策略**：签名服务不可用时的处理

---

## 二、SignSrv 接口概览

### 2.1 服务信息

| 项目 | 值 |
|------|-----|
| 仓库 | `MediaCrawlerPro-SignSrv` |
| 默认端口 | 8989 |
| 协议 | HTTP/JSON |

### 2.2 API 列表

| 平台 | 接口 | 方法 | 说明 |
|------|------|------|------|
| 小红书 | `/api/xhs/sign` | POST | XHS 请求签名 |
| 抖音 | `/api/douyin/sign` | POST | Douyin 请求签名 |
| B站 | `/api/bilibili/sign` | POST | Bilibili 请求签名 |
| 知乎 | `/api/zhihu/sign` | POST | Zhihu 请求签名 |

### 2.3 请求/响应格式

#### 小红书签名

```python
# 请求
POST /api/xhs/sign
{
    "uri": "/api/sns/web/v1/search/notes",
    "data": "",  # POST body（可选）
    "cookies": "...",  # 登录态 cookie
    "a1": "xxx"  # a1 参数
}

# 响应
{
    "code": 0,
    "msg": "success",
    "data": {
        "x-s": "xxx",
        "x-t": "xxx",
        "x-s-common": "xxx"
    }
}
```

#### 抖音签名

```python
# 请求
POST /api/douyin/sign
{
    "url": "https://www.douyin.com/aweme/v1/web/search/item/",
    "user_agent": "..."
}

# 响应
{
    "code": 0,
    "msg": "success",
    "data": {
        "a_bogus": "xxx",
        "ttwid": "xxx"
    }
}
```

---

## 三、签名客户端封装

### 3.1 基础客户端 (`api/services/sign_client.py`)

```python
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SignConfig:
    """签名服务配置"""
    enabled: bool = False
    url: str = "http://localhost:8989"
    timeout: float = 10.0
    retry_count: int = 2


class SignError(Exception):
    """签名错误"""
    pass


class SignClient:
    """签名服务客户端"""
    
    def __init__(self, config: SignConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self._config.url,
            timeout=self._config.timeout
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    @property
    def enabled(self) -> bool:
        return self._config.enabled
    
    async def _request(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送签名请求"""
        if not self._client:
            raise SignError("Client not initialized")
        
        for attempt in range(self._config.retry_count + 1):
            try:
                response = await self._client.post(path, json=data)
                response.raise_for_status()
                
                result = response.json()
                if result.get("code") != 0:
                    raise SignError(f"Sign error: {result.get('msg')}")
                
                return result.get("data", {})
            
            except httpx.HTTPError as e:
                logger.warning(f"Sign request failed (attempt {attempt + 1}): {e}")
                if attempt == self._config.retry_count:
                    raise SignError(f"Sign request failed after {attempt + 1} attempts")
    
    # ========== 平台签名方法 ==========
    
    async def sign_xhs(
        self,
        uri: str,
        data: str = "",
        cookies: str = "",
        a1: str = ""
    ) -> Dict[str, str]:
        """小红书签名"""
        return await self._request("/api/xhs/sign", {
            "uri": uri,
            "data": data,
            "cookies": cookies,
            "a1": a1
        })
    
    async def sign_douyin(
        self,
        url: str,
        user_agent: str = ""
    ) -> Dict[str, str]:
        """抖音签名"""
        return await self._request("/api/douyin/sign", {
            "url": url,
            "user_agent": user_agent
        })
    
    async def sign_bilibili(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, str]:
        """B站签名"""
        return await self._request("/api/bilibili/sign", {
            "params": params
        })
    
    async def sign_zhihu(
        self,
        url: str,
        cookies: str = ""
    ) -> Dict[str, str]:
        """知乎签名"""
        return await self._request("/api/zhihu/sign", {
            "url": url,
            "cookies": cookies
        })
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._client:
                return False
            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception:
            return False


# 全局实例
_sign_client: Optional[SignClient] = None


def get_sign_client() -> Optional[SignClient]:
    return _sign_client


async def init_sign_client(config: SignConfig) -> SignClient:
    global _sign_client
    _sign_client = SignClient(config)
    await _sign_client.__aenter__()
    return _sign_client


async def close_sign_client():
    global _sign_client
    if _sign_client:
        await _sign_client.__aexit__(None, None, None)
        _sign_client = None
```

---

## 四、平台客户端改造

### 4.1 XHS 客户端改造示例

```python
# media_platform/xhs/client.py

from typing import Optional, Dict
from api.services.sign_client import get_sign_client, SignError


class XHSClient:
    """小红书客户端"""
    
    def __init__(
        self,
        cookies: str,
        user_agent: str,
        use_sign_server: bool = True  # 新增参数
    ):
        self._cookies = cookies
        self._user_agent = user_agent
        self._use_sign_server = use_sign_server
        self._a1 = self._extract_a1(cookies)
    
    async def _get_sign_headers(self, uri: str, data: str = "") -> Dict[str, str]:
        """获取签名头"""
        sign_client = get_sign_client()
        
        # 优先使用签名服务
        if self._use_sign_server and sign_client and sign_client.enabled:
            try:
                return await sign_client.sign_xhs(
                    uri=uri,
                    data=data,
                    cookies=self._cookies,
                    a1=self._a1
                )
            except SignError as e:
                logger.warning(f"Sign server failed, fallback to local: {e}")
        
        # 降级到本地签名（需要 Playwright）
        return await self._local_sign(uri, data)
    
    async def _local_sign(self, uri: str, data: str) -> Dict[str, str]:
        """本地签名（Playwright）"""
        # 原有的 Playwright 签名逻辑
        # ...
        pass
    
    async def search_notes(self, keyword: str, **kwargs) -> Dict:
        """搜索笔记"""
        uri = "/api/sns/web/v1/search/notes"
        params = {"keyword": keyword, **kwargs}
        
        # 获取签名
        sign_headers = await self._get_sign_headers(uri)
        
        # 发送请求
        headers = {
            "User-Agent": self._user_agent,
            "Cookie": self._cookies,
            **sign_headers
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://edith.xiaohongshu.com{uri}",
                params=params,
                headers=headers
            )
            return response.json()
```

### 4.2 配置集成

```python
# config/sign_server.py

from pydantic import BaseSettings


class SignServerSettings(BaseSettings):
    """签名服务配置"""
    
    sign_server_enabled: bool = True
    sign_server_url: str = "http://localhost:8989"
    sign_server_timeout: float = 10.0
    sign_server_retry: int = 2
    
    # 降级策略
    sign_fallback_enabled: bool = True  # 签名服务失败时是否降级到本地
    
    class Config:
        env_prefix = "MC_"
```

### 4.3 启动时初始化

```python
# api/main.py

from contextlib import asynccontextmanager
from api.services.sign_client import init_sign_client, close_sign_client, SignConfig
from config.sign_server import SignServerSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = SignServerSettings()
    
    # 初始化签名客户端
    if settings.sign_server_enabled:
        config = SignConfig(
            enabled=True,
            url=settings.sign_server_url,
            timeout=settings.sign_server_timeout,
            retry_count=settings.sign_server_retry
        )
        sign_client = await init_sign_client(config)
        
        # 健康检查
        if not await sign_client.health_check():
            logger.warning("Sign server not available")
    
    yield
    
    # 清理
    await close_sign_client()
```

---

## 五、命令行参数支持

### 5.1 main.py 改造

```python
# main.py

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="MediaCrawler")
    
    # ... 现有参数 ...
    
    # 签名服务参数
    parser.add_argument(
        "--sign-server",
        type=str,
        default="http://localhost:8989",
        help="签名服务地址"
    )
    parser.add_argument(
        "--no-sign-server",
        action="store_true",
        help="禁用签名服务（使用本地 Playwright 签名）"
    )
    
    return parser.parse_args()


async def main():
    args = parse_args()
    
    # 配置签名服务
    if not args.no_sign_server:
        from api.services.sign_client import init_sign_client, SignConfig
        
        config = SignConfig(
            enabled=True,
            url=args.sign_server
        )
        await init_sign_client(config)
    
    # ... 运行爬虫 ...
```

---

## 六、测试用例

### 6.1 签名客户端测试

```python
import pytest
from api.services.sign_client import SignClient, SignConfig, SignError


@pytest.fixture
async def sign_client():
    config = SignConfig(
        enabled=True,
        url="http://localhost:8989",
        timeout=5.0
    )
    async with SignClient(config) as client:
        yield client


@pytest.mark.asyncio
async def test_xhs_sign(sign_client):
    """测试小红书签名"""
    result = await sign_client.sign_xhs(
        uri="/api/sns/web/v1/search/notes",
        data="",
        cookies="a1=xxx;",
        a1="xxx"
    )
    
    assert "x-s" in result
    assert "x-t" in result


@pytest.mark.asyncio
async def test_sign_server_unavailable():
    """测试签名服务不可用"""
    config = SignConfig(
        enabled=True,
        url="http://localhost:9999",  # 不存在的服务
        timeout=1.0,
        retry_count=0
    )
    
    async with SignClient(config) as client:
        with pytest.raises(SignError):
            await client.sign_xhs(uri="/test")


@pytest.mark.asyncio
async def test_health_check(sign_client):
    """测试健康检查"""
    result = await sign_client.health_check()
    assert result == True
```

### 6.2 集成测试

```python
@pytest.mark.asyncio
async def test_xhs_search_with_sign_server():
    """测试使用签名服务搜索"""
    from media_platform.xhs.client import XHSClient
    
    client = XHSClient(
        cookies="your_cookies",
        user_agent="your_ua",
        use_sign_server=True
    )
    
    result = await client.search_notes("测试关键词")
    
    assert result.get("code") == 0
```

---

## 七、部署配置

### 7.1 Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  sign-server:
    image: mediacrawler-sign-server:latest
    build:
      context: ../MediaCrawlerPro-SignSrv
    ports:
      - "8989:8989"
    environment:
      - SIGN_MODE=js  # js 或 playwright
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8989/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  api-server:
    image: mediacrawler-api:latest
    depends_on:
      sign-server:
        condition: service_healthy
    environment:
      - MC_SIGN_SERVER_ENABLED=true
      - MC_SIGN_SERVER_URL=http://sign-server:8989
    ports:
      - "8080:8080"

  worker:
    image: mediacrawler-worker:latest
    depends_on:
      - api-server
      - sign-server
    environment:
      - MC_SIGN_SERVER_ENABLED=true
      - MC_SIGN_SERVER_URL=http://sign-server:8989
    deploy:
      replicas: 2
```

### 7.2 环境变量

```bash
# .env

# 签名服务
MC_SIGN_SERVER_ENABLED=true
MC_SIGN_SERVER_URL=http://localhost:8989
MC_SIGN_SERVER_TIMEOUT=10
MC_SIGN_SERVER_RETRY=2

# 降级策略
MC_SIGN_FALLBACK_ENABLED=true
```

---

## 八、监控与告警

### 8.1 指标采集

```python
from prometheus_client import Counter, Histogram

# 签名请求计数
sign_requests_total = Counter(
    "sign_requests_total",
    "Total sign requests",
    ["platform", "status"]
)

# 签名延迟
sign_latency_seconds = Histogram(
    "sign_latency_seconds",
    "Sign request latency",
    ["platform"]
)

# 在 SignClient 中使用
async def _request(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    platform = path.split("/")[2]  # /api/{platform}/sign
    
    with sign_latency_seconds.labels(platform=platform).time():
        try:
            result = await self._do_request(path, data)
            sign_requests_total.labels(platform=platform, status="success").inc()
            return result
        except Exception as e:
            sign_requests_total.labels(platform=platform, status="error").inc()
            raise
```

### 8.2 告警规则（Prometheus）

```yaml
groups:
  - name: sign_server
    rules:
      - alert: SignServerDown
        expr: up{job="sign-server"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Sign server is down"
          
      - alert: SignErrorRateHigh
        expr: rate(sign_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Sign error rate is high"
```

---

## 九、验收标准

- [ ] 签名客户端正确封装
- [ ] XHS/Douyin/Bilibili/Zhihu 支持远程签名
- [ ] 降级策略生效（签名服务不可用时使用本地）
- [ ] 命令行参数 `--sign-server` 可用
- [ ] 集成测试通过
- [ ] 监控指标采集正常

---

*文档结束*

