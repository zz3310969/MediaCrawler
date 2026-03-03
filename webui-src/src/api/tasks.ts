/**
 * 任务 API 封装
 */
import { client } from './client';
import {
  setStoredSessionId,
  clearStoredSessionId,
} from './session';
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

// 重新导出 session 相关函数（保持向后兼容）
export { setStoredSessionId, clearStoredSessionId } from './session';

// ========== Session API ==========

/**
 * 创建/获取 Session
 */
export async function createSession(): Promise<SessionResponse> {
  const res = await client.post<SessionResponse>('/api/auth/session');
  setStoredSessionId(res.data.session_id);
  return res.data;
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<SessionResponse> {
  const res = await client.get<SessionResponse>('/api/auth/me');
  return res.data;
}

/**
 * 登出
 */
export async function logout(): Promise<void> {
  await client.post('/api/auth/logout');
  clearStoredSessionId();
}

/**
 * 刷新 Session
 */
export async function refreshSession(): Promise<SessionResponse> {
  const res = await client.post<SessionResponse>('/api/auth/refresh');
  return res.data;
}

// ========== Tasks API ==========

export const tasksApi = {
  /**
   * 创建任务
   */
  async create(data: TaskCreateRequest): Promise<Task> {
    const res = await client.post<Task>('/api/tasks/', data);
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
    const res = await client.get<TaskListResponse>('/api/tasks/', { params });
    return res.data;
  },

  /**
   * 获取任务详情
   */
  async get(taskId: string): Promise<Task> {
    const res = await client.get<Task>(`/api/tasks/${taskId}`);
    return res.data;
  },

  /**
   * 获取任务统计
   */
  async getStats(): Promise<TaskStats> {
    const res = await client.get<TaskStats>('/api/tasks/stats');
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
    const res = await client.get<LogEntry[]>(`/api/tasks/${taskId}/logs`, { params });
    return res.data;
  },

  /**
   * 取消任务
   */
  async cancel(taskId: string): Promise<{ message: string }> {
    const res = await client.post<{ message: string }>(`/api/tasks/${taskId}/cancel`);
    return res.data;
  },

  /**
   * 重试任务
   */
  async retry(taskId: string): Promise<Task> {
    const res = await client.post<Task>(`/api/tasks/${taskId}/retry`);
    return res.data;
  },

  /**
   * 调整优先级
   */
  async updatePriority(taskId: string, priority: number): Promise<{ message: string }> {
    const res = await client.patch<{ message: string }>(`/api/tasks/${taskId}/priority`, null, {
      params: { priority }
    });
    return res.data;
  },

  /**
   * 删除任务
   */
  async delete(taskId: string): Promise<{ message: string }> {
    const res = await client.delete<{ message: string }>(`/api/tasks/${taskId}`);
    return res.data;
  },
};

export default tasksApi;
