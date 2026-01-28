/**
 * 任务 API 封装
 */
import axios, { AxiosInstance } from 'axios';
import type { 
  Task, 
  TaskCreateRequest, 
  TaskListResponse, 
  TaskStats, 
  LogEntry,
  SessionResponse,
  TaskStatus,
  Platform
} from '../types/task';

// API 客户端
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 30000,
});

// Session ID 存储
const SESSION_ID_KEY = 'mc_session_id';

/**
 * 获取存储的 Session ID
 */
export function getStoredSessionId(): string | null {
  return localStorage.getItem(SESSION_ID_KEY);
}

/**
 * 存储 Session ID
 */
export function setStoredSessionId(sessionId: string): void {
  localStorage.setItem(SESSION_ID_KEY, sessionId);
}

/**
 * 清除 Session ID
 */
export function clearStoredSessionId(): void {
  localStorage.removeItem(SESSION_ID_KEY);
}

// 请求拦截：添加 session header
api.interceptors.request.use((config) => {
  const sessionId = getStoredSessionId();
  if (sessionId) {
    config.headers['X-Session-ID'] = sessionId;
  }
  return config;
});

// 响应拦截：处理 401 错误
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Session 过期，清除并尝试重新创建
      clearStoredSessionId();
    }
    return Promise.reject(error);
  }
);

// ========== Session API ==========

/**
 * 创建/获取 Session
 */
export async function createSession(): Promise<SessionResponse> {
  const res = await api.post<SessionResponse>('/auth/session');
  setStoredSessionId(res.data.session_id);
  return res.data;
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<SessionResponse> {
  const res = await api.get<SessionResponse>('/auth/me');
  return res.data;
}

/**
 * 登出
 */
export async function logout(): Promise<void> {
  await api.post('/auth/logout');
  clearStoredSessionId();
}

/**
 * 刷新 Session
 */
export async function refreshSession(): Promise<SessionResponse> {
  const res = await api.post<SessionResponse>('/auth/refresh');
  return res.data;
}

// ========== Tasks API ==========

export const tasksApi = {
  /**
   * 创建任务
   */
  async create(data: TaskCreateRequest): Promise<Task> {
    const res = await api.post<Task>('/tasks/', data);
    return res.data;
  },

  /**
   * 获取任务列表
   */
  async list(params?: {
    status?: TaskStatus;
    platform?: Platform;
    page?: number;
    page_size?: number;
  }): Promise<TaskListResponse> {
    const res = await api.get<TaskListResponse>('/tasks/', { params });
    return res.data;
  },

  /**
   * 获取任务详情
   */
  async get(taskId: string): Promise<Task> {
    const res = await api.get<Task>(`/tasks/${taskId}`);
    return res.data;
  },

  /**
   * 获取任务统计
   */
  async getStats(): Promise<TaskStats> {
    const res = await api.get<TaskStats>('/tasks/stats');
    return res.data;
  },

  /**
   * 获取任务日志
   */
  async getLogs(taskId: string, params?: {
    limit?: number;
    offset?: number;
    level?: string;
  }): Promise<LogEntry[]> {
    const res = await api.get<LogEntry[]>(`/tasks/${taskId}/logs`, { params });
    return res.data;
  },

  /**
   * 取消任务
   */
  async cancel(taskId: string): Promise<{ message: string }> {
    const res = await api.post<{ message: string }>(`/tasks/${taskId}/cancel`);
    return res.data;
  },

  /**
   * 重试任务
   */
  async retry(taskId: string): Promise<Task> {
    const res = await api.post<Task>(`/tasks/${taskId}/retry`);
    return res.data;
  },

  /**
   * 调整优先级
   */
  async updatePriority(taskId: string, priority: number): Promise<{ message: string }> {
    const res = await api.patch<{ message: string }>(`/tasks/${taskId}/priority`, null, {
      params: { priority }
    });
    return res.data;
  },

  /**
   * 删除任务
   */
  async delete(taskId: string): Promise<{ message: string }> {
    const res = await api.delete<{ message: string }>(`/tasks/${taskId}`);
    return res.data;
  },
};

export default tasksApi;

