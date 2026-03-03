# MediaCrawler 外部对接指南

面向 AI Agent（如 OpenClaw）和第三方系统的 API 对接文档。

---

## 1. 认证方式

MediaCrawler 支持两种认证方式：

| 方式 | 适用场景 | Header |
|------|---------|--------|
| API Key | 外部系统 / AI Agent / 定时脚本 | `Authorization: Bearer mc_xxx` |
| Session | WebUI 浏览器访问 | `X-Session-ID: xxx` 或 Cookie |

**外部对接请使用 API Key。** 在 WebUI 「系统设置」中创建，或通过已认证的 Session 调用 API 创建。

### 1.1 创建 API Key

```bash
# 通过已有 Session 创建
curl -X POST http://localhost:8080/api/api-keys/ \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenClaw Agent",
    "scopes": ["tasks:*", "schedules:*", "data:*"],
    "rate_limit": 60,
    "expire_days": 90
  }'
```

响应：

```json
{
  "key_id": "abc123",
  "api_key": "mc_xxxxxxxxxxxxxxxxxxxxxxxxx",
  "name": "OpenClaw Agent",
  "scopes": ["tasks:*", "schedules:*", "data:*"],
  "rate_limit": 60,
  "expires_at": "2026-06-01T00:00:00",
  "created_at": "2026-03-03T10:00:00"
}
```

> **重要**：`api_key` 仅在创建时返回一次，请妥善保存。

### 1.2 使用 API Key

后续所有请求带上 Header：

```
Authorization: Bearer mc_xxxxxxxxxxxxxxxxxxxxxxxxx
```

### 1.3 权限范围（Scopes）

| Scope | 说明 |
|-------|------|
| `tasks:*` | 任务的完整读写权限 |
| `tasks:read` | 只读任务 |
| `tasks:write` | 创建/操作任务 |
| `schedules:*` | 定时调度的完整读写权限 |
| `data:*` | 数据导出权限 |
| `*` | 全部权限 |

---

## 2. 核心 API

**Base URL**: `http://localhost:8080`

所有时间字段均为 UTC ISO 8601 格式。

### 2.1 创建一次性任务

```
POST /api/tasks/
```

适用场景：Agent 需要临时爬取某些内容。

**请求体：**

```json
{
  "task_name": "搜索AI绘画相关笔记",
  "config": {
    "platform": "xhs",
    "crawler_type": "search",
    "keywords": ["AI绘画", "Midjourney"],
    "max_notes": 50,
    "enable_comments": true,
    "save_option": "json"
  },
  "priority": 5
}
```

**config 参数说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `platform` | string | 是 | 平台代码：`xhs` / `dy` / `bili` / `wb` / `wechat` / `ks` / `tieba` / `zhihu` |
| `crawler_type` | string | 否 | 爬取模式：`search`(默认) / `creator` / `detail` |
| `keywords` | string[] | 否 | 搜索关键词（search 模式） |
| `creator_ids` | string[] | 否 | 创作者 ID/URL（creator 模式） |
| `note_urls` | string[] | 否 | 内容 URL/ID（detail 模式） |
| `max_notes` | int | 否 | 最大爬取数量，默认 100 |
| `enable_comments` | bool | 否 | 是否爬取评论，默认 false |
| `save_option` | string | 否 | 存储格式：`json`(默认) / `csv` / `excel` / `sqlite` |
| `account_id` | string | 否 | 指定使用的账号 ID（账号管理中创建） |

**响应（201）：**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "platform": "xhs",
  "crawler_type": "search",
  "config": { ... },
  "created_at": "2026-03-03T10:00:00"
}
```

### 2.2 查询任务状态

```
GET /api/tasks/{task_id}
```

**响应：**

```json
{
  "task_id": "550e8400-...",
  "status": "completed",
  "progress": {
    "current": 50,
    "total": 50,
    "percentage": 100,
    "items_crawled": 50
  },
  "result": {
    "success": true,
    "statistics": {}
  },
  "started_at": "2026-03-03T10:00:05",
  "finished_at": "2026-03-03T10:03:20"
}
```

**任务状态 (status)：**

| 值 | 含义 |
|----|------|
| `pending` | 等待执行 |
| `running` | 执行中 |
| `completed` | 已完成 |
| `failed` | 执行失败 |
| `cancelled` | 已取消 |

### 2.3 列出任务

```
GET /api/tasks/?status=completed&platform=xhs&page=1&page_size=20
```

### 2.4 取消任务

```
POST /api/tasks/{task_id}/cancel
```

### 2.5 重试失败任务

```
POST /api/tasks/{task_id}/retry
```

---

## 3. 定时调度 API

适用场景：Agent 创建周期性监控计划（如每天 8:00 自动爬取竞品数据）。

### 3.1 创建定时计划

```
POST /api/schedules/
```

**示例 - 每天 8:00 执行：**

```json
{
  "schedule_name": "每日竞品监控",
  "task_config": {
    "platform": "xhs",
    "crawler_type": "search",
    "keywords": ["竞品分析", "行业趋势"],
    "max_notes": 100,
    "save_option": "json"
  },
  "trigger_type": "cron",
  "cron_expression": "0 8 * * *",
  "timezone": "Asia/Shanghai",
  "webhook_url": "https://your-agent.com/webhook",
  "webhook_secret": "your_hmac_secret_key"
}
```

**示例 - 每 2 小时执行一次：**

```json
{
  "schedule_name": "舆情实时监控",
  "task_config": {
    "platform": "wb",
    "crawler_type": "search",
    "keywords": ["品牌名称"],
    "max_notes": 50
  },
  "trigger_type": "interval",
  "interval_seconds": 7200,
  "webhook_url": "https://your-agent.com/webhook"
}
```

**触发类型 (trigger_type)：**

| 值 | 说明 | 必须参数 |
|----|------|---------|
| `cron` | Cron 定时 | `cron_expression` |
| `interval` | 固定间隔 | `interval_seconds`（最小 60 秒） |
| `once` | 一次性（创建后约 5 秒执行） | 无 |

**常用 Cron 表达式：**

| 表达式 | 含义 |
|--------|------|
| `0 8 * * *` | 每天 8:00 |
| `0 */6 * * *` | 每 6 小时 |
| `0 9 * * 1` | 每周一 9:00 |
| `0 9 * * 1,3,5` | 周一三五 9:00 |
| `30 20 * * *` | 每天 20:30 |

**响应（201）：**

```json
{
  "schedule_id": "660e8400-...",
  "schedule_name": "每日竞品监控",
  "platform": "xhs",
  "trigger_type": "cron",
  "cron_expression": "0 8 * * *",
  "enabled": true,
  "total_runs": 0,
  "next_run_at": "2026-03-04T00:00:00",
  "created_at": "2026-03-03T10:00:00"
}
```

### 3.2 列出调度计划

```
GET /api/schedules/?platform=xhs&enabled_only=true
```

### 3.3 暂停 / 恢复

```
POST /api/schedules/{schedule_id}/pause
POST /api/schedules/{schedule_id}/resume
```

### 3.4 手动触发一次

```
POST /api/schedules/{schedule_id}/trigger
```

响应：

```json
{
  "message": "Schedule triggered",
  "task_id": "770e8400-..."
}
```

### 3.5 更新计划

```
PATCH /api/schedules/{schedule_id}
```

只需传入要修改的字段：

```json
{
  "cron_expression": "0 9 * * *",
  "task_config": {
    "platform": "xhs",
    "keywords": ["新关键词"],
    "max_notes": 200
  }
}
```

### 3.6 删除计划

```
DELETE /api/schedules/{schedule_id}
```

---

## 4. 数据导出 API

### 4.1 导出爬取数据

```
GET /api/data/export?task_id=xxx&format=json&limit=1000
```

| 参数 | 说明 |
|------|------|
| `task_id` | 按任务 ID 过滤 |
| `platform` | 按平台过滤 |
| `format` | 输出格式：`json`(默认) / `csv` |
| `limit` | 最大返回条数，默认 1000 |

**JSON 响应：**

```json
{
  "data": [
    {
      "title": "笔记标题",
      "content": "笔记内容...",
      "likes": 1234,
      "comments": 56,
      "_source_file": "xhs/search_keyword_20260303.json"
    }
  ],
  "total": 50,
  "task_id": "xxx",
  "platform": "xhs"
}
```

**CSV 响应：** 返回 `text/csv`，可直接下载。

### 4.2 浏览数据文件

```
GET /api/data/files?platform=xhs&file_type=json
```

### 4.3 预览文件内容

```
GET /api/data/files/{file_path}?preview=true&limit=100
```

---

## 5. Webhook 回调

当任务完成或失败时，系统会向 Schedule 中配置的 `webhook_url` 发送 HTTP POST 回调。

### 5.1 回调格式

**任务完成 (`task.completed`)：**

```json
{
  "event": "task.completed",
  "timestamp": "2026-03-03T08:05:00Z",
  "data": {
    "task_id": "550e8400-...",
    "schedule_id": "660e8400-...",
    "platform": "xhs",
    "crawler_type": "search",
    "stats": {},
    "result_url": "/api/data/export?task_id=550e8400-...&format=json"
  }
}
```

**任务失败 (`task.failed`)：**

```json
{
  "event": "task.failed",
  "timestamp": "2026-03-03T08:05:00Z",
  "data": {
    "task_id": "550e8400-...",
    "schedule_id": "660e8400-...",
    "error_message": "Cookie expired"
  }
}
```

**调度触发 (`schedule.triggered`)：**

```json
{
  "event": "schedule.triggered",
  "timestamp": "2026-03-03T08:00:00Z",
  "data": {
    "schedule_id": "660e8400-...",
    "schedule_name": "每日竞品监控",
    "task_id": "770e8400-...",
    "platform": "xhs",
    "crawler_type": "search"
  }
}
```

### 5.2 签名验证

如果创建 Schedule 时提供了 `webhook_secret`，每个回调请求会包含签名 Header：

```
X-Webhook-Signature: sha256=abcdef1234567890...
X-Webhook-Event: task.completed
User-Agent: MediaCrawler-Webhook/1.0
```

**Python 验证示例：**

```python
import hmac
import hashlib

def verify_webhook(body: bytes, signature_header: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    received = signature_header.replace("sha256=", "")
    return hmac.compare_digest(expected, received)
```

### 5.3 重试策略

| 重试次数 | 延迟 |
|---------|------|
| 第 1 次 | 2 秒 |
| 第 2 次 | 5 秒 |
| 第 3 次 | 15 秒 |

回调目标返回 2xx 状态码视为成功，否则重试。最多重试 3 次。

---

## 6. 典型对接流程

### 场景 A：Agent 临时爬取（同步轮询）

```
Agent                         MediaCrawler API
  |                                  |
  |-- POST /api/tasks/ ------------->|  创建任务
  |<-------- 201 { task_id } --------|
  |                                  |
  |-- GET /api/tasks/{id} --------->|  轮询状态（建议间隔 5-10 秒）
  |<-------- { status: "running" } --|
  |                                  |
  |-- GET /api/tasks/{id} --------->|
  |<-------- { status: "completed" } |
  |                                  |
  |-- GET /api/data/export -------->|  拉取结果
  |<-------- { data: [...] } --------|
```

### 场景 B：Agent 定时监控（Webhook 推送）

```
Agent                         MediaCrawler API        APScheduler
  |                                  |                     |
  |-- POST /api/schedules/ -------->|                     |
  |   cron: "0 8 * * *"            |-- 注册 Cron Job --->|
  |   webhook_url: "https://..."   |                     |
  |<-------- 201 { schedule_id } ---|                     |
  |                                  |                     |
  |           ... 每天 8:00 ...      |                     |
  |                                  |<-- 触发 ------------|
  |                                  |-- 创建任务+执行 ---->|
  |                                  |                     |
  |<-- Webhook POST -----------------|  任务完成，推送通知    |
  |   { event: "task.completed",    |                     |
  |     data: { result_url: "..." }}|                     |
  |                                  |                     |
  |-- GET /api/data/export -------->|  按需拉取数据         |
  |<-------- { data: [...] } --------|                     |
```

### 场景 C：混合模式

1. Agent 创建 Schedule（每天定时爬竞品）
2. 用户在 WebUI 中查看定时结果、管理账号
3. Agent 偶尔临时发起一次性任务（如用户提问触发）
4. 所有数据统一存储，WebUI 和 API 共享

---

## 7. 支持的平台

| 代码 | 平台 | 支持模式 |
|------|------|---------|
| `xhs` | 小红书 | search, detail, creator |
| `dy` | 抖音 | search, detail, creator |
| `bili` | B站 | search, detail, creator |
| `wb` | 微博 | search, detail, creator, creator_vip |
| `wechat` | 微信公众号 | search, detail, creator, album |
| `ks` | 快手 | search, detail, creator |
| `tieba` | 百度贴吧 | search, detail, creator |
| `zhihu` | 知乎 | search, detail, creator |

---

## 8. 错误处理

所有 API 错误遵循统一格式：

```json
{
  "detail": "错误描述"
}
```

| HTTP 状态码 | 含义 |
|------------|------|
| 400 | 请求参数错误 |
| 401 | 认证失败（API Key 无效或过期） |
| 403 | 权限不足（scope 不匹配） |
| 404 | 资源不存在 |
| 429 | 请求过于频繁（超过 rate_limit） |
| 500 | 服务器内部错误 |

---

## 9. 快速开始示例

### Python

```python
import httpx
import time

BASE_URL = "http://localhost:8080"
API_KEY = "mc_xxxxxxxxxxxxxxxxxxxxxxxxx"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def create_and_wait(keywords: list[str], platform: str = "xhs") -> dict:
    """创建任务并等待完成，返回爬取数据"""
    # 1. 创建任务
    resp = httpx.post(f"{BASE_URL}/api/tasks/", headers=HEADERS, json={
        "task_name": f"搜索: {', '.join(keywords)}",
        "config": {
            "platform": platform,
            "crawler_type": "search",
            "keywords": keywords,
            "max_notes": 50,
            "save_option": "json",
        },
    })
    resp.raise_for_status()
    task_id = resp.json()["task_id"]
    print(f"任务已创建: {task_id}")

    # 2. 轮询等待
    while True:
        resp = httpx.get(f"{BASE_URL}/api/tasks/{task_id}", headers=HEADERS)
        status = resp.json()["status"]
        if status == "completed":
            break
        if status == "failed":
            raise RuntimeError(f"任务失败: {resp.json().get('error_message')}")
        time.sleep(5)

    # 3. 导出数据
    resp = httpx.get(
        f"{BASE_URL}/api/data/export",
        headers=HEADERS,
        params={"task_id": task_id, "format": "json"},
    )
    return resp.json()


# 使用示例
data = create_and_wait(["AI绘画", "Midjourney"])
print(f"共获取 {data['total']} 条数据")
for item in data["data"][:3]:
    print(f"  - {item.get('title', 'N/A')}")
```

### cURL

```bash
# 创建每日定时计划
curl -X POST http://localhost:8080/api/schedules/ \
  -H "Authorization: Bearer mc_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_name": "每日热点监控",
    "task_config": {
      "platform": "xhs",
      "crawler_type": "search",
      "keywords": ["今日热点"],
      "max_notes": 100
    },
    "trigger_type": "cron",
    "cron_expression": "0 8 * * *",
    "webhook_url": "https://your-server.com/webhook",
    "webhook_secret": "my_secret_123"
  }'

# 查看调度列表
curl http://localhost:8080/api/schedules/ \
  -H "Authorization: Bearer mc_xxx"

# 手动触发一次
curl -X POST http://localhost:8080/api/schedules/{schedule_id}/trigger \
  -H "Authorization: Bearer mc_xxx"
```

---

## 10. 交互式文档

API 服务启动后，访问以下地址查看自动生成的交互式文档：

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
