# MediaCrawler 代理系统增强设计方案

> **版本**: v1.0  
> **日期**: 2026-01-28  
> **状态**: 设计完成，待实现

## 目录

- [一、概述](#一概述)
- [二、系统架构](#二系统架构)
- [三、账号-代理绑定模块](#三账号-代理绑定模块)
- [四、代理来源模块](#四代理来源模块)
- [五、代理质量评估模块](#五代理质量评估模块)
- [六、故障转移模块](#六故障转移模块)
- [七、使用统计模块](#七使用统计模块)
- [八、数据库设计](#八数据库设计)
- [九、配置文件设计](#九配置文件设计)
- [十、前端界面设计](#十前端界面设计)
- [十一、API接口设计](#十一api接口设计)
- [十二、错误处理设计](#十二错误处理设计)
- [十三、实现计划](#十三实现计划)
- [十四、测试策略](#十四测试策略)

---

## 一、概述

### 1.1 背景

当前 MediaCrawler 的代理系统存在以下问题：

| 问题 | 描述 | 影响 |
|------|------|------|
| 代理供应商有限 | 仅支持快代理和豌豆HTTP | 用户选择受限 |
| 缺乏代理质量评估 | 没有代理质量评分/黑名单机制 | 可能反复获取到低质量代理 |
| 缓存依赖Redis | `IpCache` 强依赖 Redis | 简单部署场景需要额外配置 |
| 缺乏代理故障转移 | 代理失败时重试逻辑简单 | 单个代理失败可能导致请求失败 |
| 协议支持单一 | 主要支持HTTP代理 | 不支持SOCKS5等其他协议 |
| 缺乏代理使用统计 | 没有记录代理使用情况 | 难以分析代理效果和成本 |
| IP突变问题 | 账号没有绑定固定代理 | 同一账号IP频繁变化可能触发风控 |

### 1.2 目标

本方案旨在实现以下功能：

1. **代理配置持久化 + 账号绑定** - 解决IP突变问题
2. **自定义代理API接口** - 允许用户配置自己的代理获取API
3. **代理质量评估** - 记录代理成功率、响应时间，自动淘汰低质量代理
4. **本地代理列表支持** - 允许从文件加载静态代理列表
5. **SOCKS5支持** - 扩展协议支持
6. **代理故障转移** - 当代理失败时自动切换到下一个
7. **代理使用统计** - 记录每个代理的使用情况和效果
8. **完整的WebUI管理界面** - 可视化代理管理

### 1.3 关键概念说明

**账号（Account）**：指爬虫使用的登录凭证（Cookie/Token），来自 `account/account_pool.py` 中的 `Account` 类。

**账号-代理绑定**：将爬虫账号与特定代理IP关联，确保同一账号始终使用同一代理，避免IP突变触发平台风控。

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           配置层 (config/)                                   │
│  proxy_config.yaml - 代理配置文件（供应商、自定义API、本地列表等）              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         代理管理层 (proxy/)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ProxyManager (核心管理器)                          │   │
│  │  - 统一管理所有代理来源                                               │   │
│  │  - 代理分配与回收                                                     │   │
│  │  - 账号-代理绑定管理                                                  │   │
│  │  - 代理故障转移                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐         │
│         ▼                            ▼                            ▼         │
│  ┌─────────────────┐   ┌─────────────────────────┐   ┌─────────────────┐   │
│  │ ProxyProvider   │   │ ProxyQualityEvaluator   │   │ ProxyStatistics │   │
│  │ (代理供应商)     │   │ (质量评估器)             │   │ (使用统计)       │   │
│  │ ├─ KuaiDaiLi    │   │ - 成功率计算             │   │ - 请求计数       │   │
│  │ ├─ WanDou       │   │ - 响应时间统计           │   │ - 流量统计       │   │
│  │ ├─ CustomAPI    │   │ - 自动降级/淘汰          │   │ - 成本分析       │   │
│  │ └─ LocalFile    │   │ - 代理评分               │   │ - 报表生成       │   │
│  └─────────────────┘   └─────────────────────────┘   └─────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ProxyPersistence (持久化层)                        │   │
│  │  - 代理配置持久化 (JSON/SQLite)                                       │   │
│  │  - 账号-代理绑定关系持久化                                            │   │
│  │  - 代理质量数据持久化                                                 │   │
│  │  - 使用统计数据持久化                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           使用层 (各平台Client)                              │
│  通过 ProxyRefreshMixin 与 ProxyManager 交互                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 账号-代理绑定模型

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           账号-代理绑定模型                                   │
│                                                                             │
│   Account (爬虫账号)              Proxy (代理IP)                             │
│   ┌─────────────────┐            ┌─────────────────┐                       │
│   │ account_id      │            │ proxy_id        │                       │
│   │ platform (xhs)  │◄──绑定────►│ ip:port         │                       │
│   │ cookies         │            │ protocol        │                       │
│   │ status          │            │ quality_score   │                       │
│   └─────────────────┘            └─────────────────┘                       │
│                                                                             │
│   绑定规则：                                                                 │
│   1. 一个账号只能绑定一个代理（1:1）                                          │
│   2. 一个代理可以被多个账号使用（1:N，可配置是否允许）                          │
│   3. 绑定关系持久化，重启后保持                                               │
│   4. 代理失效时，优先选择同地区/同运营商的代理重新绑定                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 文件结构

```
proxy/
├── __init__.py
├── types.py                          # 数据类型定义（扩展协议支持）
├── base_proxy.py                     # Provider基类
├── proxy_ip_pool.py                  # 代理池（扩展）
├── proxy_mixin.py                    # Mixin（扩展故障转移）
├── proxy_manager.py                  # 【新增】核心管理器
│
├── providers/                        # 代理供应商
│   ├── __init__.py
│   ├── kuaidl_proxy.py
│   ├── wandou_http_proxy.py
│   ├── custom_api_proxy.py          # 【新增】自定义API
│   └── local_file_proxy.py          # 【新增】本地文件
│
├── persistence/                      # 【新增】持久化层
│   ├── __init__.py
│   ├── models.py                    # 持久化数据模型
│   ├── proxy_store.py               # 代理存储
│   └── backends/
│       ├── json_backend.py
│       ├── sqlite_backend.py
│       └── database_backend.py
│
├── binding/                          # 【新增】账号-代理绑定
│   ├── __init__.py
│   ├── models.py                    # 绑定数据模型
│   ├── manager.py                   # 绑定管理器
│   └── store.py                     # 绑定存储
│
├── quality/                          # 【新增】质量评估
│   ├── __init__.py
│   ├── models.py
│   ├── evaluator.py
│   └── auto_retirer.py
│
├── failover/                         # 【新增】故障转移
│   ├── __init__.py
│   ├── strategy.py
│   └── manager.py
│
├── statistics/                       # 【新增】使用统计
│   ├── __init__.py
│   ├── models.py
│   ├── collector.py
│   ├── reporter.py
│   └── store.py
│
└── validators/                       # 【新增】代理验证
    ├── __init__.py
    ├── http_validator.py
    └── socks5_validator.py

api/
├── proxy_api.py                      # 【新增】代理管理API
└── proxy_binding_api.py              # 【新增】绑定管理API

webui-src/src/
├── pages/proxy/                      # 【新增】代理管理页面
├── components/proxy/                 # 【新增】代理相关组件
├── hooks/proxy/                      # 【新增】代理相关Hooks
├── api/proxy.ts                      # 【新增】代理API调用
└── types/proxy.ts                    # 【新增】代理类型定义
```

---

## 三、账号-代理绑定模块

### 3.1 数据模型

```python
# proxy/binding/models.py

@dataclass
class AccountProxyBinding:
    """账号-代理绑定关系"""
    binding_id: str                      # 绑定ID
    
    # 账号信息
    account_id: str                      # 账号唯一标识（来自 account_pool.Account）
    platform: str                        # 平台 (xhs, dy, wb, bili, etc.)
    
    # 代理信息
    proxy_id: str                        # 绑定的代理ID
    
    # 绑定配置
    is_sticky: bool = True               # 粘性绑定（代理失效时尽量选相似代理）
    allow_auto_rebind: bool = True       # 允许自动重新绑定
    
    # 时间信息
    bound_at: datetime                   # 绑定时间
    last_used_at: Optional[datetime]     # 最后使用时间
    last_verified_at: Optional[datetime] # 最后验证时间
    
    # 状态
    status: str = "active"               # active | expired | unbound
    rebind_count: int = 0                # 重新绑定次数


@dataclass
class ProxyRegionInfo:
    """代理地区信息（用于相似代理匹配）"""
    proxy_id: str
    country: str                         # 国家
    province: str                        # 省份
    city: str                            # 城市
    isp: str                             # 运营商 (电信/联通/移动)
    
    def similarity_score(self, other: "ProxyRegionInfo") -> float:
        """计算与另一个代理的相似度 (0-1)"""
        score = 0.0
        if self.country == other.country:
            score += 0.2
        if self.province == other.province:
            score += 0.3
        if self.city == other.city:
            score += 0.3
        if self.isp == other.isp:
            score += 0.2
        return score
```

### 3.2 绑定管理器

```python
# proxy/binding/manager.py

class AccountProxyBindingManager:
    """账号-代理绑定管理器"""
    
    def __init__(
        self,
        binding_store: BindingStore,
        proxy_store: ProxyStore,
        quality_evaluator: Optional[ProxyQualityEvaluator] = None,
    ):
        pass
    
    # ==================== 绑定操作 ====================
    
    async def bind(
        self,
        account_id: str,
        platform: str,
        proxy_id: Optional[str] = None,    # 不指定则自动分配
        is_sticky: bool = True,
    ) -> AccountProxyBinding:
        """为账号绑定代理"""
    
    async def unbind(self, account_id: str, platform: str) -> bool:
        """解除账号的代理绑定"""
    
    async def rebind(
        self,
        account_id: str,
        platform: str,
        reason: str = "proxy_failed"
    ) -> Optional[AccountProxyBinding]:
        """重新绑定代理（优先相似代理）"""
    
    # ==================== 查询操作 ====================
    
    async def get_binding(
        self,
        account_id: str,
        platform: str
    ) -> Optional[AccountProxyBinding]:
        """获取账号的代理绑定"""
    
    async def get_proxy_for_account(
        self,
        account_id: str,
        platform: str,
        auto_bind: bool = True
    ) -> Optional[IpInfoModel]:
        """获取账号绑定的代理（自动绑定/重绑）"""
    
    # ==================== 自动分配 ====================
    
    async def auto_assign_proxy(
        self,
        account_id: str,
        platform: str,
        prefer_exclusive: bool = False,
    ) -> IpInfoModel:
        """自动为账号分配代理"""
    
    async def find_similar_proxy(
        self,
        old_proxy: IpInfoModel
    ) -> Optional[IpInfoModel]:
        """查找相似代理（同地区/同运营商）"""
    
    # ==================== 验证与维护 ====================
    
    async def verify_binding(
        self,
        account_id: str,
        platform: str
    ) -> bool:
        """验证绑定的代理是否有效"""
    
    async def verify_all_bindings(self) -> Dict[str, bool]:
        """验证所有绑定"""
    
    async def cleanup_expired_bindings(self) -> int:
        """清理过期的绑定"""
```

### 3.3 与AccountPool集成

```python
# account/account_pool.py (扩展)

@dataclass
class Account:
    """账号数据模型 - 扩展代理绑定字段"""
    
    # ... 现有字段 ...
    
    # 代理绑定（新增）
    bound_proxy_id: Optional[str] = None        # 绑定的代理ID
    proxy_binding_mode: str = "auto"            # auto | manual | none
    proxy_sticky: bool = True                   # 粘性绑定


class AccountPool:
    """账号池管理器 - 扩展代理绑定支持"""
    
    async def get_next_account_with_proxy(
        self
    ) -> Tuple[Optional[Account], Optional[IpInfoModel]]:
        """获取下一个账号及其绑定的代理"""
```

---

## 四、代理来源模块

### 4.1 本地文件代理

#### 支持的文件格式

**TXT格式** (每行一个):
```txt
192.168.1.1:8080
http://user:pass@192.168.1.2:8080
socks5://192.168.1.3:1080
```

**JSON格式**:
```json
{
  "proxies": [
    {"ip": "192.168.1.1", "port": 8080, "protocol": "http"},
    {"ip": "192.168.1.2", "port": 8080, "protocol": "http", "user": "admin", "password": "secret"}
  ]
}
```

**YAML格式**:
```yaml
proxies:
  - ip: 192.168.1.1
    port: 8080
    protocol: http
  - ip: 192.168.1.2
    port: 1080
    protocol: socks5
    user: admin
    password: secret
```

#### Provider实现

```python
# proxy/providers/local_file_proxy.py

class LocalFileProxy(ProxyProvider):
    """本地文件代理Provider"""
    
    def __init__(
        self,
        file_path: str,
        file_format: LocalFileFormat = None,  # 自动检测
        watch_changes: bool = True,           # 监听文件变化
        reload_interval: int = 60,            # 重载间隔(秒)
    ):
        pass
    
    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """获取代理（支持热重载）"""
    
    async def _load_from_file(self) -> List[IpInfoModel]:
        """从文件加载代理列表"""
    
    async def _watch_file_changes(self) -> None:
        """监听文件变化，自动重载"""
```

### 4.2 自定义API代理

#### 配置示例

```yaml
custom_api:
  enabled: true
  endpoints:
    - name: "my_proxy_pool"
      url: "https://my-proxy-api.com/get"
      method: GET
      params:
        num: "${count}"           # 动态参数
        type: "json"
      headers:
        Authorization: "Bearer ${CUSTOM_PROXY_TOKEN}"  # 环境变量
      response_mapping:
        list_field: "data.proxies"
        ip_field: "ip"
        port_field: "port"
        protocol_field: "protocol"
        user_field: "username"
        password_field: "password"
        expire_field: "expire_time"
        expire_format: "timestamp"  # timestamp | iso | seconds
      rate_limit:
        requests_per_minute: 10
```

#### Provider实现

```python
# proxy/providers/custom_api_proxy.py

@dataclass
class CustomApiConfig:
    """自定义API配置"""
    name: str
    url: str
    method: str
    params: Optional[Dict]
    headers: Optional[Dict]
    body: Optional[Dict]
    response_mapping: Dict[str, str]
    rate_limit: Optional[Dict]


class CustomApiProxy(ProxyProvider):
    """自定义代理API实现"""
    
    def __init__(self, config: CustomApiConfig):
        self.config = config
        self._rate_limiter = RateLimiter(config.rate_limit)
    
    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """从自定义API获取代理"""
        
    def _parse_response(self, response: Dict) -> List[IpInfoModel]:
        """根据配置的字段映射解析响应"""
        
    def _substitute_variables(self, template: str, context: Dict) -> str:
        """替换模板变量"""
```

### 4.3 SOCKS5支持

```python
# proxy/types.py

class ProxyProtocol(Enum):
    """代理协议类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class IpInfoModel(BaseModel):
    """统一IP模型 - 扩展版"""
    
    ip: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    user: Optional[str] = None
    password: Optional[str] = None
    expired_time_ts: Optional[int] = None
    
    def to_url(self) -> str:
        """转换为代理URL"""
        auth = f"{self.user}:{self.password}@" if self.user else ""
        return f"{self.protocol.value}://{auth}{self.ip}:{self.port}"
    
    def to_httpx_proxy(self) -> str:
        """转换为httpx代理格式（支持socks5）"""
        return self.to_url()
    
    def to_playwright_proxy(self) -> Dict:
        """转换为Playwright代理格式"""
        proxy = {"server": f"{self.protocol.value}://{self.ip}:{self.port}"}
        if self.user:
            proxy["username"] = self.user
            proxy["password"] = self.password
        return proxy
```

---

## 五、代理质量评估模块

### 5.1 质量指标模型

```python
# proxy/quality/models.py

@dataclass
class ProxyQualityMetrics:
    """代理质量指标"""
    proxy_id: str
    
    # 成功率指标
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    
    # 响应时间指标 (毫秒)
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    p95_response_time: float = 0.0
    
    # 稳定性指标
    consecutive_failures: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_requests / self.total_requests
    
    @property
    def quality_score(self) -> float:
        """综合质量评分 (0-100)"""
        # 加权计算: 成功率60% + 响应时间30% + 稳定性10%
        success_score = self.success_rate * 60
        time_score = max(0, 30 - self.avg_response_time / 200)
        stability_score = max(0, 10 - self.consecutive_failures * 2)
        return success_score + time_score + stability_score
```

### 5.2 质量评估器

```python
# proxy/quality/evaluator.py

class ProxyQualityEvaluator:
    """代理质量评估器"""
    
    def __init__(
        self,
        min_success_rate: float = 0.7,
        max_avg_response_time: int = 5000,
        max_consecutive_failures: int = 5,
        evaluation_window: int = 100,
    ):
        self._metrics_store: Dict[str, ProxyQualityMetrics] = {}
        self._response_time_buffer: Dict[str, deque] = {}
    
    async def record_request(
        self,
        proxy_id: str,
        success: bool,
        response_time_ms: float,
        error_type: Optional[str] = None
    ) -> None:
        """记录请求结果"""
    
    async def evaluate_proxy(self, proxy_id: str) -> ProxyQualityMetrics:
        """评估代理质量"""
    
    async def should_retire_proxy(self, proxy_id: str) -> bool:
        """判断是否应该淘汰代理"""
    
    async def get_best_proxies(self, count: int = 10) -> List[str]:
        """获取质量最好的N个代理"""


class AutoProxyRetirer:
    """自动代理淘汰器"""
    
    async def start_background_check(self) -> None:
        """启动后台检查任务"""
    
    async def retire_low_quality_proxies(self) -> List[str]:
        """淘汰低质量代理"""
```

---

## 六、故障转移模块

### 6.1 故障转移策略

```python
# proxy/failover/strategy.py

class FailoverStrategy(ABC):
    """故障转移策略抽象"""
    
    @abstractmethod
    async def on_failure(
        self,
        failed_proxy: IpInfoModel,
        error: Exception,
        context: Dict
    ) -> Optional[IpInfoModel]:
        """代理失败时调用，返回替代代理"""


class SimpleFailoverStrategy(FailoverStrategy):
    """简单故障转移 - 直接获取下一个可用代理"""


class StickyFailoverStrategy(FailoverStrategy):
    """粘性故障转移 - 优先选择相似代理"""


class WeightedFailoverStrategy(FailoverStrategy):
    """加权故障转移 - 根据代理质量评分选择"""


class CircuitBreakerFailoverStrategy(FailoverStrategy):
    """熔断故障转移 - 代理连续失败后暂时禁用"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
        half_open_requests: int = 3,
    ):
        pass
```

### 6.2 熔断器状态机

```
┌─────────┐    failures >= threshold    ┌─────────┐
│ CLOSED  │ ──────────────────────────► │  OPEN   │
│ (正常)   │                             │ (熔断)   │
└─────────┘                             └─────────┘
     ▲                                       │
     │                            timeout后  │
     │     success                          ▼
     │    ┌──────────────────────────┐
     └────│      HALF_OPEN          │
          │ (半开, 试探性请求)        │
          └──────────────────────────┘
                      │
                      │ failure
                      └──────────► 回到 OPEN
```

### 6.3 故障转移管理器

```python
# proxy/failover/manager.py

class ProxyFailoverManager:
    """代理故障转移管理器"""
    
    def __init__(
        self,
        proxy_pool: ProxyIpPool,
        strategy: FailoverStrategy,
        quality_evaluator: ProxyQualityEvaluator,
        max_retries: int = 3,
    ):
        pass
    
    async def execute_with_failover(
        self,
        request_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行请求，失败时自动切换代理重试"""
    
    async def get_fallback_proxy(
        self,
        failed_proxy: IpInfoModel,
        error: Exception
    ) -> Optional[IpInfoModel]:
        """获取备用代理"""
```

---

## 七、使用统计模块

### 7.1 统计数据模型

```python
# proxy/statistics/models.py

@dataclass
class ProxyUsageRecord:
    """单次代理使用记录"""
    record_id: str
    proxy_id: str
    user_id: Optional[str]
    platform: str
    timestamp: datetime
    request_url: str
    response_code: int
    response_time_ms: float
    bytes_sent: int
    bytes_received: int
    success: bool
    error_message: Optional[str]


@dataclass
class ProxyDailyStats:
    """代理每日统计"""
    proxy_id: str
    date: date
    total_requests: int
    success_requests: int
    failed_requests: int
    total_bytes_sent: int
    total_bytes_received: int
    avg_response_time: float
    unique_users: int
    platforms_used: List[str]


@dataclass
class ProxyOverallStats:
    """代理总体统计"""
    proxy_id: str
    source: str
    first_used_at: datetime
    last_used_at: datetime
    total_requests: int
    success_rate: float
    avg_response_time: float
    total_traffic_bytes: int
    estimated_cost: float
```

### 7.2 统计收集与报表

```python
# proxy/statistics/collector.py

class ProxyStatisticsCollector:
    """代理统计收集器"""
    
    def __init__(
        self,
        store: ProxyStatisticsStore,
        buffer_size: int = 100,
        flush_interval: int = 60,
    ):
        self._buffer: List[ProxyUsageRecord] = []
    
    async def record_usage(self, ...) -> None:
        """记录代理使用"""
    
    async def flush(self) -> None:
        """刷新缓冲区到存储"""


# proxy/statistics/reporter.py

class ProxyStatisticsReporter:
    """代理统计报表生成器"""
    
    async def get_daily_report(self, date: date) -> Dict:
        """获取每日报表"""
    
    async def get_proxy_report(self, proxy_id: str) -> Dict:
        """获取单个代理的详细报表"""
    
    async def get_cost_report(self, start_date: date, end_date: date) -> Dict:
        """获取成本报表"""
    
    async def export_to_csv(self, report: Dict, file_path: str) -> None:
        """导出报表到CSV"""
```

---

## 八、数据库设计

### 8.1 代理基础表

```sql
-- 代理表
CREATE TABLE proxies (
    proxy_id VARCHAR(64) PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    port INT NOT NULL,
    protocol VARCHAR(10) NOT NULL DEFAULT 'http',
    username VARCHAR(64),
    password VARCHAR(128),
    source VARCHAR(32) NOT NULL,
    source_name VARCHAR(64),
    
    -- 地区信息
    country VARCHAR(32) DEFAULT 'CN',
    province VARCHAR(32),
    city VARCHAR(32),
    isp VARCHAR(32),
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    is_validated BOOLEAN DEFAULT FALSE,
    last_validated_at TIMESTAMP,
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expired_at TIMESTAMP,
    
    UNIQUE INDEX idx_ip_port_protocol (ip, port, protocol),
    INDEX idx_source (source),
    INDEX idx_active (is_active),
    INDEX idx_region (country, province, city)
);
```

### 8.2 账号-代理绑定表

```sql
-- 绑定关系表
CREATE TABLE account_proxy_bindings (
    binding_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    proxy_id VARCHAR(64) NOT NULL,
    
    -- 配置
    is_sticky BOOLEAN DEFAULT TRUE,
    allow_auto_rebind BOOLEAN DEFAULT TRUE,
    
    -- 状态
    status VARCHAR(16) DEFAULT 'active',
    rebind_count INT DEFAULT 0,
    
    -- 时间
    bound_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    last_verified_at TIMESTAMP,
    unbound_at TIMESTAMP,
    
    UNIQUE INDEX idx_account_platform (account_id, platform),
    INDEX idx_proxy (proxy_id),
    INDEX idx_status (status),
    
    FOREIGN KEY (proxy_id) REFERENCES proxies(proxy_id) ON DELETE CASCADE
);

-- 绑定历史表
CREATE TABLE binding_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    binding_id VARCHAR(64),
    account_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    action VARCHAR(16) NOT NULL,
    old_proxy_id VARCHAR(64),
    new_proxy_id VARCHAR(64),
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_account (account_id, platform),
    INDEX idx_time (created_at)
);
```

### 8.3 质量与统计表

```sql
-- 代理质量指标表
CREATE TABLE proxy_quality_metrics (
    proxy_id VARCHAR(64) PRIMARY KEY,
    total_requests INT DEFAULT 0,
    success_requests INT DEFAULT 0,
    failed_requests INT DEFAULT 0,
    timeout_requests INT DEFAULT 0,
    avg_response_time FLOAT DEFAULT 0,
    min_response_time FLOAT,
    max_response_time FLOAT,
    p95_response_time FLOAT,
    consecutive_failures INT DEFAULT 0,
    consecutive_successes INT DEFAULT 0,
    success_rate FLOAT DEFAULT 0,
    quality_score FLOAT DEFAULT 100,
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (proxy_id) REFERENCES proxies(proxy_id) ON DELETE CASCADE
);

-- 代理使用记录表
CREATE TABLE proxy_usage_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    proxy_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64),
    platform VARCHAR(32) NOT NULL,
    request_url TEXT,
    request_method VARCHAR(10),
    response_code INT,
    response_time_ms FLOAT,
    bytes_sent INT DEFAULT 0,
    bytes_received INT DEFAULT 0,
    success BOOLEAN,
    error_type VARCHAR(32),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_proxy_time (proxy_id, created_at),
    INDEX idx_account_time (account_id, created_at),
    INDEX idx_created (created_at)
);

-- 代理每日汇总表
CREATE TABLE proxy_daily_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proxy_id VARCHAR(64) NOT NULL,
    stat_date DATE NOT NULL,
    total_requests INT DEFAULT 0,
    success_requests INT DEFAULT 0,
    failed_requests INT DEFAULT 0,
    total_bytes_sent BIGINT DEFAULT 0,
    total_bytes_received BIGINT DEFAULT 0,
    avg_response_time FLOAT,
    unique_accounts INT DEFAULT 0,
    platforms_used JSON,
    
    UNIQUE INDEX idx_proxy_date (proxy_id, stat_date),
    INDEX idx_date (stat_date)
);
```

---

## 九、配置文件设计

```yaml
# config/proxy_config.yaml

proxy:
  # ---------- 基础配置 ----------
  enabled: true
  
  storage:
    backend: sqlite                       # json | sqlite | mysql
    sqlite:
      path: ./data/proxy.db
  
  protocols:
    - http
    - https
    - socks5
  
  # ---------- 代理池配置 ----------
  pool:
    size: 20
    min_available: 5
    preload: true
    preload_count: 10
    
    validate:
      on_get: true
      interval: 300
      timeout: 10
      test_url: "https://httpbin.org/ip"
    
    auto_refill:
      enabled: true
      check_interval: 60
      batch_size: 5
  
  # ---------- 代理来源配置 ----------
  sources:
    priority:
      local_file: 1
      custom_api: 2
      kuaidaili: 3
      wandou: 4
    
    local_file:
      enabled: true
      paths:
        - ./config/proxies.txt
        - ./config/proxies.json
      watch_changes: true
      reload_interval: 60
    
    kuaidaili:
      enabled: false
      secret_id: ${KDL_SECRET_ID:}
      signature: ${KDL_SIGNATURE:}
      username: ${KDL_USERNAME:}
      password: ${KDL_PASSWORD:}
    
    wandou:
      enabled: false
      app_key: ${WANDOU_APP_KEY:}
    
    custom_api:
      enabled: true
      endpoints:
        - name: "my_proxy_pool"
          enabled: true
          url: "https://my-proxy-api.com/get"
          method: GET
          params:
            num: "${count}"
          headers:
            Authorization: "Bearer ${CUSTOM_PROXY_TOKEN}"
          response_mapping:
            list_field: "data.proxies"
            ip_field: "ip"
            port_field: "port"
          rate_limit:
            requests_per_minute: 10
  
  # ---------- 账号绑定配置 ----------
  binding:
    enabled: true
    sticky: true
    auto_bind: true
    auto_rebind: true
    
    exclusive:
      enabled: false
      max_bindings_per_proxy: 3
    
    similarity:
      prefer_same_region: true
      prefer_same_isp: true
      min_similarity_score: 0.5
    
    verify:
      enabled: true
      interval: 300
      on_failure_rebind: true
  
  # ---------- 质量评估配置 ----------
  quality:
    enabled: true
    
    evaluation:
      window_size: 100
      min_samples: 10
    
    thresholds:
      min_success_rate: 0.7
      max_avg_response_time: 5000
      max_consecutive_failures: 5
    
    score_weights:
      success_rate: 0.6
      response_time: 0.3
      stability: 0.1
    
    auto_retire:
      enabled: true
      check_interval: 300
      min_quality_score: 40
      grace_period: 600
  
  # ---------- 故障转移配置 ----------
  failover:
    enabled: true
    strategy: circuit_breaker
    
    retry:
      max_attempts: 3
      delay: 1000
      backoff_multiplier: 2
    
    circuit_breaker:
      failure_threshold: 5
      success_threshold: 3
      timeout: 300
      half_open_requests: 3
  
  # ---------- 统计配置 ----------
  statistics:
    enabled: true
    
    collector:
      buffer_size: 100
      flush_interval: 60
    
    retention:
      detailed_logs_days: 7
      daily_stats_days: 90
      samples_days: 3
```

---

## 十、前端界面设计

### 10.1 页面结构

```
WebUI 代理管理模块
├── 代理总览页 (/proxy)
│   ├── 统计卡片区
│   ├── 快速操作区
│   └── 代理列表
│
├── 代理配置页 (/proxy/settings)
│   ├── 基础配置
│   ├── 代理源配置
│   ├── 质量评估配置
│   └── 故障转移配置
│
├── 账号绑定页 (/proxy/bindings)
│   ├── 绑定列表
│   ├── 批量绑定
│   └── 绑定规则配置
│
├── 代理导入页 (/proxy/import)
│   ├── 文件上传
│   ├── API配置
│   └── 导入预览
│
└── 统计报表页 (/proxy/statistics)
    ├── 使用趋势图
    ├── 质量分布图
    └── 成本分析
```

### 10.2 代理总览页

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  代理管理                                                    [+ 添加代理]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   总代理数   │  │   可用代理   │  │  已绑定账号  │  │  平均质量分  │        │
│  │     128     │  │     96      │  │     45      │  │    87.5     │        │
│  │   ↑12 今日  │  │   ↓3 今日   │  │   ↑8 今日   │  │   ↑2.3%    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  快速操作                                                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ 导入代理  │ │ 验证全部  │ │ 清理失效  │ │ 批量绑定  │ │ 导出报表  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  代理列表                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 筛选: [来源 ▼] [协议 ▼] [状态 ▼] [地区 ▼]        搜索: [________]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────┬────────────────┬──────┬──────┬──────┬───────┬───────┬─────────┐  │
│  │ ☐  │ 代理地址        │ 协议  │ 来源  │ 地区  │ 质量分 │ 绑定数  │ 操作    │  │
│  ├─────┼────────────────┼──────┼──────┼──────┼───────┼───────┼─────────┤  │
│  │ ☐  │ 192.168.1.1:80 │ HTTP │ 快代理│ 北京  │ 95.2  │ 2     │ [详情]  │  │
│  │ ☐  │ 192.168.1.2:10 │SOCKS5│ 本地  │ 上海  │ 88.7  │ 1     │ [详情]  │  │
│  │ ☐  │ 192.168.1.3:80 │ HTTP │自定义 │ 广州  │ 72.3  │ 0     │ [详情]  │  │
│  │ ☐  │ 192.168.1.4:80 │ HTTP │ 豌豆  │ 深圳  │ ⚠ 45.1│ 0     │ [详情]  │  │
│  └─────┴────────────────┴──────┴──────┴──────┴───────┴───────┴─────────┘  │
│                                                                             │
│  [批量删除] [批量验证]                              共 128 条 < 1 2 3 ... >  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.3 账号-代理绑定页

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  账号-代理绑定                                              [批量绑定]       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   总账号数   │  │   已绑定    │  │   未绑定    │  │  绑定异常   │        │
│  │     56      │  │     45      │  │     8       │  │     3       │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  筛选: [平台 ▼] [绑定状态 ▼]                          搜索: [________]      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────┬────────────┬──────┬─────────────────┬───────┬──────┬──────────┐  │
│  │ ☐  │ 账号        │ 平台  │ 绑定代理         │ 状态   │ 绑定时间│ 操作     │  │
│  ├─────┼────────────┼──────┼─────────────────┼───────┼──────┼──────────┤  │
│  │ ☐  │ xhs_001    │ 小红书│ 192.168.1.1:80  │ ✓正常 │ 3天前 │[换绑][解绑]│  │
│  │ ☐  │ xhs_002    │ 小红书│ 192.168.1.2:80  │ ✓正常 │ 2天前 │[换绑][解绑]│  │
│  │ ☐  │ dy_001     │ 抖音  │ 192.168.1.3:80  │ ⚠异常 │ 5天前 │[换绑][解绑]│  │
│  │ ☐  │ dy_002     │ 抖音  │ --未绑定--       │ --    │ --    │ [绑定]    │  │
│  │ ☐  │ wb_001     │ 微博  │ 192.168.1.5:80  │ ✓正常 │ 1天前 │[换绑][解绑]│  │
│  └─────┴────────────┴──────┴─────────────────┴───────┴──────┴──────────┘  │
│                                                                             │
│  [批量绑定] [批量解绑] [批量验证] [自动修复异常]        共 56 条 < 1 2 3 >   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.4 代理配置页

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  代理配置                                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ 基础配置 ──────────────────────────────────────────────────────────┐   │
│  │  启用代理          [✓] 开启                                          │   │
│  │  代理池大小        [  10  ] 个    (最小可用数量: [ 3 ] 个)            │   │
│  │  存储方式          (•) SQLite  ( ) JSON文件  ( ) MySQL               │   │
│  │  支持协议          [✓] HTTP  [✓] HTTPS  [✓] SOCKS5                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ 代理来源配置 ──────────────────────────────────────────────────────┐   │
│  │  来源优先级（拖拽排序）:                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ ≡ 1. 本地文件        [✓启用]  [配置]                         │    │   │
│  │  │ ≡ 2. 自定义API       [✓启用]  [配置]                         │    │   │
│  │  │ ≡ 3. 快代理          [ 启用]  [配置]                         │    │   │
│  │  │ ≡ 4. 豌豆HTTP        [ 启用]  [配置]                         │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │  [+ 添加自定义API源]                                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ 账号绑定配置 ──────────────────────────────────────────────────────┐   │
│  │  启用账号绑定      [✓] 开启    (为每个爬虫账号绑定固定代理)           │   │
│  │  粘性绑定          [✓] 开启    (代理失效时优先选择相似代理)           │   │
│  │  自动重新绑定      [✓] 开启    (代理失效时自动重新绑定)               │   │
│  │  代理独占模式      [ ] 开启    (一个代理只能绑定一个账号)             │   │
│  │  绑定验证间隔      [  300  ] 秒                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ 质量评估配置 ──────────────────────────────────────────────────────┐   │
│  │  启用质量评估      [✓] 开启                                          │   │
│  │  最低成功率        [  70  ] %                                        │   │
│  │  最大响应时间      [ 5000 ] ms                                       │   │
│  │  连续失败阈值      [   5  ] 次                                       │   │
│  │  自动淘汰          [✓] 开启                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─ 故障转移配置 ──────────────────────────────────────────────────────┐   │
│  │  启用故障转移      [✓] 开启                                          │   │
│  │  转移策略          [熔断器策略 ▼]                                     │   │
│  │  最大重试次数      [   3  ] 次                                       │   │
│  │  熔断恢复时间      [  300 ] 秒                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                                              [恢复默认]  [保存配置]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.5 统计报表页

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  代理统计                                    时间范围: [最近7天 ▼] [导出]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  总请求数    │  │   成功率    │  │ 平均响应时间 │  │  总流量     │        │
│  │   125,680   │  │   94.5%    │  │   856ms    │  │   2.3GB    │        │
│  │  ↑15% 环比  │  │  ↑2.1%    │  │  ↓120ms   │  │  ↑18%     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  请求趋势图                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ [图表: 折线图显示每日成功/失败请求数]                                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─ 按来源统计 ────────────────────┐  ┌─ 按平台统计 ────────────────────┐  │
│  │ [饼图: 本地文件45%, 快代理30%...] │  │ [饼图: 小红书35%, 抖音28%...]    │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  代理质量分布                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  优秀 (90-100)  ████████████████████████████████████  68个 (53%)     │  │
│  │  良好 (70-89)   ██████████████████████                 32个 (25%)     │  │
│  │  一般 (50-69)   ████████████                           18个 (14%)     │  │
│  │  较差 (<50)     ██████                                 10个 (8%)      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Top 10 代理排行                                                             │
│  ┌─────┬────────────────┬───────┬────────┬─────────┬───────────────────┐  │
│  │排名 │ 代理地址        │ 请求数 │ 成功率  │ 响应时间 │ 质量分             │  │
│  ├─────┼────────────────┼───────┼────────┼─────────┼───────────────────┤  │
│  │ 1   │ 192.168.1.1:80 │ 15,230│ 98.5%  │ 520ms  │ ████████████ 98.2 │  │
│  │ 2   │ 192.168.1.2:80 │ 12,450│ 97.8%  │ 580ms  │ ███████████▌ 96.5 │  │
│  │ ... │ ...            │ ...   │ ...    │ ...    │ ...               │  │
│  └─────┴────────────────┴───────┴────────┴─────────┴───────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.6 React组件结构

```
webui-src/src/
├── pages/
│   └── proxy/
│       ├── index.tsx                    # 代理总览页
│       ├── settings.tsx                 # 代理配置页
│       ├── bindings.tsx                 # 账号绑定页
│       ├── import.tsx                   # 代理导入页
│       └── statistics.tsx               # 统计报表页
│
├── components/
│   └── proxy/
│       ├── ProxyOverview/
│       │   ├── StatsCards.tsx
│       │   ├── QuickActions.tsx
│       │   └── ProxyTable.tsx
│       │
│       ├── ProxySettings/
│       │   ├── BasicSettings.tsx
│       │   ├── SourceSettings.tsx
│       │   ├── BindingSettings.tsx
│       │   ├── QualitySettings.tsx
│       │   └── FailoverSettings.tsx
│       │
│       ├── ProxyBindings/
│       │   ├── BindingTable.tsx
│       │   ├── BindingDetail.tsx
│       │   └── BatchBindModal.tsx
│       │
│       ├── ProxyImport/
│       │   ├── FileUploader.tsx
│       │   ├── ApiConfigModal.tsx
│       │   └── ImportPreview.tsx
│       │
│       └── ProxyStatistics/
│           ├── TrendChart.tsx
│           ├── SourcePieChart.tsx
│           └── QualityDistribution.tsx
│
├── hooks/
│   └── proxy/
│       ├── useProxyList.ts
│       ├── useProxyBindings.ts
│       ├── useProxySettings.ts
│       └── useProxyStatistics.ts
│
├── api/
│   └── proxy.ts
│
└── types/
    └── proxy.ts
```

---

## 十一、API接口设计

### 11.1 代理管理接口

```python
# 代理列表
GET /api/proxy/list
    ?source=kuaidaili|wandou|custom_api|local_file
    &protocol=http|https|socks5
    &is_active=true|false
    &page=1&page_size=20

# 添加代理
POST /api/proxy/add
    {ip, port, protocol, username?, password?, source}

# 批量导入
POST /api/proxy/import
    FormData: file, source

# 验证代理
POST /api/proxy/validate/{proxy_id}
POST /api/proxy/validate/batch
    {proxy_ids: [...]}

# 删除代理
DELETE /api/proxy/{proxy_id}
```

### 11.2 账号绑定接口

```python
# 绑定列表
GET /api/proxy/bindings
    ?platform=xhs|dy|wb|bili
    &status=active|expired|unbound
    &page=1&page_size=20

# 绑定详情
GET /api/proxy/bindings/{account_id}?platform=xhs

# 绑定代理
POST /api/proxy/bindings/bind
    {account_id, platform, proxy_id?, is_sticky?}

# 解除绑定
POST /api/proxy/bindings/unbind
    {account_id, platform}

# 重新绑定
POST /api/proxy/bindings/rebind
    {account_id, platform, prefer_similar?}

# 批量绑定
POST /api/proxy/bindings/batch
    {bindings: [{account_id, platform, proxy_id?}], auto_assign?}

# 验证绑定
POST /api/proxy/bindings/verify
    {account_ids?: [...]}

# 自动修复
POST /api/proxy/bindings/auto-fix

# 绑定历史
GET /api/proxy/bindings/{account_id}/history?platform=xhs
```

### 11.3 配置管理接口

```python
# 获取配置
GET /api/proxy/settings

# 更新配置
PUT /api/proxy/settings
    {settings...}

# 添加自定义API
POST /api/proxy/settings/custom-api
    {name, url, method, params, headers, response_mapping, rate_limit}

# 测试自定义API
POST /api/proxy/settings/custom-api/test
    {config...}
```

### 11.4 统计报表接口

```python
# 统计概览
GET /api/proxy/statistics/overview
    ?start_date=2024-01-01&end_date=2024-01-31

# 趋势数据
GET /api/proxy/statistics/trend
    ?start_date&end_date&granularity=hour|day|week

# 按来源统计
GET /api/proxy/statistics/by-source
    ?start_date&end_date

# 按平台统计
GET /api/proxy/statistics/by-platform
    ?start_date&end_date

# 质量分布
GET /api/proxy/statistics/quality-distribution

# 代理排行
GET /api/proxy/statistics/top-proxies
    ?limit=10&sort_by=quality_score|requests|success_rate

# 导出报表
GET /api/proxy/statistics/export
    ?start_date&end_date&format=csv|excel|json
```

---

## 十二、错误处理设计

### 12.1 异常类定义

```python
# proxy/exceptions.py

class ProxyError(Exception):
    """代理系统基础异常"""

class ProxyNotFoundError(ProxyError):
    """代理不存在"""

class ProxyExpiredError(ProxyError):
    """代理已过期"""

class ProxyValidationError(ProxyError):
    """代理验证失败"""

class ProxyExhaustedError(ProxyError):
    """代理池耗尽"""

class BindingError(ProxyError):
    """绑定相关异常"""

class BindingNotFoundError(BindingError):
    """绑定不存在"""

class BindingConflictError(BindingError):
    """绑定冲突（独占模式下代理已被绑定）"""

class NoAvailableProxyError(ProxyError):
    """无可用代理"""

class CustomApiError(ProxyError):
    """自定义API异常"""

class RateLimitError(ProxyError):
    """API速率限制"""

class FailoverExhaustedError(ProxyError):
    """故障转移耗尽所有重试"""
```

### 12.2 错误处理策略

```python
class ErrorAction(Enum):
    RETRY = "retry"                # 重试
    SWITCH_PROXY = "switch_proxy"  # 切换代理
    REBIND = "rebind"              # 重新绑定
    FAIL = "fail"                  # 直接失败
    IGNORE = "ignore"              # 忽略

# 错误类型 -> 处理动作映射
ERROR_ACTION_MAP = {
    # 网络错误
    "ConnectionError": ErrorAction.SWITCH_PROXY,
    "TimeoutError": ErrorAction.RETRY,
    "ConnectTimeout": ErrorAction.SWITCH_PROXY,
    
    # HTTP错误
    "407": ErrorAction.REBIND,     # Proxy Authentication Required
    "429": ErrorAction.SWITCH_PROXY,  # Too Many Requests
    "502": ErrorAction.RETRY,
    "503": ErrorAction.RETRY,
    
    # 业务错误
    "RateLimitError": ErrorAction.SWITCH_PROXY,
    "BannedError": ErrorAction.REBIND,
}
```

---

## 十三、实现计划

### Phase 1: 基础框架 (Week 1-2)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 代理数据模型重构 (types.py) | P0 | 0.5天 |
| SQLite持久化后端 | P0 | 1天 |
| 本地文件代理加载 | P0 | 1天 |
| 基础绑定管理器 | P0 | 1.5天 |
| 绑定存储层 | P0 | 1天 |
| 单元测试 | P0 | 1天 |

**交付物**: 可以从本地文件加载代理，支持账号-代理绑定持久化

### Phase 2: 质量与故障转移 (Week 3-4)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| SOCKS5协议支持 | P1 | 1天 |
| 质量评估器 | P1 | 1.5天 |
| 质量分计算 | P1 | 0.5天 |
| 自动淘汰机制 | P1 | 1天 |
| 故障转移基础框架 | P1 | 1天 |
| 熔断器策略实现 | P1 | 1天 |
| 集成测试 | P1 | 1天 |

**交付物**: 代理质量评估、自动淘汰、故障转移

### Phase 3: 自定义API与统计 (Week 5-6)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 自定义API Provider | P2 | 2天 |
| API配置解析 | P2 | 1天 |
| 统计收集器 | P2 | 1天 |
| 统计存储与聚合 | P2 | 1天 |
| 报表生成器 | P2 | 1天 |
| 集成测试 | P2 | 1天 |

**交付物**: 自定义API支持、使用统计

### Phase 4: WebUI (Week 7-9)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 后端API接口 | P0 | 2天 |
| 代理总览页 | P1 | 2天 |
| 代理配置页 | P1 | 2天 |
| 账号绑定页 | P1 | 2天 |
| 代理导入页 | P2 | 1.5天 |
| 统计报表页 | P2 | 2天 |
| UI测试 | P1 | 1天 |

**交付物**: 完整的WebUI代理管理界面

### Phase 5: 优化与文档 (Week 10)

| 任务 | 优先级 | 预估时间 |
|------|--------|----------|
| 性能优化 | P1 | 2天 |
| 文档编写 | P1 | 2天 |
| E2E测试 | P2 | 1天 |

**交付物**: 完整文档、性能优化

---

## 十四、测试策略

### 14.1 单元测试

```python
# tests/proxy/test_binding_manager.py

class TestBindingManager:
    """绑定管理器测试"""
    
    async def test_bind_proxy_to_account(self, manager):
        """测试绑定代理到账号"""
        binding = await manager.bind(
            account_id="test_account_001",
            platform="xhs",
            proxy_id="proxy_001"
        )
        assert binding.account_id == "test_account_001"
        assert binding.proxy_id == "proxy_001"
        assert binding.status == "active"
    
    async def test_auto_assign_proxy(self, manager):
        """测试自动分配代理"""
        binding = await manager.bind(
            account_id="test_account_002",
            platform="xhs",
            proxy_id=None  # 自动分配
        )
        assert binding.proxy_id is not None
    
    async def test_exclusive_mode_conflict(self, manager):
        """测试独占模式冲突"""
        manager.exclusive_mode = True
        await manager.bind("account_001", "xhs", "proxy_001")
        
        with pytest.raises(BindingConflictError):
            await manager.bind("account_002", "xhs", "proxy_001")
    
    async def test_rebind_prefers_similar_proxy(self, manager):
        """测试重绑时优先相似代理"""
        binding = await manager.bind("account_001", "xhs", "proxy_beijing_telecom")
        await manager.mark_proxy_invalid("proxy_beijing_telecom")
        new_binding = await manager.rebind("account_001", "xhs")
        
        new_proxy = await manager.get_proxy(new_binding.proxy_id)
        assert new_proxy.province == "北京" or new_proxy.isp == "电信"
```

### 14.2 集成测试

```python
# tests/proxy/test_integration.py

class TestProxyIntegration:
    """代理系统集成测试"""
    
    async def test_full_crawl_flow_with_proxy(self):
        """测试完整爬取流程（带代理）"""
        # 1. 初始化代理池
        # 2. 初始化账号池
        # 3. 获取账号和代理
        # 4. 模拟请求
        # 5. 验证绑定持久化
    
    async def test_failover_on_proxy_failure(self):
        """测试代理失败时的故障转移"""
        # 1. 配置一个会失败的代理
        # 2. 发起请求，预期触发故障转移
        # 3. 验证已切换到新代理
        # 4. 验证绑定已更新
```

### 14.3 E2E测试

```python
# tests/e2e/test_proxy_webui.py

class TestProxyWebUI:
    """WebUI E2E测试"""
    
    async def test_import_proxies_from_file(self, browser):
        """测试从文件导入代理"""
    
    async def test_bind_proxy_to_account(self, browser):
        """测试绑定代理到账号"""
```

---

## 附录A：TypeScript类型定义

```typescript
// webui-src/src/types/proxy.ts

export interface Proxy {
  proxy_id: string;
  ip: string;
  port: number;
  protocol: 'http' | 'https' | 'socks5';
  username?: string;
  password?: string;
  source: 'kuaidaili' | 'wandou' | 'custom_api' | 'local_file';
  region?: string;
  isp?: string;
  is_active: boolean;
  quality_score: number;
  binding_count: number;
  created_at: string;
  expired_at?: string;
}

export interface AccountProxyBinding {
  binding_id: string;
  account_id: string;
  platform: string;
  proxy_id: string;
  proxy?: Proxy;
  is_sticky: boolean;
  status: 'active' | 'expired' | 'unbound';
  bound_at: string;
  last_used_at?: string;
  rebind_count: number;
}

export interface ProxySettings {
  enabled: boolean;
  pool_size: number;
  min_available: number;
  storage_backend: 'json' | 'sqlite' | 'mysql';
  protocols: ('http' | 'https' | 'socks5')[];
  
  source_priority: string[];
  custom_apis: CustomApiConfig[];
  
  binding: {
    enabled: boolean;
    sticky: boolean;
    allow_auto_rebind: boolean;
    exclusive_mode: boolean;
    verify_interval: number;
  };
  
  quality: {
    enabled: boolean;
    min_success_rate: number;
    max_response_time: number;
    auto_retire: boolean;
  };
  
  failover: {
    enabled: boolean;
    strategy: 'simple' | 'sticky' | 'weighted' | 'circuit_breaker';
    max_retries: number;
  };
}

export interface CustomApiConfig {
  name: string;
  url: string;
  method: 'GET' | 'POST';
  params?: Record<string, string>;
  headers?: Record<string, string>;
  response_mapping: {
    list_field?: string;
    ip_field: string;
    port_field: string;
    protocol_field?: string;
    expire_field?: string;
  };
  rate_limit?: {
    requests_per_minute: number;
  };
}

export interface ProxyStatisticsOverview {
  total_proxies: number;
  available_proxies: number;
  bound_accounts: number;
  avg_quality_score: number;
  total_requests: number;
  success_rate: number;
  avg_response_time: number;
  total_traffic_bytes: number;
}
```

---

## 附录B：核心流程图

### 账号获取代理流程

```
Crawler.start()
    │
    ▼
┌─────────────────────┐
│ 1. 获取当前账号      │
│ AccountPool.get()   │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. 查询绑定关系      │
│ BindingManager      │
└─────────────────────┘
    │
    ├── 已有绑定且有效 ──► 返回绑定的代理
    │
    ├── 无绑定 ──► 自动分配新代理
    │
    └── 绑定已过期 ──► 重新绑定（优先相似代理）
    │
    ▼
┌─────────────────────┐
│ 3. 使用代理发起请求  │
└─────────────────────┘
    │
    │ 请求失败
    ▼
┌─────────────────────┐
│ 4. 故障转移处理      │
│ - 重试其他代理      │
│ - 更新绑定关系      │
└─────────────────────┘
```

### 质量评估流程

```
每次请求完成后:
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ 1. 记录请求结果                                            │
│    record_request(proxy_id, success, response_time)       │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ 2. 更新滑动窗口统计                                        │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ 3. 计算质量分                                              │
│    quality_score = success_rate * 60                      │
│                  + response_time_score * 30               │
│                  + stability_score * 10                   │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│ 4. 检查是否需要淘汰                                        │
│    if quality_score < threshold:                          │
│        retire_proxy()                                     │
│        trigger_rebind_for_affected_accounts()             │
└───────────────────────────────────────────────────────────┘
```

---

## 版本历史

| 版本 | 日期 | 作者 | 描述 |
|------|------|------|------|
| v1.0 | 2026-01-28 | - | 初始设计方案 |

