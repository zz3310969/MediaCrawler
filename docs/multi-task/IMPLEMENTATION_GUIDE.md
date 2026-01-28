# MediaCrawler 多任务系统实现指南

## 快速开始

### 1. 启动 API Server

```bash
# 使用内存后端（开发环境）
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. 启动 Worker

```bash
# 在另一个终端
python -m api.worker_main
```

### 3. 测试 API

```bash
# 创建 Session
curl -X POST http://localhost:8080/api/auth/session

# 创建任务
curl -X POST http://localhost:8080/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -d '{
    "task_name": "测试任务",
    "config": {
      "platform": "xhs",
      "crawler_type": "search",
      "keywords": "护肤品推荐",
      "max_notes": 10
    }
  }'

# 查看任务列表
curl http://localhost:8080/api/tasks/ \
  -H "X-Session-ID: YOUR_SESSION_ID"
```

---

## 目录结构

```
api/
├── interfaces/              # 抽象接口
│   ├── __init__.py
│   ├── queue.py            # ITaskQueue
│   ├── storage.py          # ITaskStorage
│   ├── session.py          # ISessionStore
│   └── event.py            # IEventBus
├── schemas/                 # 数据模型
│   ├── task.py             # Task, TaskLease, etc.
│   ├── session.py          # Session, SessionQuota
│   └── event.py            # TaskEvent, LogEntry
├── services/                # 服务实现
│   ├── factory.py          # 服务工厂
│   ├── task_manager.py     # 任务管理器
│   ├── task_executor.py    # 任务执行器
│   ├── reliability.py      # 可靠性服务
│   ├── sign_client.py      # 签名服务客户端
│   ├── queue/
│   │   ├── memory.py       # 内存队列
│   │   └── redis.py        # Redis 队列
│   ├── storage/
│   │   ├── memory.py       # 内存存储
│   │   └── redis.py        # Redis 存储
│   ├── session/
│   │   ├── memory.py       # 内存 Session
│   │   └── redis.py        # Redis Session
│   └── event/
│       ├── asyncio_bus.py  # Asyncio 事件总线
│       └── redis_bus.py    # Redis 事件总线
├── middleware/
│   └── session.py          # Session 中间件
├── routers/
│   ├── auth.py             # 认证路由
│   ├── tasks.py            # 任务路由
│   └── ws_tasks.py         # WebSocket 路由
├── main.py                  # API 入口
└── worker_main.py           # Worker 入口

webui-src/src/
├── types/task.ts            # TypeScript 类型
├── api/tasks.ts             # API 封装
├── hooks/
│   ├── useSession.ts        # Session Hook
│   └── useTaskEvents.ts     # WebSocket Hook
└── components/
    ├── TaskList.tsx         # 任务列表
    ├── TaskDetail.tsx       # 任务详情
    ├── TaskCreate.tsx       # 创建任务
    └── TaskDashboard.tsx    # 仪表盘
```

---

## 核心概念

### 1. 任务生命周期

```
创建 (PENDING) → 入队 → Worker 取出 (RUNNING) → 完成 (COMPLETED/FAILED/CANCELLED)
                                ↓
                           续租 (heartbeat)
                                ↓
                           超时回收 → 重试或死信
```

### 2. 租约机制 (Lease)

- Worker 通过 `reserve()` 获取任务租约
- 租约有过期时间（默认 5 分钟）
- Worker 需定期 `heartbeat()` 续租
- 过期租约会被自动回收

### 3. 可靠性保证

- **At-least-once**: 任务至少执行一次
- **幂等键**: 防止重复创建
- **死信队列**: 多次失败的任务移入死信

---

## API 参考

### 认证

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/session` | POST | 创建/获取 Session |
| `/api/auth/me` | GET | 获取当前用户信息 |
| `/api/auth/logout` | POST | 登出 |
| `/api/auth/refresh` | POST | 刷新 Session |

### 任务管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tasks/` | POST | 创建任务 |
| `/api/tasks/` | GET | 获取任务列表 |
| `/api/tasks/stats` | GET | 获取任务统计 |
| `/api/tasks/{id}` | GET | 获取任务详情 |
| `/api/tasks/{id}/logs` | GET | 获取任务日志 |
| `/api/tasks/{id}/cancel` | POST | 取消任务 |
| `/api/tasks/{id}/retry` | POST | 重试任务 |
| `/api/tasks/{id}/priority` | PATCH | 调整优先级 |
| `/api/tasks/{id}` | DELETE | 删除任务 |

### WebSocket

| 接口 | 说明 |
|------|------|
| `/ws/tasks/{id}/logs?session_id=xxx` | 订阅任务日志和事件 |
| `/ws/session/events?session_id=xxx` | 订阅用户所有任务事件 |

---

## 配置

### 环境变量

```bash
# 后端选择
MC_BACKEND=memory  # memory 或 redis

# Redis 配置（当使用 Redis 后端）
MC_REDIS_URL=redis://localhost:6379/0

# Session 配置
MC_SESSION_EXPIRE_HOURS=24

# 并发控制
MC_GLOBAL_MAX_CONCURRENT=10
MC_USER_MAX_CONCURRENT=3
MC_USER_MAX_DAILY=100

# 签名服务
MC_SIGN_SERVER_ENABLED=true
MC_SIGN_SERVER_URL=http://localhost:8989
```

### 配置文件 (`config/multi_task.yaml`)

参见项目中的配置文件模板。

---

## 使用 Redis 后端

Redis 后端适用于生产环境和分布式部署。

### 修改配置

```python
# 在 api/main.py 或通过环境变量
from api.services.factory import create_services

services = create_services(
    backend="redis",
    redis_url="redis://localhost:6379/0"
)
```

### 启动多个 Worker

```bash
# Worker 1
python -m api.worker_main

# Worker 2 (另一个终端)
python -m api.worker_main

# Worker 3 (另一个终端)
python -m api.worker_main
```

---

## 前端集成

### 安装依赖

```bash
cd webui-src
npm install @radix-ui/react-progress axios
```

### 使用组件

```tsx
import { TaskDashboard } from './components/TaskDashboard';
import { TaskCreate } from './components/TaskCreate';
import { useSession } from './hooks/useSession';

function App() {
  const { session, loading } = useSession();
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <TaskDashboard
        onTaskSelect={setSelectedTask}
        onCreateTask={() => setCreateOpen(true)}
      />
      <TaskCreate
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(taskId) => console.log('Created:', taskId)}
      />
    </div>
  );
}
```

---

## 监控和调试

### 健康检查

```bash
curl http://localhost:8080/health
```

### 队列统计

```bash
curl http://localhost:8080/api/tasks/stats \
  -H "X-Session-ID: YOUR_SESSION_ID"
```

### WebSocket 连接统计

```bash
curl http://localhost:8080/ws/stats
```

---

## 故障排除

### 任务卡在 RUNNING 状态

1. 检查 Worker 是否正常运行
2. 检查租约是否过期
3. 等待租约回收（约 5 分钟）

### WebSocket 连接失败

1. 检查 Session ID 是否有效
2. 检查防火墙/代理设置
3. 查看浏览器控制台错误

### 任务创建失败（配额不足）

1. 检查每日任务配额
2. 检查并发任务数
3. 等待运行中任务完成

---

*文档版本: 1.0*
*更新时间: 2026-01-28*

