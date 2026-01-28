# MediaCrawler 多任务开发文档索引

> 版本: v1.0  
> 日期: 2026-01-28  
> 基于: [MULTI_TASK_DESIGN.md](../MULTI_TASK_DESIGN.md)

---

## 文档清单

| 序号 | 文档 | 对应 Phase | 负责模块 | 预估工期 |
|------|------|-----------|----------|----------|
| 01 | [核心接口定义](./01_INTERFACES.md) | Phase 1 | 抽象层 | 2 天 |
| 02 | [Session 服务](./02_SESSION_SERVICE.md) | Phase 2 | 用户认证/会话管理 | 1 天 |
| 03 | [队列服务](./03_QUEUE_SERVICE.md) | Phase 2/6 | 任务排队/调度 | 1.5 天 |
| 04 | [存储服务](./04_STORAGE_SERVICE.md) | Phase 2/6 | 任务状态/日志持久化 | 1.5 天 |
| 05 | [事件服务](./05_EVENT_SERVICE.md) | Phase 2/6 | 事件发布订阅 | 1 天 |
| 06 | [任务管理器](./06_TASK_MANAGER.md) | Phase 2 | 任务创建/查询/协调 | 1 天 |
| 07 | [Worker 执行器](./07_WORKER.md) | Phase 2/3.5 | 任务执行/并发控制 | 2 天 |
| 08 | [API 路由](./08_API_ROUTES.md) | Phase 3 | HTTP/WebSocket 接口 | 2 天 |
| 09 | [前端开发](./09_FRONTEND.md) | Phase 5 | WebUI 改造 | 3 天 |
| 10 | [签名服务集成](./10_SIGN_SERVER.md) | Phase 4 | SignSrv 对接 | 2 天 |

---

## 开发顺序建议

```
Phase 0 (准备)
    │
    ▼
Phase 1 ─────────────────────────────────────────────────────────
    │  01_INTERFACES.md
    │  定义所有抽象接口与数据模型
    │
    ▼
Phase 2 ─────────────────────────────────────────────────────────
    │  02_SESSION_SERVICE.md (Memory 版)
    │  03_QUEUE_SERVICE.md (Memory 版)
    │  04_STORAGE_SERVICE.md (Memory 版)
    │  05_EVENT_SERVICE.md (Memory 版)
    │  06_TASK_MANAGER.md
    │  07_WORKER.md
    │
    ▼
Phase 3 ─────────────────────────────────────────────────────────
    │  08_API_ROUTES.md
    │
    ▼
Phase 3.5 ───────────────────────────────────────────────────────
    │  可靠性闭环（lease/ack/nack、取消、背压）
    │  涉及 03/04/05/07 文档的"可靠性"章节
    │
    ▼
Phase 4 ─────────────────────────────────────────────────────────
    │  10_SIGN_SERVER.md
    │
    ▼
Phase 5 ─────────────────────────────────────────────────────────
    │  09_FRONTEND.md
    │
    ▼
Phase 6 (可选) ──────────────────────────────────────────────────
    │  Redis 版实现（各服务文档中已包含 Redis 章节）
    │
    ▼
Phase 7 ─────────────────────────────────────────────────────────
    │  测试与文档
```

---

## 目录结构（完成后）

```
api/
├── interfaces/              # Phase 1
│   ├── __init__.py
│   ├── queue.py            # ITaskQueue
│   ├── storage.py          # ITaskStorage
│   ├── session.py          # ISessionStore
│   └── event.py            # IEventBus
│
├── schemas/                 # Phase 1
│   ├── __init__.py
│   ├── task.py             # Task, TaskLease, TaskCreateRequest
│   ├── session.py          # Session, SessionConfig
│   └── event.py            # TaskEvent, EventType
│
├── services/                # Phase 2/6
│   ├── __init__.py
│   ├── factory.py          # 根据配置创建实例
│   ├── task_manager.py     # TaskManager
│   ├── task_executor.py    # TaskExecutor (Worker 内)
│   │
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── memory.py       # MemoryTaskQueue
│   │   └── redis.py        # RedisTaskQueue
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── memory.py       # MemoryTaskStorage
│   │   └── redis.py        # RedisTaskStorage
│   │
│   ├── session/
│   │   ├── __init__.py
│   │   ├── memory.py       # MemorySessionStore
│   │   └── redis.py        # RedisSessionStore
│   │
│   └── event/
│       ├── __init__.py
│       ├── asyncio_bus.py  # AsyncioEventBus
│       └── redis_bus.py    # RedisEventBus
│
├── middleware/              # Phase 3
│   ├── __init__.py
│   └── session.py
│
├── routers/                 # Phase 3
│   ├── __init__.py
│   ├── auth.py
│   ├── tasks.py
│   └── websocket.py
│
├── main.py                  # API 入口
└── worker_main.py           # Worker 入口

webui-src/src/               # Phase 5
├── types/
│   └── task.ts
├── api/
│   └── tasks.ts
├── hooks/
│   └── useSession.ts
├── components/
│   ├── TaskList.tsx
│   ├── TaskDetail.tsx
│   └── TaskCreate.tsx
└── App.tsx
```

---

## 快速导航

### 后端开发

- [接口定义 →](./01_INTERFACES.md)
- [Session 服务 →](./02_SESSION_SERVICE.md)
- [队列服务 →](./03_QUEUE_SERVICE.md)
- [存储服务 →](./04_STORAGE_SERVICE.md)
- [事件服务 →](./05_EVENT_SERVICE.md)
- [任务管理器 →](./06_TASK_MANAGER.md)
- [Worker 执行器 →](./07_WORKER.md)
- [API 路由 →](./08_API_ROUTES.md)

### 前端开发

- [前端开发文档（含原型） →](./09_FRONTEND.md)

### 集成

- [签名服务集成 →](./10_SIGN_SERVER.md)

---

*索引文档结束*

