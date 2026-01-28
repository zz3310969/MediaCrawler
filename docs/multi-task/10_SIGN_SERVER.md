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
| 框架 | Tornado |

### 2.2 API 列表

| 平台 | 接口 | 方法 | 说明 |
|------|------|------|------|
| 健康检查 | `/signsrv/pong` | GET | 服务健康检查 |
| 小红书 | `/signsrv/v1/xhs/sign` | POST | XHS 请求签名 |
| 小红书 | `/signsrv/v1/xhs/update_browser_cookies` | POST | 更新 XHS 浏览器 cookies |
| 抖音 | `/signsrv/v1/douyin/sign` | POST | Douyin 请求签名 |
| B站 | `/signsrv/v1/bilibili/sign` | POST | Bilibili 请求签名 |
| 知乎 | `/signsrv/v1/zhihu/sign` | POST | Zhihu 请求签名 |

### 2.3 统一响应格式

SignSrv 使用统一的响应格式：

```python
# 成功响应
{
    "biz_code": 0,
    "msg": "OK!",
    "isok": true,
    "data": { ... }  # 具体签名数据
}

# 失败响应
{
    "biz_code": 10001,  # 非 0 的错误码
    "msg": "error message",
    "isok": false,
    "extra": { ... }   # 额外错误信息
}
```

---

## 三、各平台签名接口详情

### 3.1 小红书签名

#### 签名接口

```python
# 请求
POST /signsrv/v1/xhs/sign
Content-Type: application/json

{
    "uri": "/api/sns/web/v1/search/notes",  # 必填，请求 URI
    "data": null,                            # 可选，POST body 数据
    "cookies": "a1=xxx;web_session=xxx;..."  # 必填，登录态 cookies
}

# 响应
{
    "biz_code": 0,
    "msg": "OK!",
    "isok": true,
    "data": {
        "x_s": "xxx",
        "x_t": "xxx",
        "x_s_common": "xxx",
        "x_b3_traceid": "xxx",
        "x_mns": "xxx"
    }
}
```

#### 更新浏览器 Cookies

```python
# 请求
POST /signsrv/v1/xhs/update_browser_cookies
Content-Type: application/json

{
    "cookies": "a1=xxx;web_session=xxx;..."  # 新的 cookies
}

# 响应
{
    "biz_code": 0,
    "msg": "update xhs sign server browser cookies success",
    "isok": true,
    "data": {}
}
```

### 3.2 抖音签名

```python
# 请求
POST /signsrv/v1/douyin/sign
Content-Type: application/json

{
    "uri": "/aweme/v1/web/search/item/",      # 必填，请求 URI
    "query_params": "keyword=test&count=20",  # 必填，URL 编码后的查询参数
    "user_agent": "Mozilla/5.0 ...",          # 必填，User-Agent
    "cookies": "ttwid=xxx;..."                # 必填，登录态 cookies
}

# 响应
{
    "biz_code": 0,
    "msg": "OK!",
    "isok": true,
    "data": {
        "a_bogus": "xxx"
    }
}
```

### 3.3 B站签名

```python
# 请求
POST /signsrv/v1/bilibili/sign
Content-Type: application/json

{
    "req_data": {                    # 必填，JSON 格式的请求参数
        "keyword": "test",
        "page": 1,
        "page_size": 20
    },
    "cookies": "bili_ticket=xxx;..." # 必填，登录态 cookies
}

# 响应
{
    "biz_code": 0,
    "msg": "OK!",
    "isok": true,
    "data": {
        "wts": "xxx",
        "w_rid": "xxx"
    }
}
```

### 3.4 知乎签名

```python
# 请求
POST /signsrv/v1/zhihu/sign
Content-Type: application/json

{
    "uri": "/api/v4/search_v3",       # 必填，请求 URI
    "cookies": "z_c0=xxx;..."         # 必填，登录态 cookies
}

# 响应
{
    "biz_code": 0,
    "msg": "OK!",
    "isok": true,
    "data": {
        "x_zst_81": "xxx",
        "x_zse_96": "xxx"
    }
}
```

### 3.5 健康检查

```python
# 请求
GET /signsrv/pong

# 响应
{
    "biz_code": 0,
    "msg": "OK!",
    "isok": true,
    "data": {
        "message": "pong"
    }
}
```

---

## 四、签名客户端封装

### 4.1 响应模型 (`api/services/sign_client.py`)

```python
from pydantic import BaseModel


class XhsSignResult(BaseModel):
    """小红书签名结果"""
    x_s: str
    x_t: str
    x_s_common: str
    x_b3_traceid: str
    x_mns: str


class DouyinSignResult(BaseModel):
    """抖音签名结果"""
    a_bogus: str


class BilibiliSignResult(BaseModel):
    """B站签名结果"""
    wts: str
    w_rid: str


class ZhihuSignResult(BaseModel):
    """知乎签名结果"""
    x_zst_81: str
    x_zse_96: str
```

### 4.2 签名客户端 (`api/services/sign_client.py`)

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
    
    # API 路径常量
    API_XHS_SIGN = "/signsrv/v1/xhs/sign"
    API_XHS_UPDATE_COOKIES = "/signsrv/v1/xhs/update_browser_cookies"
    API_DOUYIN_SIGN = "/signsrv/v1/douyin/sign"
    API_BILIBILI_SIGN = "/signsrv/v1/bilibili/sign"
    API_ZHIHU_SIGN = "/signsrv/v1/zhihu/sign"
    API_HEALTH = "/signsrv/pong"
    
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
                # SignSrv 使用 biz_code 字段
                if result.get("biz_code") != 0:
                    raise SignError(f"Sign error: {result.get('msg')}")
                
                return result.get("data", {})
            
            except httpx.HTTPError as e:
                logger.warning(f"Sign request failed (attempt {attempt + 1}): {e}")
                if attempt == self._config.retry_count:
                    raise SignError(f"Sign request failed after {attempt + 1} attempts")
    
    # ========== 小红书 ==========
    
    async def sign_xhs(
        self,
        uri: str,
        data: Any = None,
        cookies: str = ""
    ) -> XhsSignResult:
        """小红书签名"""
        result = await self._request(self.API_XHS_SIGN, {
            "uri": uri,
            "data": data,
            "cookies": cookies
        })
        return XhsSignResult(**result)
    
    async def update_xhs_cookies(self, cookies: str) -> bool:
        """更新小红书浏览器 cookies"""
        try:
            await self._request(self.API_XHS_UPDATE_COOKIES, {"cookies": cookies})
            return True
        except SignError:
            return False
    
    # ========== 抖音 ==========
    
    async def sign_douyin(
        self,
        uri: str,
        query_params: str,
        user_agent: str,
        cookies: str
    ) -> DouyinSignResult:
        """抖音签名"""
        result = await self._request(self.API_DOUYIN_SIGN, {
            "uri": uri,
            "query_params": query_params,
            "user_agent": user_agent,
            "cookies": cookies
        })
        return DouyinSignResult(**result)
    
    # ========== B站 ==========
    
    async def sign_bilibili(
        self,
        req_data: Dict[str, Any],
        cookies: str
    ) -> BilibiliSignResult:
        """B站签名"""
        result = await self._request(self.API_BILIBILI_SIGN, {
            "req_data": req_data,
            "cookies": cookies
        })
        return BilibiliSignResult(**result)
    
    # ========== 知乎 ==========
    
    async def sign_zhihu(
        self,
        uri: str,
        cookies: str
    ) -> ZhihuSignResult:
        """知乎签名"""
        result = await self._request(self.API_ZHIHU_SIGN, {
            "uri": uri,
            "cookies": cookies
        })
        return ZhihuSignResult(**result)
    
    # ========== 健康检查 ==========
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._client:
                return False
            response = await self._client.get(self.API_HEALTH)
            if response.status_code == 200:
                result = response.json()
                return result.get("biz_code") == 0
            return False
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
    
    if config.enabled:
        is_healthy = await _sign_client.health_check()
        if is_healthy:
            logger.info(f"Sign client connected to {config.url}")
        else:
            logger.warning(f"Sign server at {config.url} is not available")
    
    return _sign_client


async def close_sign_client():
    global _sign_client
    if _sign_client:
        await _sign_client.__aexit__(None, None, None)
        _sign_client = None


def is_sign_server_enabled() -> bool:
    return _sign_client is not None and _sign_client.enabled
```

---

## 五、平台客户端改造

### 5.1 XHS 客户端改造示例

```python
# media_platform/xhs/client.py

from typing import Optional, Dict
from api.services.sign_client import get_sign_client, SignError, XhsSignResult


class XHSClient:
    """小红书客户端"""
    
    def __init__(
        self,
        cookies: str,
        user_agent: str,
        use_sign_server: bool = True
    ):
        self._cookies = cookies
        self._user_agent = user_agent
        self._use_sign_server = use_sign_server
    
    async def _get_sign_headers(self, uri: str, data: Any = None) -> Dict[str, str]:
        """获取签名头"""
        sign_client = get_sign_client()
        
        # 优先使用签名服务
        if self._use_sign_server and sign_client and sign_client.enabled:
            try:
                result: XhsSignResult = await sign_client.sign_xhs(
                    uri=uri,
                    data=data,
                    cookies=self._cookies
                )
                return {
                    "x-s": result.x_s,
                    "x-t": result.x_t,
                    "x-s-common": result.x_s_common,
                    "x-b3-traceid": result.x_b3_traceid,
                    "x-mns": result.x_mns
                }
            except SignError as e:
                logger.warning(f"Sign server failed, fallback to local: {e}")
        
        # 降级到本地签名（需要 Playwright）
        return await self._local_sign(uri, data)
    
    async def _local_sign(self, uri: str, data: Any) -> Dict[str, str]:
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

### 5.2 抖音客户端改造示例

```python
# media_platform/douyin/client.py

from urllib.parse import urlencode
from api.services.sign_client import get_sign_client, SignError, DouyinSignResult


class DouyinClient:
    """抖音客户端"""
    
    async def _get_sign_params(
        self,
        uri: str,
        params: Dict[str, Any]
    ) -> Dict[str, str]:
        """获取签名参数"""
        sign_client = get_sign_client()
        
        if sign_client and sign_client.enabled:
            try:
                query_params = urlencode(params)
                result: DouyinSignResult = await sign_client.sign_douyin(
                    uri=uri,
                    query_params=query_params,
                    user_agent=self._user_agent,
                    cookies=self._cookies
                )
                return {"a_bogus": result.a_bogus}
            except SignError as e:
                logger.warning(f"Sign server failed: {e}")
        
        return await self._local_sign(uri, params)
```

### 5.3 B站客户端改造示例

```python
# media_platform/bilibili/client.py

from api.services.sign_client import get_sign_client, SignError, BilibiliSignResult


class BilibiliClient:
    """B站客户端"""
    
    async def _get_sign_params(
        self,
        req_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """获取签名参数"""
        sign_client = get_sign_client()
        
        if sign_client and sign_client.enabled:
            try:
                result: BilibiliSignResult = await sign_client.sign_bilibili(
                    req_data=req_data,
                    cookies=self._cookies
                )
                return {
                    "wts": result.wts,
                    "w_rid": result.w_rid
                }
            except SignError as e:
                logger.warning(f"Sign server failed: {e}")
        
        return await self._local_sign(req_data)
```

---

## 六、配置集成

### 6.1 配置类

```python
# config/sign_server.py

from pydantic_settings import BaseSettings


class SignServerSettings(BaseSettings):
    """签名服务配置"""
    
    sign_server_enabled: bool = True
    sign_server_url: str = "http://localhost:8989"
    sign_server_timeout: float = 10.0
    sign_server_retry: int = 2
    
    # 降级策略
    sign_fallback_enabled: bool = True
    
    class Config:
        env_prefix = "MC_"
```

### 6.2 启动时初始化

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
        await init_sign_client(config)
    
    yield
    
    # 清理
    await close_sign_client()
```

---

## 七、命令行参数支持

### 7.1 main.py 改造

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

## 八、测试用例

### 8.1 签名客户端测试

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
async def test_health_check(sign_client):
    """测试健康检查"""
    result = await sign_client.health_check()
    assert result == True


@pytest.mark.asyncio
async def test_xhs_sign(sign_client):
    """测试小红书签名"""
    result = await sign_client.sign_xhs(
        uri="/api/sns/web/v1/search/notes",
        data=None,
        cookies="a1=xxx;web_session=xxx"
    )
    
    assert result.x_s is not None
    assert result.x_t is not None
    assert result.x_s_common is not None
    assert result.x_b3_traceid is not None
    assert result.x_mns is not None


@pytest.mark.asyncio
async def test_douyin_sign(sign_client):
    """测试抖音签名"""
    result = await sign_client.sign_douyin(
        uri="/aweme/v1/web/search/item/",
        query_params="keyword=test&count=20",
        user_agent="Mozilla/5.0 ...",
        cookies="ttwid=xxx"
    )
    
    assert result.a_bogus is not None


@pytest.mark.asyncio
async def test_bilibili_sign(sign_client):
    """测试B站签名"""
    result = await sign_client.sign_bilibili(
        req_data={"keyword": "test", "page": 1},
        cookies="bili_ticket=xxx"
    )
    
    assert result.wts is not None
    assert result.w_rid is not None


@pytest.mark.asyncio
async def test_zhihu_sign(sign_client):
    """测试知乎签名"""
    result = await sign_client.sign_zhihu(
        uri="/api/v4/search_v3",
        cookies="z_c0=xxx"
    )
    
    assert result.x_zst_81 is not None
    assert result.x_zse_96 is not None


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
            await client.sign_xhs(uri="/test", cookies="test")
```

### 8.2 集成测试

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

## 九、部署配置

### 9.1 Docker Compose

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
      - SIGN_TYPE=javascript  # 或 playwright
      - APP_PORT=8989
      - APP_ADDRESS=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8989/signsrv/pong"]
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

### 9.2 环境变量

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

## 十、监控与告警

### 10.1 指标采集

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
    platform = path.split("/")[3]  # /signsrv/v1/{platform}/sign
    
    with sign_latency_seconds.labels(platform=platform).time():
        try:
            result = await self._do_request(path, data)
            sign_requests_total.labels(platform=platform, status="success").inc()
            return result
        except Exception as e:
            sign_requests_total.labels(platform=platform, status="error").inc()
            raise
```

### 10.2 告警规则（Prometheus）

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

## 十一、验收标准

- [ ] 签名客户端正确封装
- [ ] API 路径与 SignSrv 一致 (`/signsrv/v1/...`)
- [ ] 响应解析正确 (`biz_code` 字段)
- [ ] XHS/Douyin/Bilibili/Zhihu 支持远程签名
- [ ] 降级策略生效（签名服务不可用时使用本地）
- [ ] 命令行参数 `--sign-server` 可用
- [ ] 集成测试通过
- [ ] 监控指标采集正常

---

*文档结束*
