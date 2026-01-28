# MediaCrawler 多任务改造方案

> 版本: v1.0  
> 日期: 2026-01-28  
> 状态: 设计阶段

---

## 0. Review 结论与修订记录（2026-01-28）

本节是对原方案的“可落地性/可扩展性/安全性”review 总结，并给出本次文档修订要点，便于团队对齐。

### 0.1 核心结论（必须补齐的缺口）

1. **进程/资源模型缺失（高风险）**  
   原方案隐含“API Server 内置 Task Executor 并发跑任务”。但爬虫任务通常包含 **Playwright/浏览器、CPU 密集解析、长 I/O**，与 FastAPI/uvicorn 混跑会带来：
   - 事件循环被阻塞，API/WS 卡顿甚至雪崩
   - uvicorn 多 worker 场景下状态不一致（每个 worker 各自一套内存队列/存储）
   - Playwright/浏览器实例争抢，内存与句柄数飙升
   
   **建议：API 与 Worker 解耦**：API 只负责鉴权/入队/查询；Worker 进程（或独立容器）负责拉取队列执行任务。

2. **队列可靠性语义不完整（高风险）**  
   现有 `dequeue() -> Task? (阻塞)` 缺少 “预留/确认（reserve/ack）”、“可见性超时（visibility timeout）”、“至少一次语义与幂等要求”。  
   仅用 `ZADD + BZPOPMIN` 很难覆盖：worker crash、任务丢失/重复、超时回收、取消等关键路径。

3. **任务幂等/重试/取消/超时未闭环（高风险）**  
   多任务并发后，失败重试与重复执行不可避免；必须明确：
   - **任务幂等键**（同一 session+配置是否允许重复创建？）
   - **重试策略**（指数退避/最大重试/不可重试错误）
   - **取消语义**（对执行中的 Playwright 任务如何中断？）
   - **超时与回收**（卡死任务如何回收执行槽与队列租约）

4. **日志与 WebSocket 推送缺少背压与限流（中高风险）**  
   高并发下日志量极大，若 “append_log + WS 全量推送” 不做背压，会导致：
   - Redis/内存被日志撑爆
   - 慢客户端拖垮服务端发送队列
   
   需要明确：日志分级/采样/最大保留、按任务 ring buffer、WS 发送队列、慢客户端丢弃策略。

5. **Session/Cookie 隔离有方向但缺少安全细节（中风险）**  
   “匿名 session_id” 本质是 bearer token：必须有 **随机强度、过期刷新、绑定策略、存储方式（HttpOnly Cookie vs localStorage）**；Cookie 存储也要考虑加密/体积/更新频率。

### 0.2 本次修订做了什么

- 补充 **进程拓扑与组件边界**：API Server 与 Worker 分离，明确单机/分布式路径。
- 将 `ITaskQueue` 扩展为 **reserve/ack/nack + visibility timeout** 的可实现接口；补充 Redis 实现建议。
- 补齐 **任务生命周期**（创建→排队→执行→完成/失败/取消/超时）与 **幂等/重试/取消** 设计要点。
- 增加 **日志/事件背压、限流与保留策略**，避免运行后期 OOM/Redis 爆。
- 增加 **安全与隔离**实践建议（匿名会话、API Key/JWT、Cookie 更新与加密、权限校验点）。

---

## 一、设计目标

### 1.1 核心目标

1. **多任务并发**: 支持同时运行多个爬虫任务
2. **用户隔离**: 支持多用户 Session，任务归属于特定用户
3. **可扩展队列**: 队列支持内存版和 Redis 版，便于分布式扩展
4. **签名服务解耦**: 集成独立签名服务，降低单任务资源消耗

### 1.2 设计原则

- **接口抽象**: 核心组件定义抽象接口，支持多种实现
- **配置驱动**: 通过配置切换不同实现（内存/Redis）
- **向后兼容**: 保留原有 API，新 API 并行提供
- **水平扩展**: 架构支持后续分布式部署

---

## 二、整体架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 整体架构                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │                      SignSrv (独立服务 - 端口 8989)                    │     │
│   │   功能: 小红书/抖音/B站/知乎 请求签名                                   │     │
│   │   模式: JavaScript 纯算 (推荐) 或 Playwright                           │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                       ▲                                         │
│                                       │ HTTP                                    │
│   ┌───────────────────────────────────┴───────────────────────────────────┐     │
│   │                    MediaCrawler API Server (端口 8080)                 │     │
│   │   职责: 鉴权/配额/入队/查询/WS 推送（轻计算）                           │     │
│   │                                                                       │     │
│   │   ┌─────────────────────────────────────────────────────────────┐     │     │
│   │   │                     Session Manager                          │     │     │
│   │   │   - 用户认证 (JWT / API Key / 匿名 Session)                   │     │     │
│   │   │   - Session 存储 (Memory / Redis)                            │     │     │
│   │   │   - 配额与限流 (每用户/每平台)                                │     │     │
│   │   └─────────────────────────────────────────────────────────────┘     │     │
│   │                              │                                        │     │
│   │                              ▼                                        │     │
│   │   ┌─────────────────────────────────────────────────────────────┐     │     │
│   │   │                     Task Manager                             │     │     │
│   │   │   - 创建任务/幂等校验/入队                                     │     │     │
│   │   │   - 查询状态/读取日志                                         │     │     │
│   │   └─────────────────────────────────────────────────────────────┘     │     │
│   │                              │                                        │     │
│   │                              ▼                                        │     │
│   │   ┌─────────────────────────────────────────────────────────────┐     │     │
│   │   │      Queue + Storage + Event Bus (可选 Redis)                │     │     │
│   │   │      - queue: memory/redis                                   │     │     │
│   │   │      - storage: memory/redis/sqlite/mysql                     │     │     │
│   │   │      - events: asyncio/redis pubsub（或基于 storage 拉取）     │     │     │
│   │   └─────────────────────────────────────────────────────────────┘     │     │
│   │                              │                                        │     │
│   │                              ▼                                        │     │
│   │   ┌─────────────────────────────────────────────────────────────┐     │     │
│   │   │                     WebSocket Hub                            │     │     │
│   │   │   - 按 session/task 订阅事件/日志                              │     │     │
│   │   │   - 背压/限流/慢客户端丢弃                                     │     │     │
│   │   └─────────────────────────────────────────────────────────────┘     │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │                 Worker Pool (独立进程/容器，建议)                      │     │
│   │   职责: 取任务->执行->写状态/日志->发布事件                             │     │
│   │                                                                       │     │
│   │   ┌─────────────────────────────────────────────────────────────┐     │     │
│   │   │                Task Executor (每个 worker 内)                │     │     │
│   │   │   - 并发控制: 全局/用户/平台 semaphore + rate limit           │     │     │
│   │   │   - Playwright/浏览器资源池/隔离                               │     │     │
│   │   │   - 超时/取消/租约续期 (heartbeat)                             │     │     │
│   │   └─────────────────────────────────────────────────────────────┘     │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件说明

| 组件 | 职责 | 抽象接口 | 实现 |
|------|------|----------|------|
| **Session Manager** | 用户认证、Session 管理 | `ISessionStore` | Memory / Redis |
| **Task Queue** | 任务排队、优先级调度 | `ITaskQueue` | Memory / Redis |
| **Task Storage** | 任务状态、日志持久化 | `ITaskStorage` | Memory / Redis / DB |
| **Task Executor** | 任务执行、并发控制 | - | Worker 内组件 |
| **Event Bus** | 事件发布订阅 | `IEventBus` | Asyncio / Redis Pub/Sub |

### 2.3 执行与进程模型（落地约束）

#### 2.3.1 为什么必须引入 Worker

- **FastAPI/uvicorn 适合处理短请求**；爬虫任务通常是分钟级甚至小时级，混跑会导致接口不可用。  
- **uvicorn 多 worker** 会让 “内存队列/内存存储” 变成多份孤岛状态；同一任务的状态与 WS 推送会错乱。  
- **Playwright/Chromium** 对并发与资源占用敏感：需要明确的资源池与隔离策略。

#### 2.3.2 推荐形态

- **单机起步**：`API进程 + 1..N 个 Worker 进程`（同一台机器）  
- **分布式扩展**：`API 多副本 + Worker 多副本 + Redis(Queue/Storage/Event)`  

> 备注：即使 Phase 1/2 先做 memory 版，也建议 Worker 与 API 进程分离，以免后续迁移成本指数增长。

---

## 三、用户 Session 设计

### 3.1 Session 模型

```
┌─────────────────────────────────────────────────────────────────┐
│                        Session 模型                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Session {                                                     │
│       session_id: string       // 唯一标识 (UUID)               │
│       user_id: string          // 用户ID (可选，支持匿名)        │
│       created_at: datetime     // 创建时间                      │
│       expires_at: datetime     // 过期时间                      │
│       last_active: datetime    // 最后活跃时间                   │
│                                                                 │
│       // 用户配置                                                │
│       preferences: {                                            │
│           default_platform: string                              │
│           default_save_option: string                           │
│           cookies: Map<platform, string>   // 各平台登录态       │
│       }                                                         │
│                                                                 │
│       // 配额限制                                                │
│       quota: {                                                  │
│           max_concurrent_tasks: int    // 最大并发任务数         │
│           max_daily_tasks: int         // 每日任务上限           │
│           used_daily_tasks: int        // 今日已用               │
│       }                                                         │
│   }                                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 认证方式

| 方式 | 适用场景 | 说明 |
|------|----------|------|
| **匿名 Session** | 单用户/本地使用 | 自动创建，存储在浏览器 localStorage |
| **API Key** | 服务端调用 | 预生成的密钥，适合自动化脚本 |
| **JWT Token** | 多用户系统 | 标准 JWT 认证，支持用户注册登录 |

#### 3.2.1 安全建议（匿名 Session 的关键点）

- **匿名 session_id 是 bearer token**：建议由服务端生成高强度随机值（>=128bit），并设置明确过期与刷新策略。  
- **存储位置优先级**：推荐 **HttpOnly + Secure Cookie**（降低 XSS 风险），其次才是 localStorage。  
- **绑定策略（可选）**：可绑定 user-agent 指纹/来源 IP 段（注意移动网络漂移），用于降低盗用风险。  
- **权限校验点**：所有 `/api/tasks/*` 与 `/ws/*` 必须校验 `task.session_id == current_session_id`。

### 3.3 Session 存储接口

```
ISessionStore (抽象接口)
├── create(user_id?) -> Session
├── get(session_id) -> Session?
├── update(session_id, data) -> bool
├── delete(session_id) -> bool
├── refresh(session_id) -> bool        // 刷新过期时间
├── get_by_user(user_id) -> Session[]  // 获取用户所有会话
└── cleanup_expired() -> int           // 清理过期会话

实现:
├── MemorySessionStore   // 内存存储，适合单机
└── RedisSessionStore    // Redis 存储，适合分布式
```

### 3.4 用户隔离策略

```
┌─────────────────────────────────────────────────────────────────┐
│                       用户隔离策略                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   1. 任务归属                                                    │
│      - 每个任务关联 session_id                                   │
│      - 用户只能查看/操作自己的任务                                │
│                                                                 │
│   2. 资源隔离                                                    │
│      - 每用户独立的并发配额                                       │
│      - 每用户独立的日志队列                                       │
│                                                                 │
│   3. 数据隔离                                                    │
│      - 爬取数据按 session_id 分目录存储                          │
│      - 数据库记录关联 session_id                                 │
│                                                                 │
│   4. Cookie 隔离                                                 │
│      - 各平台 Cookie 存储在 Session 中                           │
│      - 不同用户可使用不同账号登录同一平台                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.4.1 Cookie/登录态存储建议（尤其是 Redis 版）

- **不要无上限地把整段 Cookie 放进 Session**（体积大、更新频繁、写放大）。推荐：
  - Session 里只存 **cookie_ref**（引用）+ 最近更新时间
  - Cookie 内容落在 `ITaskStorage/独立 KV/DB`，并做 **加密（AES-GCM）+ 压缩**  
- **更新策略**：只在登录态变更时写入；WS/轮询请求不要反复刷新 cookie 字段，避免热点写。

---

## 四、任务队列设计

### 4.1 队列抽象接口

```
ITaskQueue (抽象接口)
│
├── 基础操作
│   ├── enqueue(task, priority?) -> bool      // 入队
│   ├── reserve(timeout?) -> TaskLease?       // 预留/取出(阻塞)，返回租约
│   ├── peek() -> Task?                       // 查看队首
│   ├── remove(task_id) -> bool               // 移除指定任务
│   └── size() -> int                         // 队列长度
│
├── 确认与回收（可靠性语义）
│   ├── ack(lease_id) -> bool                 // 执行成功确认
│   ├── nack(lease_id, reason, retry?) -> bool// 执行失败确认（可触发重试/死信）
│   ├── heartbeat(lease_id, extend_seconds) -> bool // 续租/防止超时回收
│   └── reclaim_expired_leases() -> int       // 回收超时租约（worker 崩溃场景）
│
├── 优先级支持
│   ├── enqueue_with_priority(task, priority) // 按优先级入队
│   └── reorder(task_id, new_priority)        // 调整优先级
│
├── 延迟任务
│   ├── enqueue_delayed(task, delay_seconds)  // 延迟入队
│   └── get_delayed_count() -> int            // 延迟任务数
│
├── 死信队列
│   ├── move_to_dead_letter(task_id, reason)  // 移入死信队列
│   ├── get_dead_letters() -> Task[]          // 获取死信任务
│   └── retry_dead_letter(task_id) -> bool    // 重试死信任务
│
└── 监控
    ├── get_stats() -> QueueStats             // 队列统计
    └── health_check() -> bool                // 健康检查
```

> 说明：`reserve/ack/nack/lease` 是多 worker 下“至少一次投递”的标准语义。任务可能会重复执行，因此 **任务逻辑必须幂等**（见 5.4/5.5）。

### 4.2 内存队列实现

```
MemoryTaskQueue
│
├── 数据结构
│   ├── priority_queue: PriorityQueue        // 优先级队列 (heapq)
│   ├── delayed_tasks: Dict[task_id, (time, task)]  // 延迟任务
│   ├── dead_letters: List[Task]             // 死信队列
│   └── task_index: Dict[task_id, Task]      // 快速查找索引
│
├── 特点
│   ├── 零依赖，开箱即用
│   ├── 性能最优，无网络开销
│   └── 重启后数据丢失
│
└── 适用场景
    └── 单机部署，开发测试
```

### 4.3 Redis 队列实现

```
RedisTaskQueue
│
├── 数据结构
│   方案 A（推荐，可靠性更强）: Redis Streams
│   ├── STREAM: task_stream:{session_id}      // 任务流
│   ├── CG: worker_group:{session_id}         // consumer group
│   ├── PEL: pending entries                  // 自动支持 pending/重投递
│   └── LIST: dead_letter:{session_id}        // 死信队列（可选）
│
│   方案 B（实现更轻）: ZSET + processing（需要 Lua 保证原子）
│   ├── ZSET: ready:{session_id}              // 可执行任务（score=priority+ts）
│   ├── ZSET: delayed:{session_id}            // 延迟任务（score=ready_time）
│   ├── ZSET: processing:{session_id}         // 执行中租约（score=lease_expire_at）
│   ├── HASH: task:{task_id}                  // 任务详情/状态（小对象）
│   └── LIST: dead_letter:{session_id}        // 死信队列
│
├── 特点
│   ├── 支持分布式部署
│   ├── 数据持久化
│   ├── 原子操作保证
│   └── 需要 Redis 依赖
│
├── 关键实现
│   ├── Streams: XADD/XREADGROUP/XACK + XPENDING/XCLAIM 做超时回收
│   ├── ZSET+processing: reserve/ack/nack/heartbeat 全部用 Lua 脚本原子化
│   └── 延迟: 定时将 delayed 中到期任务搬运到 ready（或 reserve 时顺便搬运）
│
└── 适用场景
    └── 生产环境，分布式部署
```

### 4.4 可靠性语义（必须明确）

- **投递语义**：至少一次（at-least-once）。worker 崩溃/超时会导致任务被回收并再次执行。  
- **幂等要求**：同一 `task_id` 的执行必须可重复（写 DB/写文件要么幂等要么具备去重/事务）。  
- **可见性超时**：租约到期后任务可被其他 worker 重新 `reserve`。  
- **取消**：对 `ready` 里的任务可直接 `remove(task_id)`；对 `processing` 里的任务需要设置 `cancel_requested=true` 并由 worker 及时中断。  
- **心跳续租**：长任务必须周期性 `heartbeat`，避免被误回收导致并发重复执行。

### 4.5 队列配置

```yaml
# config/queue.yaml

queue:
  # 队列类型: memory / redis
  type: memory
  
  # 内存队列配置
  memory:
    max_size: 1000              # 最大队列长度
    dead_letter_max: 100        # 死信队列最大长度
  
  # Redis 队列配置
  redis:
    host: localhost
    port: 6379
    db: 0
    password: ""
    key_prefix: "mc:queue:"     # Key 前缀
    
  # 通用配置
  common:
    default_priority: 5         # 默认优先级 (1-10)
    max_retries: 3              # 最大重试次数
    retry_delay: 60             # 重试延迟(秒)
    task_timeout: 3600          # 任务超时(秒)
```

---

## 五、任务存储设计

### 5.1 存储抽象接口

```
ITaskStorage (抽象接口)
│
├── 任务 CRUD
│   ├── create(task) -> task_id
│   ├── get(task_id) -> Task?
│   ├── update(task_id, data) -> bool
│   ├── delete(task_id) -> bool
│   └── exists(task_id) -> bool
│
├── 批量操作
│   ├── get_by_session(session_id, filters?) -> Task[]
│   ├── get_by_status(status) -> Task[]
│   └── bulk_update_status(task_ids, status) -> int
│
├── 日志存储
│   ├── append_log(task_id, log_entry) -> bool
│   ├── get_logs(task_id, limit?, offset?) -> LogEntry[]
│   └── clear_logs(task_id) -> bool
│
├── 统计查询
│   ├── count_by_status(session_id?) -> Dict[status, int]
│   ├── get_recent_tasks(session_id, limit) -> Task[]
│   └── get_task_metrics(task_id) -> TaskMetrics
│
└── 维护
    ├── cleanup_old_tasks(days) -> int    // 清理旧任务
    └── archive_task(task_id) -> bool     // 归档任务
```

### 5.2 存储实现对比

| 实现 | 持久化 | 查询能力 | 性能 | 适用场景 |
|------|--------|----------|------|----------|
| **MemoryStorage** | ❌ | 基础 | ⭐⭐⭐⭐⭐ | 开发测试 |
| **RedisStorage** | ✅ | 中等 | ⭐⭐⭐⭐ | 生产单机 |
| **SQLiteStorage** | ✅ | 强 | ⭐⭐⭐ | 生产单机 |
| **MySQLStorage** | ✅ | 强 | ⭐⭐⭐ | 生产分布式 |

### 5.3 任务数据模型

```
Task {
    // 基础信息
    task_id: string              // 任务ID (UUID)
    session_id: string           // 所属会话
    task_name: string?           // 任务名称 (可选)
    
    // 状态
    status: TaskStatus           // pending/running/completed/failed/cancelled
    priority: int                // 优先级 1-10
    retry_count: int             // 已重试次数
    idempotency_key: string?     // 幂等键（可选，但强烈建议）
    
    // 时间
    created_at: datetime
    scheduled_at: datetime?      // 计划执行时间
    started_at: datetime?
    finished_at: datetime?
    last_heartbeat_at: datetime? // worker 心跳（用于超时检测/展示）
    
    // 配置
    config: {
        platform: string
        crawler_type: string
        keywords: string?
        creator_ids: string?
        // ... 其他爬虫配置
    }
    
    // 进度
    progress: {
        current: int
        total: int
        percentage: int
        items_crawled: int
        comments_crawled: int
    }
    
    // 结果
    result: {
        success: bool
        error_message: string?
        output_path: string?
        statistics: object?
    }
    
    // 元数据
    metadata: {
        sign_server_used: bool
        execution_node: string?   // 分布式时的执行节点
        resource_usage: object?
    }
}
```

### 5.4 存储与一致性建议（避免“状态对不上”）

- **状态写入顺序**：优先写 `storage.update(status=running, started_at=...)`，再开始执行；结束时写 `finished_at` 与终态。  
- **幂等更新**：`update()` 需支持基于版本号/乐观锁（或 compare-and-set），避免重复执行的 worker 把状态回滚。  
- **输出路径规范**：以 `session_id/task_id` 做目录前缀，避免并发写同一路径。  

### 5.5 日志存储（背压与成本控制）

建议将日志分为两条路径：

- **实时路径（WS 推送）**：worker 写入内存/Redis 的 **ring buffer**（每 task 例如 2k 行或 5MB 上限），并推送事件。  
- **持久化路径（可选）**：仅存 WARN/ERROR 或阶段性摘要（避免把 Redis/MySQL 当 ELK）。  

必须定义：
- 单任务日志最大保留（行数/字节）
- 单 session 总日志上限（避免一个用户打爆）
- 慢客户端策略：发送队列满则丢弃 DEBUG/INFO，只保留 WARN/ERROR + 最新 N 行

---

## 六、事件总线设计

### 6.1 事件类型

```
TaskEvent {
    event_id: string
    event_type: EventType
    task_id: string
    session_id: string
    timestamp: datetime
    payload: object
}

EventType:
├── TASK_CREATED        // 任务创建
├── TASK_QUEUED         // 任务入队
├── TASK_STARTED        // 任务开始执行
├── TASK_PROGRESS       // 任务进度更新
├── TASK_LOG            // 任务日志
├── TASK_COMPLETED      // 任务完成
├── TASK_FAILED         // 任务失败
├── TASK_CANCELLED      // 任务取消
└── TASK_RETRYING       // 任务重试
```

### 6.2 事件总线接口

```
IEventBus (抽象接口)
│
├── 发布
│   ├── publish(event) -> bool
│   └── publish_batch(events) -> int
│
├── 订阅
│   ├── subscribe(event_type, handler) -> subscription_id
│   ├── subscribe_task(task_id, handler) -> subscription_id
│   ├── subscribe_session(session_id, handler) -> subscription_id
│   └── unsubscribe(subscription_id) -> bool
│
└── 管理
    ├── get_subscribers_count(event_type) -> int
    └── clear_subscriptions(session_id) -> int
```

### 6.3 实现方案

```
AsyncioEventBus (内存版)
├── 使用 asyncio.Queue 实现
├── 订阅者存储在内存 Dict 中
└── 适合单机部署

RedisEventBus (分布式版)
├── 使用 Redis Pub/Sub 实现
├── 支持跨进程/跨机器订阅
└── 适合分布式部署
```

### 6.4 事件/日志推送的背压策略（必做）

- **WS 发送队列**：每个连接维护有界队列（例如 256 条），满了就丢弃低优先级事件。  
- **事件合并**：`TASK_PROGRESS` 可做合并（只保留最新进度），降低风暴。  
- **订阅粒度**：默认按 task 订阅；按 session 全量订阅需要分页/限速。  
- **降级路径**：当 WS 不可用时，客户端可定时拉取 `/api/tasks/{task_id}/logs` 与任务状态。

---

## 七、并发控制设计

### 7.1 多层并发控制

```
┌─────────────────────────────────────────────────────────────────┐
│                      并发控制层次                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Layer 1: 全局并发限制                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  GlobalSemaphore(max=10)                                │   │
│   │  限制整个系统同时运行的任务总数                           │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│   Layer 2: 用户并发限制                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  UserSemaphore[session_id](max=3)                       │   │
│   │  限制单个用户同时运行的任务数                             │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│   Layer 3: 平台并发限制                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  PlatformSemaphore[platform](max=2)                     │   │
│   │  限制同一平台同时运行的任务数，避免触发反爬               │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│   Layer 4: 请求频率限制                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  RateLimiter[platform](requests_per_minute=30)          │   │
│   │  限制对目标平台的请求频率                                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 7.1.1 额外建议：把“并发”与“频率”拆开

- Semaphore 解决的是“同时运行多少个任务/请求”，但反爬更多是 **请求频率**。建议对每平台实现 **令牌桶/漏桶 RateLimiter**（内存版用 asyncio，Redis 版用 Lua/INCR+EXPIRE）。  
- Playwright 类任务建议设置更严格的并发上限，并引入 **浏览器上下文池** 或 “每任务独立 browser + 上限”。  
- 如果平台存在“账号级限频”，建议把限频维度从 `platform` 扩展到 `platform + account_id`。

### 7.2 并发配置

```yaml
# config/concurrency.yaml

concurrency:
  # 全局限制
  global:
    max_concurrent_tasks: 10      # 系统最大并发任务数
    
  # 用户限制
  user:
    default_max_concurrent: 3     # 默认用户并发数
    premium_max_concurrent: 5     # 高级用户并发数
    
  # 平台限制
  platform:
    xhs:
      max_concurrent: 2
      requests_per_minute: 30
    dy:
      max_concurrent: 2
      requests_per_minute: 20
    bili:
      max_concurrent: 3
      requests_per_minute: 60
    wb:
      max_concurrent: 2
      requests_per_minute: 30
    wechat:
      max_concurrent: 3
      requests_per_minute: 60
```

---

## 八、API 设计

### 8.1 认证相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/session` | 创建/获取匿名 Session |
| POST | `/api/auth/login` | 用户登录 (可选) |
| POST | `/api/auth/logout` | 用户登出 |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 8.2 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/` | 创建任务 |
| GET | `/api/tasks/` | 获取任务列表 (当前用户) |
| GET | `/api/tasks/stats` | 获取任务统计 |
| GET | `/api/tasks/{task_id}` | 获取任务详情 |
| GET | `/api/tasks/{task_id}/logs` | 获取任务日志 |
| POST | `/api/tasks/{task_id}/cancel` | 取消任务 |
| POST | `/api/tasks/{task_id}/retry` | 重试任务 |
| DELETE | `/api/tasks/{task_id}` | 删除任务 |
| PATCH | `/api/tasks/{task_id}/priority` | 调整优先级 |

#### 8.2.1 建议补充的接口（实用且省坑）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tasks/dedup` | 使用幂等键创建任务（重复则返回已有 task） |
| POST | `/api/tasks/{task_id}/heartbeat` | （可选）worker 心跳上报/续租 |
| GET  | `/api/tasks/{task_id}/events` | 拉取事件（无 WS 环境下兜底） |

### 8.3 WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/tasks/{task_id}/logs` | 订阅特定任务日志 |
| `/ws/session/logs` | 订阅当前用户所有任务日志 |
| `/ws/session/events` | 订阅当前用户任务事件 |

#### 8.3.1 WS 鉴权与权限校验

- WS 握手时必须做鉴权（cookie/token），并在订阅时校验 `session_id/task_id` 归属。  
- 建议对 session 级订阅设置限速与最大并发连接数（默认 1~3）。  

### 8.4 管理接口 (可选)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/tasks` | 获取所有任务 (管理员) |
| GET | `/api/admin/sessions` | 获取所有会话 |
| GET | `/api/admin/queue/stats` | 队列统计 |
| POST | `/api/admin/queue/pause` | 暂停队列 |
| POST | `/api/admin/queue/resume` | 恢复队列 |

---

## 九、配置体系

### 9.1 配置文件结构

```
config/
├── base.yaml           # 基础配置
├── queue.yaml          # 队列配置
├── storage.yaml        # 存储配置
├── concurrency.yaml    # 并发配置
├── session.yaml        # Session 配置
└── sign_server.yaml    # 签名服务配置
```

### 9.2 环境变量覆盖

```bash
# 支持通过环境变量覆盖配置
MC_QUEUE_TYPE=redis
MC_REDIS_HOST=redis.example.com
MC_MAX_CONCURRENT=5
MC_SIGN_SERVER_URL=http://sign.example.com:8989
```

### 9.3 配置优先级

```
环境变量 > 配置文件 > 默认值
```

---

## 十、部署架构

### 10.1 单机部署 (推荐起步)

```
┌─────────────────────────────────────────────────────────────────┐
│                        单机部署                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Docker Compose                        │   │
│   │                                                         │   │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│   │   │  SignSrv    │  │  API Server │  │  Worker(1)  │  │   WebUI     │    │   │
│   │   │  :8989      │  │  :8080      │  │             │  │  :5173      │    │   │
│   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│   │                                                         │   │
│   │   存储/队列: Memory（起步）或 Redis（推荐尽早切）           │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   资源需求: 2 CPU, 4GB RAM                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 生产部署 (Redis 版)

```
┌─────────────────────────────────────────────────────────────────┐
│                       生产部署 (Redis)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐     │
│   │                      Nginx                             │     │
│   │              (负载均衡 + SSL 终止)                      │     │
│   └───────────────────────────────────────────────────────┘     │
│                              │                                   │
│              ┌───────────────┼───────────────┐                   │
│              ▼               ▼               ▼                   │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│   │ API Server  │ │ API Server  │ │ API Server  │               │
│   │  (Node 1)   │ │  (Node 2)   │ │  (Node 3)   │               │
│   └─────────────┘ └─────────────┘ └─────────────┘               │
│              │               │               │                   │
│              └───────────────┼───────────────┘                   │
│                              ▼                                   │
│              ┌───────────────────────────────┐                   │
│              │           Redis               │                   │
│              │  (Queue + Storage + PubSub)   │                   │
│              └───────────────────────────────┘                   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                   │
│              ▼               ▼               ▼                   │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│   │  SignSrv    │ │  SignSrv    │ │  SignSrv    │               │
│   │  (备用)     │ │  (主)       │ │  (备用)     │               │
│   └─────────────┘ └─────────────┘ └─────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 十一、执行计划

### Phase 0: 准备工作 (1天)

| 任务 | 产出 |
|------|------|
| 部署并验证签名服务 | SignSrv 运行在 8989 端口 |
| 创建功能分支 | `feature/multi-task` |
| 确定配置文件格式 | `config/*.yaml` 模板 |

### Phase 1: 核心抽象层 (2天)

| 任务 | 产出 |
|------|------|
| 定义 ITaskQueue 接口 | `api/interfaces/queue.py` |
| 定义 ITaskStorage 接口 | `api/interfaces/storage.py` |
| 定义 ISessionStore 接口 | `api/interfaces/session.py` |
| 定义 IEventBus 接口 | `api/interfaces/event.py` |
| 定义数据模型 | `api/schemas/task.py`, `session.py` |

### Phase 2: 内存版实现 (3天)

| 任务 | 产出 |
|------|------|
| 实现 MemoryTaskQueue | `api/services/queue/memory.py` |
| 实现 MemoryTaskStorage | `api/services/storage/memory.py` |
| 实现 MemorySessionStore | `api/services/session/memory.py` |
| 实现 AsyncioEventBus | `api/services/event/asyncio.py` |
| 实现 TaskManager | `api/services/task_manager.py` |
| 实现 TaskExecutor（Worker 内） | `api/services/task_executor.py` |
| 增加 Worker 入口（命令行/进程） | `api/worker_main.py` 或 `main.py --worker` |

### Phase 3: API 层 (2天)

| 任务 | 产出 |
|------|------|
| 实现 Session 中间件 | `api/middleware/session.py` |
| 实现 /api/auth 路由 | `api/routers/auth.py` |
| 实现 /api/tasks 路由 | `api/routers/tasks.py` |
| 改造 WebSocket | `api/routers/websocket.py` |
| 集成测试 | `tests/test_api.py` |

### Phase 3.5: 可靠性闭环（强烈建议插入，1-2天）

| 任务 | 产出 |
|------|------|
| 实现 lease/ack/nack + 超时回收 | queue/storage/worker 全链路 |
| 实现取消语义 + worker 中断 | cancel flag + playwright 关闭 |
| 日志 ring buffer + WS 背压 | 运行不爆内存/Redis |

### Phase 4: 签名服务集成 (2天)

| 任务 | 产出 |
|------|------|
| 添加 --sign_server 参数 | `main.py` 改造 |
| 改造 XHS/Douyin Client | 支持远程签名 |
| 联调测试 | 签名服务 + 爬虫 |

### Phase 5: 前端改造 (3天)

| 任务 | 产出 |
|------|------|
| 定义 TypeScript 类型 | `src/types/task.ts` |
| 实现 Session 管理 | `src/hooks/useSession.ts` |
| 实现 tasks API | `src/api/tasks.ts` |
| 实现 TaskList 组件 | `src/components/TaskList.tsx` |
| 实现 TaskDetail 组件 | `src/components/TaskDetail.tsx` |
| 实现 TaskCreate 弹窗 | `src/components/TaskCreate.tsx` |
| 改造 App 布局 | `src/App.tsx` |

### Phase 6: Redis 版实现 (可选, 2天)

| 任务 | 产出 |
|------|------|
| 实现 RedisTaskQueue | `api/services/queue/redis.py` |
| 实现 RedisTaskStorage | `api/services/storage/redis.py` |
| 实现 RedisSessionStore | `api/services/session/redis.py` |
| 实现 RedisEventBus | `api/services/event/redis.py` |
| 配置切换支持 | `api/services/factory.py` |

> 建议：如果目标是“多用户 + 多任务 + 可扩展”，Redis 版其实不是可选项，至少要在进入真实用户之前完成（否则内存版在多进程/重启后体验会很差）。

### Phase 7: 测试与文档 (2天)

| 任务 | 产出 |
|------|------|
| 端到端测试 | 完整流程验证 |
| 并发压力测试 | 性能报告 |
| API 文档 | OpenAPI Spec |
| 用户文档 | 使用说明 |

### 时间线

```
Week 1:
├── Day 1: Phase 0 (准备)
├── Day 2-3: Phase 1 (抽象层)
├── Day 4-6: Phase 2 (内存版)
├── Day 7: Phase 3 开始 (API)

Week 2:
├── Day 8: Phase 3 完成 (API)
├── Day 9-10: Phase 4 (签名服务)
├── Day 11-13: Phase 5 (前端)
├── Day 14: Phase 7 (测试文档)

Week 3 (可选):
├── Day 15-16: Phase 6 (Redis 版)
├── Day 17: 最终测试
```

**核心功能工期: 约 2 周**  
**含 Redis 版: 约 2.5 周**

---

## 十二、风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 签名算法失效 | 中 | 高 | 保留 Playwright 降级方案 |
| 并发导致封禁 | 中 | 中 | 多层并发控制 + 频率限制 |
| 内存泄漏 | 低 | 中 | 日志/任务定期清理 |
| Redis 连接问题 | 低 | 中 | 连接池 + 重试机制 |
| Session 劫持 | 低 | 高 | HTTPS + Token 加密 |
| 任务重复执行 | 中 | 中 | at-least-once + 幂等键 + 乐观锁 |
| 日志/WS 风暴 | 中 | 中 | 背压/限流/采样/保留上限 |
| Playwright 资源爆炸 | 中 | 高 | Worker 隔离 + 并发上限 + 浏览器池/超时 |

---

## 十三、后续扩展

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 定时任务 | P1 | Cron 表达式支持 |
| 任务模板 | P2 | 保存常用配置 |
| Webhook 通知 | P2 | 任务完成回调 |
| 任务依赖 | P3 | DAG 任务编排 |
| 分布式执行 | P3 | 多节点任务分发 |
| 监控告警 | P3 | Prometheus + Grafana |

---

## 附录 A: 目录结构

```
api/
├── interfaces/              # 抽象接口定义
│   ├── __init__.py
│   ├── queue.py            # ITaskQueue
│   ├── storage.py          # ITaskStorage
│   ├── session.py          # ISessionStore
│   └── event.py            # IEventBus
│
├── schemas/                 # 数据模型
│   ├── __init__.py
│   ├── task.py             # Task, TaskCreateRequest, etc.
│   └── session.py          # Session, SessionConfig, etc.
│
├── services/                # 服务实现
│   ├── __init__.py
│   ├── factory.py          # 根据配置创建实例
│   ├── task_manager.py     # 任务管理器
│   ├── task_executor.py    # 任务执行器
│   │
│   ├── queue/              # 队列实现
│   │   ├── __init__.py
│   │   ├── memory.py
│   │   └── redis.py
│   │
│   ├── storage/            # 存储实现
│   │   ├── __init__.py
│   │   ├── memory.py
│   │   └── redis.py
│   │
│   ├── session/            # Session 实现
│   │   ├── __init__.py
│   │   ├── memory.py
│   │   └── redis.py
│   │
│   └── event/              # 事件总线实现
│       ├── __init__.py
│       ├── asyncio.py
│       └── redis.py
│
├── middleware/              # 中间件
│   ├── __init__.py
│   └── session.py          # Session 中间件
│
├── routers/                 # API 路由
│   ├── __init__.py
│   ├── auth.py             # 认证相关
│   ├── tasks.py            # 任务管理
│   └── websocket.py        # WebSocket
│
└── main.py                  # FastAPI 应用入口
```

---

## 附录 B: 配置示例

```yaml
# config/base.yaml

app:
  name: MediaCrawler
  version: 2.0.0
  debug: false

# 组件类型选择
components:
  queue: memory          # memory / redis
  storage: memory        # memory / redis / sqlite
  session: memory        # memory / redis
  event_bus: asyncio     # asyncio / redis

# 签名服务
sign_server:
  enabled: true
  url: http://localhost:8989
  timeout: 10
  
# 并发配置
concurrency:
  global_max: 10
  user_default_max: 3
  platform:
    xhs: { max: 2, rpm: 30 }
    dy: { max: 2, rpm: 20 }
    bili: { max: 3, rpm: 60 }

# Session 配置
session:
  expire_hours: 24
  anonymous_allowed: true
  
# Redis 配置 (当使用 Redis 组件时)
redis:
  host: localhost
  port: 6379
  db: 0
  password: ""
```

---

*文档结束*

