import { client } from './client';

export interface AntiDetectConfig {
  enable_fingerprint: boolean;
  enable_rate_limit: boolean;
  enable_human_behavior: boolean;
  enable_account_health: boolean;
  enable_binding: boolean;
  fingerprint_platform_hint?: string;
  rate_limit_min_interval: number;
  rate_limit_max_interval: number;
  rate_limit_hourly_limit: number;
  rate_limit_daily_limit: number;
  account_cooling_threshold: number;
  account_warning_threshold: number;
}

export interface AntiDetectStats {
  platform: string;
  total_accounts: number;
  active_accounts: number;
  cooling_accounts: number;
  warning_accounts: number;
  banned_accounts: number;
  avg_risk_score: number;
  total_bindings: number;
  with_proxy: number;
  with_fingerprint: number;
  complete_bindings: number;
  total_requests: number;
  hourly_requests: number;
  daily_requests: number;
  hourly_limit: number;
  daily_limit: number;
}

export interface AccountHealthStatus {
  account_id: string;
  platform: string;
  total_requests: number;
  failed_requests: number;
  captcha_count: number;
  risk_score: number;
  status: 'active' | 'cooling' | 'warning' | 'banned';
  last_request_at?: string;
  cooling_until?: string;
  bound_proxy_id?: string;
  bound_fingerprint_id?: string;
}

export interface BindingInfo {
  account_id: string;
  platform: string;
  proxy_id?: string;
  fingerprint_id?: string;
  created_at: string;
  updated_at: string;
}

export const antiDetectApi = {
  // 获取统计信息
  getStats: async (platform: string): Promise<AntiDetectStats> => {
    const response = await client.get(`/api/anti-detect/stats/${platform}`);
    return response.data;
  },

  // 获取账号健康列表
  getAccountHealth: async (
    platform: string,
    page = 1,
    pageSize = 20
  ): Promise<{ accounts: AccountHealthStatus[]; total: number; page: number; page_size: number }> => {
    const response = await client.get(`/api/anti-detect/accounts/${platform}`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  // 获取绑定列表
  getBindings: async (
    platform: string,
    page = 1,
    pageSize = 20
  ): Promise<{ bindings: BindingInfo[]; total: number; page: number; page_size: number }> => {
    const response = await client.get(`/api/anti-detect/bindings/${platform}`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  // 绑定代理
  bindProxy: async (platform: string, accountId: string, proxyId: string): Promise<void> => {
    await client.post(`/api/anti-detect/bindings/${platform}/${accountId}/proxy`, null, {
      params: { proxy_id: proxyId },
    });
  },

  // 删除绑定
  deleteBinding: async (platform: string, accountId: string): Promise<void> => {
    await client.delete(`/api/anti-detect/bindings/${platform}/${accountId}`);
  },

  // 获取默认配置
  getDefaultConfig: async (platform?: string): Promise<AntiDetectConfig> => {
    const response = await client.get('/api/anti-detect/config/default', {
      params: platform ? { platform } : {},
    });
    return response.data;
  },
};
