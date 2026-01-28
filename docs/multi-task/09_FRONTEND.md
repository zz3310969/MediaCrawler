# 09. 前端开发文档

> 模块: WebUI 改造  
> Phase: 5  
> 预估工期: 3 天  
> 产出文件:  
> - `webui-src/src/types/task.ts`  
> - `webui-src/src/api/tasks.ts`  
> - `webui-src/src/hooks/useSession.ts`  
> - `webui-src/src/components/TaskList.tsx`  
> - `webui-src/src/components/TaskDetail.tsx`  
> - `webui-src/src/components/TaskCreate.tsx`

---

## 一、设计原型

### 1.1 整体布局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MediaCrawler                                              [用户信息] [设置] │
├───────────┬─────────────────────────────────────────────────────────────────┤
│           │                                                                 │
│  侧边栏    │                        主内容区                                 │
│           │                                                                 │
│  ┌───────┐│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 仪表盘 ││  │                      任务列表/详情                       │   │
│  ├───────┤│  │                                                         │   │
│  │ 任务   ││  │                                                         │   │
│  ├───────┤│  │                                                         │   │
│  │ 平台   ││  │                                                         │   │
│  │ ・小红书││  │                                                         │   │
│  │ ・抖音 ││  │                                                         │   │
│  │ ・B站  ││  │                                                         │   │
│  │ ・微博 ││  │                                                         │   │
│  │ ・微信 ││  │                                                         │   │
│  ├───────┤│  │                                                         │   │
│  │ 设置   ││  │                                                         │   │
│  └───────┘│  └─────────────────────────────────────────────────────────┘   │
│           │                                                                 │
└───────────┴─────────────────────────────────────────────────────────────────┘
```

### 1.2 任务仪表盘

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  任务仪表盘                                              [+ 创建任务]        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │    5     │  │    3     │  │   127    │  │    8     │  │    2     │     │
│  │  等待中   │  │  运行中   │  │  已完成   │  │  已失败   │  │  已取消   │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  运行中的任务                                                        │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  🔴 小红书搜索: 护肤品推荐           进度: 45/100 (45%)      │   │   │
│  │  │  ████████████░░░░░░░░░░░░░░░░░      [取消] [查看详情]        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  🟡 抖音创作者: @美食达人            进度: 12/50 (24%)       │   │   │
│  │  │  ██████░░░░░░░░░░░░░░░░░░░░░░░      [取消] [查看详情]        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  🟢 B站搜索: 编程教程                进度: 78/100 (78%)      │   │   │
│  │  │  ██████████████████████░░░░░░░      [取消] [查看详情]        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  最近完成的任务                                          [查看全部]  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  ✅ 小红书搜索: 旅行攻略    100条    2分钟前     [下载] [重新运行]   │   │
│  │  ✅ 微博热搜: #科技新闻#    50条     5分钟前     [下载] [重新运行]   │   │
│  │  ❌ 抖音搜索: 健身          失败     10分钟前    [查看错误] [重试]   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 任务列表页

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  任务列表                                                 [+ 创建任务]       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  筛选: [全部状态 ▼] [全部平台 ▼]     搜索: [_______________] 🔍              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  □  任务名称               平台    状态    进度    创建时间    操作   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  □  小红书搜索: 护肤品     XHS    🔵运行中  45%    10:30      [...]  │   │
│  │  □  抖音创作者爬取         DY     🔵运行中  24%    10:25      [...]  │   │
│  │  □  B站搜索: 编程教程      BILI   🔵运行中  78%    10:20      [...]  │   │
│  │  □  微博热搜               WB     🟢已完成  100%   10:15      [...]  │   │
│  │  □  小红书搜索: 旅行       XHS    🟢已完成  100%   10:10      [...]  │   │
│  │  □  抖音搜索: 健身         DY     🔴失败    0%     10:05      [...]  │   │
│  │  □  微信公众号爬取         WX     ⚪等待中  0%     10:00      [...]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  显示 1-7 共 145 条                              [< 上一页] [1] [2] [>]      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 任务详情页

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← 返回                任务详情                    [取消] [重试] [删除]       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  基本信息                                                            │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  任务ID:    abc123-def456-ghi789                                    │   │
│  │  任务名称:  小红书搜索: 护肤品推荐                                    │   │
│  │  平台:      小红书 (XHS)                                             │   │
│  │  类型:      关键词搜索                                               │   │
│  │  状态:      🔵 运行中                                                │   │
│  │  优先级:    普通 (5)                              [调整优先级]        │   │
│  │  创建时间:  2026-01-28 10:30:00                                      │   │
│  │  开始时间:  2026-01-28 10:30:05                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  执行进度                                                            │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ███████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%              │   │
│  │                                                                     │   │
│  │  已爬取笔记: 45 / 100                                               │   │
│  │  已爬取评论: 230                                                    │   │
│  │  预计剩余时间: 约 2 分钟                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  实时日志                                      [🔍 筛选] [⬇️ 下载]    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  10:32:15 [INFO]  正在爬取第 45 条笔记...                           │   │
│  │  10:32:14 [INFO]  笔记 xxx 爬取完成，获取 5 条评论                   │   │
│  │  10:32:12 [INFO]  正在爬取第 44 条笔记...                           │   │
│  │  10:32:10 [WARN]  请求频率过快，等待 2 秒...                        │   │
│  │  10:32:08 [INFO]  笔记 yyy 爬取完成，获取 3 条评论                   │   │
│  │  10:32:05 [INFO]  正在爬取第 43 条笔记...                           │   │
│  │  ...                                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.5 创建任务弹窗

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           创建新任务                               [×]       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  任务名称（可选）                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  小红书搜索: 护肤品推荐                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  选择平台                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ○ 小红书    ○ 抖音    ○ B站    ○ 微博    ○ 微信公众号              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  爬取类型                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ○ 关键词搜索    ○ 创作者主页    ○ 帖子详情                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  关键词                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  护肤品推荐                                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  高级选项                                                        [展开 ▼]   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  最大笔记数: [100]       启用评论: [✓]       最大评论数: [20]        │   │
│  │  保存格式: [CSV ▼]       优先级: [普通 ▼]                            │   │
│  │  定时执行: [  ] 2026-01-28 12:00                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                                           [取消]    [创建任务]              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、TypeScript 类型定义

### 2.1 任务类型 (`src/types/task.ts`)

```typescript
// 任务状态
export type TaskStatus = 
  | 'pending' 
  | 'running' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

// 平台
export type Platform = 'xhs' | 'dy' | 'bili' | 'wb' | 'wechat';

// 爬取类型
export type CrawlerType = 'search' | 'creator' | 'detail';

// 任务配置
export interface TaskConfig {
  platform: Platform;
  crawler_type: CrawlerType;
  keywords?: string;
  creator_ids?: string;
  max_notes: number;
  enable_comments: boolean;
  max_comments: number;
  save_option: 'csv' | 'json' | 'db';
  extra?: Record<string, any>;
}

// 任务进度
export interface TaskProgress {
  current: number;
  total: number;
  percentage: number;
  items_crawled: number;
  comments_crawled: number;
}

// 任务结果
export interface TaskResult {
  success: boolean;
  error_message?: string;
  output_path?: string;
  statistics?: Record<string, any>;
}

// 任务实体
export interface Task {
  task_id: string;
  session_id: string;
  task_name?: string;
  status: TaskStatus;
  priority: number;
  retry_count: number;
  cancel_requested: boolean;
  created_at: string;
  scheduled_at?: string;
  started_at?: string;
  finished_at?: string;
  last_heartbeat_at?: string;
  config: TaskConfig;
  progress: TaskProgress;
  result: TaskResult;
}

// 创建任务请求
export interface TaskCreateRequest {
  task_name?: string;
  config: TaskConfig;
  priority?: number;
  scheduled_at?: string;
  idempotency_key?: string;
}

// 任务列表响应
export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}

// 任务统计
export interface TaskStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

// 日志条目
export interface LogEntry {
  log_id: string;
  task_id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  extra?: Record<string, any>;
}

// 任务事件
export interface TaskEvent {
  event_id: string;
  event_type: string;
  task_id: string;
  session_id: string;
  timestamp: string;
  payload: Record<string, any>;
}
```

---

## 三、API 封装

### 3.1 任务 API (`src/api/tasks.ts`)

```typescript
import axios from 'axios';
import type { 
  Task, TaskCreateRequest, TaskListResponse, 
  TaskStats, LogEntry 
} from '@/types/task';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
});

// 请求拦截：添加 session header
api.interceptors.request.use((config) => {
  const sessionId = localStorage.getItem('session_id');
  if (sessionId) {
    config.headers['X-Session-ID'] = sessionId;
  }
  return config;
});

export const tasksApi = {
  // 创建任务
  async create(data: TaskCreateRequest): Promise<Task> {
    const res = await api.post<Task>('/tasks/', data);
    return res.data;
  },

  // 获取任务列表
  async list(params?: {
    status?: string;
    platform?: string;
    page?: number;
    page_size?: number;
  }): Promise<TaskListResponse> {
    const res = await api.get<TaskListResponse>('/tasks/', { params });
    return res.data;
  },

  // 获取任务详情
  async get(taskId: string): Promise<Task> {
    const res = await api.get<Task>(`/tasks/${taskId}`);
    return res.data;
  },

  // 获取任务统计
  async getStats(): Promise<TaskStats> {
    const res = await api.get<TaskStats>('/tasks/stats');
    return res.data;
  },

  // 获取任务日志
  async getLogs(taskId: string, params?: {
    limit?: number;
    offset?: number;
    level?: string;
  }): Promise<LogEntry[]> {
    const res = await api.get<LogEntry[]>(`/tasks/${taskId}/logs`, { params });
    return res.data;
  },

  // 取消任务
  async cancel(taskId: string): Promise<void> {
    await api.post(`/tasks/${taskId}/cancel`);
  },

  // 重试任务
  async retry(taskId: string): Promise<Task> {
    const res = await api.post<Task>(`/tasks/${taskId}/retry`);
    return res.data;
  },

  // 调整优先级
  async updatePriority(taskId: string, priority: number): Promise<void> {
    await api.patch(`/tasks/${taskId}/priority`, { priority });
  },

  // 删除任务
  async delete(taskId: string): Promise<void> {
    await api.delete(`/tasks/${taskId}`);
  },
};
```

---

## 四、Hooks

### 4.1 Session Hook (`src/hooks/useSession.ts`)

```typescript
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface Session {
  session_id: string;
  user_id?: string;
  created_at: string;
  expires_at: string;
  quota: {
    max_concurrent_tasks: number;
    max_daily_tasks: number;
    used_daily_tasks: number;
  };
}

export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // 初始化 session
  const initSession = useCallback(async () => {
    try {
      setLoading(true);
      
      // 检查是否已有 session
      let sessionId = localStorage.getItem('session_id');
      
      if (sessionId) {
        // 验证现有 session
        try {
          const res = await axios.get('/api/auth/me', {
            headers: { 'X-Session-ID': sessionId }
          });
          setSession(res.data);
          return;
        } catch {
          // session 无效，创建新的
          localStorage.removeItem('session_id');
        }
      }
      
      // 创建新 session
      const res = await axios.post('/api/auth/session');
      setSession(res.data);
      localStorage.setItem('session_id', res.data.session_id);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 登出
  const logout = useCallback(async () => {
    try {
      await axios.post('/api/auth/logout');
    } finally {
      localStorage.removeItem('session_id');
      setSession(null);
      // 重新创建匿名 session
      await initSession();
    }
  }, [initSession]);

  useEffect(() => {
    initSession();
  }, [initSession]);

  return {
    session,
    loading,
    error,
    logout,
    isAuthenticated: !!session,
  };
}
```

### 4.2 任务 WebSocket Hook (`src/hooks/useTaskEvents.ts`)

```typescript
import { useEffect, useRef, useState, useCallback } from 'react';
import type { TaskEvent } from '@/types/task';

interface UseTaskEventsOptions {
  taskId?: string;
  sessionId?: string;
  onEvent?: (event: TaskEvent) => void;
  enabled?: boolean;
}

export function useTaskEvents(options: UseTaskEventsOptions) {
  const { taskId, sessionId, onEvent, enabled = true } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<TaskEvent[]>([]);

  const connect = useCallback(() => {
    if (!enabled || !sessionId) return;

    let url: string;
    if (taskId) {
      url = `ws://${location.host}/ws/tasks/${taskId}/logs?session_id=${sessionId}`;
    } else {
      url = `ws://${location.host}/ws/session/events?session_id=${sessionId}`;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TaskEvent | { type: string };
        
        // 处理心跳
        if ('type' in data && data.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }

        const taskEvent = data as TaskEvent;
        setEvents((prev) => [...prev.slice(-99), taskEvent]);
        onEvent?.(taskEvent);
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error', error);
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('WebSocket disconnected');
      
      // 自动重连
      setTimeout(() => {
        if (enabled) connect();
      }, 3000);
    };
  }, [taskId, sessionId, onEvent, enabled]);

  useEffect(() => {
    connect();
    
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return {
    connected,
    events,
    clearEvents: () => setEvents([]),
  };
}
```

---

## 五、核心组件

### 5.1 任务列表 (`src/components/TaskList.tsx`)

```tsx
import React, { useState, useEffect } from 'react';
import { tasksApi } from '@/api/tasks';
import type { Task, TaskStatus, Platform } from '@/types/task';

interface TaskListProps {
  onTaskSelect?: (task: Task) => void;
}

export const TaskList: React.FC<TaskListProps> = ({ onTaskSelect }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  
  // 筛选
  const [statusFilter, setStatusFilter] = useState<TaskStatus | ''>('');
  const [platformFilter, setPlatformFilter] = useState<Platform | ''>('');

  const loadTasks = async () => {
    setLoading(true);
    try {
      const res = await tasksApi.list({
        status: statusFilter || undefined,
        platform: platformFilter || undefined,
        page,
        page_size: 20,
      });
      setTasks(res.tasks);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [page, statusFilter, platformFilter]);

  const getStatusBadge = (status: TaskStatus) => {
    const styles: Record<TaskStatus, string> = {
      pending: 'bg-gray-200 text-gray-800',
      running: 'bg-blue-200 text-blue-800',
      completed: 'bg-green-200 text-green-800',
      failed: 'bg-red-200 text-red-800',
      cancelled: 'bg-yellow-200 text-yellow-800',
    };
    const labels: Record<TaskStatus, string> = {
      pending: '等待中',
      running: '运行中',
      completed: '已完成',
      failed: '已失败',
      cancelled: '已取消',
    };
    return (
      <span className={`px-2 py-1 rounded text-xs ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* 筛选器 */}
      <div className="flex gap-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as TaskStatus | '')}
          className="border rounded px-3 py-2"
        >
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">运行中</option>
          <option value="completed">已完成</option>
          <option value="failed">已失败</option>
          <option value="cancelled">已取消</option>
        </select>
        
        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value as Platform | '')}
          className="border rounded px-3 py-2"
        >
          <option value="">全部平台</option>
          <option value="xhs">小红书</option>
          <option value="dy">抖音</option>
          <option value="bili">B站</option>
          <option value="wb">微博</option>
          <option value="wechat">微信</option>
        </select>
      </div>

      {/* 任务表格 */}
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-3 text-left">任务名称</th>
            <th className="p-3 text-left">平台</th>
            <th className="p-3 text-left">状态</th>
            <th className="p-3 text-left">进度</th>
            <th className="p-3 text-left">创建时间</th>
            <th className="p-3 text-left">操作</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr
              key={task.task_id}
              className="border-b hover:bg-gray-50 cursor-pointer"
              onClick={() => onTaskSelect?.(task)}
            >
              <td className="p-3">{task.task_name || task.task_id.slice(0, 8)}</td>
              <td className="p-3">{task.config.platform.toUpperCase()}</td>
              <td className="p-3">{getStatusBadge(task.status)}</td>
              <td className="p-3">
                <div className="w-24 bg-gray-200 rounded h-2">
                  <div
                    className="bg-blue-500 rounded h-2"
                    style={{ width: `${task.progress.percentage}%` }}
                  />
                </div>
              </td>
              <td className="p-3">{new Date(task.created_at).toLocaleString()}</td>
              <td className="p-3">
                <button
                  className="text-blue-600 hover:underline"
                  onClick={(e) => {
                    e.stopPropagation();
                    onTaskSelect?.(task);
                  }}
                >
                  详情
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* 分页 */}
      <div className="flex justify-between items-center">
        <span>共 {total} 条</span>
        <div className="flex gap-2">
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            上一页
          </button>
          <span className="px-3 py-1">{page}</span>
          <button
            disabled={page * 20 >= total}
            onClick={() => setPage(page + 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
};
```

### 5.2 任务详情 (`src/components/TaskDetail.tsx`)

```tsx
import React, { useState, useEffect, useRef } from 'react';
import { tasksApi } from '@/api/tasks';
import { useTaskEvents } from '@/hooks/useTaskEvents';
import type { Task, LogEntry, TaskEvent } from '@/types/task';

interface TaskDetailProps {
  taskId: string;
  sessionId: string;
  onBack?: () => void;
}

export const TaskDetail: React.FC<TaskDetailProps> = ({
  taskId,
  sessionId,
  onBack,
}) => {
  const [task, setTask] = useState<Task | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // 加载任务详情
  const loadTask = async () => {
    const data = await tasksApi.get(taskId);
    setTask(data);
  };

  // 加载历史日志
  const loadLogs = async () => {
    const data = await tasksApi.getLogs(taskId, { limit: 100 });
    setLogs(data);
  };

  useEffect(() => {
    loadTask();
    loadLogs();
  }, [taskId]);

  // WebSocket 订阅实时更新
  const { connected, events } = useTaskEvents({
    taskId,
    sessionId,
    enabled: task?.status === 'running',
    onEvent: (event: TaskEvent) => {
      if (event.event_type === 'task.progress') {
        setTask((prev) =>
          prev ? { ...prev, progress: event.payload as any } : null
        );
      } else if (event.event_type === 'task.log') {
        setLogs((prev) => [
          ...prev,
          {
            log_id: event.event_id,
            task_id: taskId,
            timestamp: event.timestamp,
            level: event.payload.level,
            message: event.payload.message,
          },
        ]);
      } else if (
        ['task.completed', 'task.failed', 'task.cancelled'].includes(
          event.event_type
        )
      ) {
        loadTask(); // 刷新任务状态
      }
    },
  });

  // 自动滚动到底部
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleCancel = async () => {
    if (confirm('确定要取消此任务吗？')) {
      await tasksApi.cancel(taskId);
      loadTask();
    }
  };

  const handleRetry = async () => {
    const newTask = await tasksApi.retry(taskId);
    // 跳转到新任务
    window.location.href = `/tasks/${newTask.task_id}`;
  };

  if (!task) {
    return <div>加载中...</div>;
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex justify-between items-center">
        <button onClick={onBack} className="text-blue-600 hover:underline">
          ← 返回
        </button>
        <div className="flex gap-2">
          {task.status === 'running' && (
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-red-500 text-white rounded"
            >
              取消任务
            </button>
          )}
          {['failed', 'cancelled'].includes(task.status) && (
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-blue-500 text-white rounded"
            >
              重试
            </button>
          )}
        </div>
      </div>

      {/* 基本信息 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">基本信息</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-gray-500">任务ID</label>
            <p>{task.task_id}</p>
          </div>
          <div>
            <label className="text-gray-500">任务名称</label>
            <p>{task.task_name || '-'}</p>
          </div>
          <div>
            <label className="text-gray-500">平台</label>
            <p>{task.config.platform.toUpperCase()}</p>
          </div>
          <div>
            <label className="text-gray-500">状态</label>
            <p>{task.status}</p>
          </div>
        </div>
      </div>

      {/* 进度 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">执行进度</h3>
        <div className="w-full bg-gray-200 rounded h-4 mb-2">
          <div
            className="bg-blue-500 rounded h-4 transition-all"
            style={{ width: `${task.progress.percentage}%` }}
          />
        </div>
        <p>
          已爬取: {task.progress.items_crawled} / {task.progress.total} (
          {task.progress.percentage}%)
        </p>
        {connected && (
          <p className="text-green-500 text-sm">🟢 实时更新中</p>
        )}
      </div>

      {/* 日志 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-bold mb-4">实时日志</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded h-64 overflow-y-auto font-mono text-sm">
          {logs.map((log) => (
            <div
              key={log.log_id}
              className={`${
                log.level === 'error'
                  ? 'text-red-400'
                  : log.level === 'warn'
                  ? 'text-yellow-400'
                  : 'text-gray-300'
              }`}
            >
              [{new Date(log.timestamp).toLocaleTimeString()}] [{log.level.toUpperCase()}]{' '}
              {log.message}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
};
```

### 5.3 创建任务弹窗 (`src/components/TaskCreate.tsx`)

```tsx
import React, { useState } from 'react';
import { tasksApi } from '@/api/tasks';
import type { TaskCreateRequest, Platform, CrawlerType } from '@/types/task';

interface TaskCreateProps {
  onClose: () => void;
  onCreated: (taskId: string) => void;
}

export const TaskCreate: React.FC<TaskCreateProps> = ({ onClose, onCreated }) => {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    task_name: '',
    platform: 'xhs' as Platform,
    crawler_type: 'search' as CrawlerType,
    keywords: '',
    creator_ids: '',
    max_notes: 100,
    enable_comments: false,
    max_comments: 20,
    save_option: 'csv' as 'csv' | 'json' | 'db',
    priority: 5,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const request: TaskCreateRequest = {
        task_name: form.task_name || undefined,
        config: {
          platform: form.platform,
          crawler_type: form.crawler_type,
          keywords: form.keywords || undefined,
          creator_ids: form.creator_ids || undefined,
          max_notes: form.max_notes,
          enable_comments: form.enable_comments,
          max_comments: form.max_comments,
          save_option: form.save_option,
        },
        priority: form.priority,
      };

      const task = await tasksApi.create(request);
      onCreated(task.task_id);
    } catch (error) {
      alert('创建失败: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">创建新任务</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              ×
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 任务名称 */}
            <div>
              <label className="block mb-1">任务名称（可选）</label>
              <input
                type="text"
                value={form.task_name}
                onChange={(e) => setForm({ ...form, task_name: e.target.value })}
                className="w-full border rounded px-3 py-2"
                placeholder="例如: 小红书搜索-护肤品"
              />
            </div>

            {/* 平台选择 */}
            <div>
              <label className="block mb-1">选择平台</label>
              <div className="flex gap-4">
                {(['xhs', 'dy', 'bili', 'wb', 'wechat'] as Platform[]).map((p) => (
                  <label key={p} className="flex items-center gap-1">
                    <input
                      type="radio"
                      checked={form.platform === p}
                      onChange={() => setForm({ ...form, platform: p })}
                    />
                    {p === 'xhs' && '小红书'}
                    {p === 'dy' && '抖音'}
                    {p === 'bili' && 'B站'}
                    {p === 'wb' && '微博'}
                    {p === 'wechat' && '微信'}
                  </label>
                ))}
              </div>
            </div>

            {/* 爬取类型 */}
            <div>
              <label className="block mb-1">爬取类型</label>
              <div className="flex gap-4">
                {(['search', 'creator', 'detail'] as CrawlerType[]).map((t) => (
                  <label key={t} className="flex items-center gap-1">
                    <input
                      type="radio"
                      checked={form.crawler_type === t}
                      onChange={() => setForm({ ...form, crawler_type: t })}
                    />
                    {t === 'search' && '关键词搜索'}
                    {t === 'creator' && '创作者主页'}
                    {t === 'detail' && '帖子详情'}
                  </label>
                ))}
              </div>
            </div>

            {/* 关键词 */}
            {form.crawler_type === 'search' && (
              <div>
                <label className="block mb-1">关键词</label>
                <input
                  type="text"
                  value={form.keywords}
                  onChange={(e) => setForm({ ...form, keywords: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
            )}

            {/* 创作者ID */}
            {form.crawler_type === 'creator' && (
              <div>
                <label className="block mb-1">创作者ID（多个用逗号分隔）</label>
                <input
                  type="text"
                  value={form.creator_ids}
                  onChange={(e) => setForm({ ...form, creator_ids: e.target.value })}
                  className="w-full border rounded px-3 py-2"
                  required
                />
              </div>
            )}

            {/* 高级选项 */}
            <details className="border rounded p-4">
              <summary className="cursor-pointer font-medium">高级选项</summary>
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block mb-1">最大笔记数</label>
                    <input
                      type="number"
                      value={form.max_notes}
                      onChange={(e) =>
                        setForm({ ...form, max_notes: parseInt(e.target.value) })
                      }
                      className="w-full border rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block mb-1">优先级</label>
                    <select
                      value={form.priority}
                      onChange={(e) =>
                        setForm({ ...form, priority: parseInt(e.target.value) })
                      }
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value={1}>低</option>
                      <option value={5}>普通</option>
                      <option value={8}>高</option>
                      <option value={10}>紧急</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={form.enable_comments}
                      onChange={(e) =>
                        setForm({ ...form, enable_comments: e.target.checked })
                      }
                    />
                    启用评论爬取
                  </label>
                </div>
              </div>
            </details>

            {/* 按钮 */}
            <div className="flex justify-end gap-2 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border rounded"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
              >
                {loading ? '创建中...' : '创建任务'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
```

---

## 六、验收标准

- [ ] 任务仪表盘显示统计数据
- [ ] 任务列表支持筛选、分页
- [ ] 任务详情实时更新进度和日志
- [ ] 创建任务弹窗功能完整
- [ ] WebSocket 自动重连
- [ ] 响应式布局（移动端适配）
- [ ] 错误提示友好

---

*文档结束*

