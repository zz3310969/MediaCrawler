# MediaCrawler 代理系统增强使用指南

本文档介绍 MediaCrawler 增强版代理系统的使用方法和配置说明。

## 目录

- [功能概述](#功能概述)
- [快速开始](#快速开始)
- [配置详解](#配置详解)
- [代理来源](#代理来源)
- [账号绑定](#账号绑定)
- [质量评估](#质量评估)
- [故障转移](#故障转移)
- [API接口](#api接口)
- [最佳实践](#最佳实践)

---

## 功能概述

增强版代理系统提供以下功能：

### 核心功能

| 功能 | 说明 |
|------|------|
| **代理持久化** | 支持 SQLite/JSON 存储代理配置 |
| **账号绑定** | 为爬虫账号绑定固定代理，避免IP频繁变化 |
| **质量评估** | 自动记录成功率、响应时间，计算质量分 |
| **故障转移** | 请求失败时自动切换代理，支持多种策略 |
| **自动淘汰** | 自动检测并淘汰低质量代理 |
| **使用统计** | 记录代理使用情况，生成统计报表 |

### 代理来源支持

- ✅ 快代理 (KuaiDaili)
- ✅ 万豆代理 (WanDou)
- ✅ 本地文件 (TXT/JSON/YAML/CSV)
- ✅ 自定义API
- ✅ 手动导入

### 协议支持

- ✅ HTTP/HTTPS
- ✅ SOCKS5
- ✅ SOCKS4

---

## 快速开始

### 1. 配置文件

复制示例配置文件：

```bash
cp config/proxy_config.yaml.example config/proxy_config.yaml
```

### 2. 基本配置

编辑 `config/proxy_config.yaml`：

```yaml
global:
  enable_proxy: true
  enable_binding: true
  auto_rebind: true

sources:
  local_file:
    enabled: true
    file_path: config/proxies.txt
```

### 3. 创建代理列表文件

创建 `config/proxies.txt`：

```text
# 每行一个代理
192.168.1.1:8080
192.168.1.2:8080:user:password
socks5://192.168.1.3:1080
```

### 4. 代码使用

```python
from proxy.proxy_manager import create_proxy_manager

async def main():
    # 创建并启动代理管理器
    manager = await create_proxy_manager()
    
    # 获取代理
    proxy = await manager.get_proxy()
    print(f"获取代理: {proxy.to_url()}")
    
    # 为账号获取代理（自动绑定）
    proxy = await manager.get_proxy_for_account(
        account_id="my_account",
        platform="xhs",
    )
    
    # 记录请求结果
    await manager.record_request_result(
        proxy_id=proxy.proxy_id,
        platform="xhs",
        success=True,
        response_time_ms=150.0,
    )
    
    # 停止
    await manager.stop()
```

---

## 配置详解

### 全局设置

```yaml
global:
  enable_proxy: true          # 启用代理
  proxy_pool_size: 5          # 代理池大小
  validate_on_get: true       # 获取时验证
  validate_timeout: 10        # 验证超时（秒）
  
  # 账号绑定
  enable_binding: true        # 启用绑定
  binding_sticky: true        # 粘性绑定
  auto_rebind: true           # 自动重绑
  max_bindings_per_proxy: 5   # 每代理最大绑定数
  prefer_similar_region: true # 重绑时优先相似地区
```

### 持久化设置

```yaml
persistence:
  backend: sqlite             # 存储后端: sqlite | json
  database_path: data/proxy.db
  json_data_dir: data/proxy
```

### 质量评估设置

```yaml
quality:
  enabled: true
  sample_window: 100          # 样本窗口大小
  time_window_hours: 24       # 统计时间窗口
  min_quality_score: 30       # 最低质量分
  max_consecutive_failures: 10  # 最大连续失败
  
  auto_retire:
    enabled: true
    check_interval_seconds: 300  # 检查间隔（5分钟）
```

### 故障转移设置

```yaml
failover:
  enabled: true
  strategy: circuit_breaker   # 策略选择
  max_retries: 3
  retry_delay_seconds: 1.0
  
  # 熔断器配置
  circuit_breaker:
    failure_threshold: 5      # 熔断阈值
    recovery_timeout_seconds: 60
    half_open_max_calls: 3
```

---

## 代理来源

### 本地文件代理

支持多种格式：

**TXT 格式** (`proxies.txt`)：
```text
# 注释以 # 开头
192.168.1.1:8080
192.168.1.2:8080:user:password
http://192.168.1.3:8080
socks5://192.168.1.4:1080
```

**JSON 格式** (`proxies.json`)：
```json
[
  {"ip": "192.168.1.1", "port": 8080, "protocol": "http"},
  {"ip": "192.168.1.2", "port": 1080, "protocol": "socks5", "user": "admin", "password": "secret"}
]
```

**YAML 格式** (`proxies.yaml`)：
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

### 自定义API代理

```yaml
sources:
  custom_apis:
    - name: my_proxy_api
      enabled: true
      url: https://api.example.com/proxy/get
      method: GET
      headers:
        Authorization: Bearer ${MY_API_TOKEN}
      params:
        count: "{num}"
        format: json
      response_type: json
      data_path: data.list
      field_mapping:
        ip: ip
        port: port
        protocol: type
```

---

## 账号绑定

### 绑定模式

| 模式 | 说明 |
|------|------|
| `auto` | 自动分配代理 |
| `manual` | 手动指定代理 |
| `inherit` | 继承上次绑定 |
| `none` | 不使用代理 |

### 使用示例

```python
# 自动绑定
proxy = await manager.get_proxy_for_account("account_1", "xhs")

# 手动绑定
await manager.bind_proxy("account_1", "xhs", "proxy_id_xxx")

# 解绑
await manager.unbind_proxy("account_1", "xhs")

# 获取绑定列表
bindings = await manager.get_all_bindings(platform="xhs")
```

### 自动重绑定

当绑定的代理失效时，系统会自动重绑定：

1. 优先选择相同地区的代理
2. 其次选择绑定数较少的代理
3. 保持账号IP一致性

---

## 质量评估

### 质量分计算

```
质量分 = 成功率×60 + 响应时间分×30 + 稳定性分×10
```

- **成功率分** (0-60)：`success_rate × 60`
- **响应时间分** (0-30)：响应时间越短分数越高
- **稳定性分** (0-10)：连续失败越少分数越高

### 自动淘汰

满足以下条件的代理会被自动淘汰：

1. 总请求数 >= 20 且 质量分 < 30
2. 连续失败次数 >= 10

---

## 故障转移

### 策略对比

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `simple` | 简单轮换，失败后切换下一个 | 代理质量较好 |
| `sticky` | 粘性策略，尽量使用同一个代理 | 需要IP稳定 |
| `weighted` | 加权选择，质量高的更容易选中 | 代理质量差异大 |
| `circuit_breaker` | 熔断器，连续失败后暂时禁用 | 推荐默认使用 |

### 熔断器状态机

```
CLOSED (正常) 
    ↓ 连续失败达阈值
OPEN (熔断)
    ↓ 经过恢复时间
HALF_OPEN (半开)
    ↓ 测试成功      ↓ 测试失败
CLOSED           OPEN
```

---

## API接口

### 代理管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/proxy/list` | GET | 获取代理列表 |
| `/api/proxy/{id}` | GET | 获取代理详情 |
| `/api/proxy/import` | POST | 批量导入代理 |
| `/api/proxy/{id}` | DELETE | 删除代理 |
| `/api/proxy/{id}/status` | PATCH | 更新代理状态 |

### 绑定管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/proxy/bindings/list` | GET | 获取绑定列表 |
| `/api/proxy/bindings/bind` | POST | 创建绑定 |
| `/api/proxy/bindings/{account}/{platform}` | DELETE | 解除绑定 |

### 统计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/proxy/statistics/overview` | GET | 总览统计 |
| `/api/proxy/statistics/proxy/{id}` | GET | 代理统计 |

---

## 最佳实践

### 1. 代理池大小建议

- 小规模爬取：5-10 个代理
- 中规模爬取：20-50 个代理
- 大规模爬取：100+ 个代理

### 2. 质量管理

- 定期检查淘汰的代理
- 监控成功率和响应时间
- 及时补充新代理

### 3. 账号绑定

- 启用粘性绑定保持IP一致
- 为重要账号手动绑定高质量代理
- 合理设置每代理最大绑定数

### 4. 故障处理

- 使用熔断器策略避免雪崩
- 设置合理的重试次数和延迟
- 监控熔断状态及时处理

### 5. 性能优化

- 使用 SQLite 存储提升性能
- 批量操作减少IO
- 合理设置缓存TTL

---

## 更新日志

### v1.0.0 (2025-01)

- ✅ 实现代理持久化存储
- ✅ 实现账号-代理绑定
- ✅ 实现质量评估和自动淘汰
- ✅ 实现故障转移（含熔断器）
- ✅ 支持SOCKS5协议
- ✅ 支持自定义API代理
- ✅ 支持本地文件代理
- ✅ 实现WebUI管理界面

