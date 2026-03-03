/**
 * 定时调度 API 封装
 */
import { client } from './client';

export interface ScheduleConfig {
  platform: string;
  crawler_type: string;
  keywords?: string[];
  creator_ids?: string[];
  note_urls?: string[];
  max_notes: number;
  enable_comments: boolean;
  max_comments_per_note: number;
  enable_media: boolean;
  concurrency: number;
  crawl_interval: number;
  account_id?: string;
  login_type?: string;
  save_option: string;
  extra?: Record<string, unknown>;
}

export interface Schedule {
  schedule_id: string;
  schedule_name: string;
  platform: string;
  crawler_type: string;
  task_config: ScheduleConfig;
  trigger_type: 'cron' | 'interval' | 'once';
  cron_expression?: string;
  interval_seconds?: number;
  timezone: string;
  enabled: boolean;
  last_run_at?: string;
  next_run_at?: string;
  total_runs: number;
  webhook_url?: string;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface ScheduleListResponse {
  schedules: Schedule[];
  total: number;
}

export interface ScheduleCreateRequest {
  schedule_name: string;
  task_config: ScheduleConfig;
  trigger_type: 'cron' | 'interval' | 'once';
  cron_expression?: string;
  interval_seconds?: number;
  timezone?: string;
  webhook_url?: string;
  webhook_secret?: string;
}

export interface ScheduleUpdateRequest {
  schedule_name?: string;
  task_config?: ScheduleConfig;
  trigger_type?: 'cron' | 'interval' | 'once';
  cron_expression?: string;
  interval_seconds?: number;
  timezone?: string;
  webhook_url?: string;
  webhook_secret?: string;
}

export const schedulesApi = {
  async list(params?: {
    platform?: string;
    enabled_only?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<ScheduleListResponse> {
    const res = await client.get<ScheduleListResponse>('/api/schedules/', { params });
    return res.data;
  },

  async get(scheduleId: string): Promise<Schedule> {
    const res = await client.get<Schedule>(`/api/schedules/${scheduleId}`);
    return res.data;
  },

  async create(data: ScheduleCreateRequest): Promise<Schedule> {
    const res = await client.post<Schedule>('/api/schedules/', data);
    return res.data;
  },

  async update(scheduleId: string, data: ScheduleUpdateRequest): Promise<Schedule> {
    const res = await client.patch<Schedule>(`/api/schedules/${scheduleId}`, data);
    return res.data;
  },

  async delete(scheduleId: string): Promise<{ message: string }> {
    const res = await client.delete<{ message: string }>(`/api/schedules/${scheduleId}`);
    return res.data;
  },

  async pause(scheduleId: string): Promise<Schedule> {
    const res = await client.post<Schedule>(`/api/schedules/${scheduleId}/pause`);
    return res.data;
  },

  async resume(scheduleId: string): Promise<Schedule> {
    const res = await client.post<Schedule>(`/api/schedules/${scheduleId}/resume`);
    return res.data;
  },

  async trigger(scheduleId: string): Promise<{ message: string; task_id: string }> {
    const res = await client.post<{ message: string; task_id: string }>(`/api/schedules/${scheduleId}/trigger`);
    return res.data;
  },
};
