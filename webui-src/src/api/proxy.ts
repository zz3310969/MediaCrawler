// 代理管理 API 客户端

import { client } from './client';
import type {
  ProxyInfo,
  ProxyWithQuality,
  OverviewStats,
  QualityMetrics,
  ProxySettings,
  SourceConfig,
  ProxyListResponse,
  BindingListResponse,
  ProxyImportItem,
} from '../types/proxy';

// ==================== 代理管理 API ====================

export const proxyApi = {
  // 获取代理列表
  getProxyList: async (params?: {
    source?: string;
    protocol?: string;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<ProxyListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.source) searchParams.set('source', params.source);
    if (params?.protocol) searchParams.set('protocol', params.protocol);
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const query = searchParams.toString();
    const response = await client.get(`/api/proxy/list${query ? `?${query}` : ''}`);
    return response.data;
  },

  // 获取代理详情
  getProxyDetail: async (proxyId: string): Promise<ProxyWithQuality> => {
    const response = await client.get(`/api/proxy/${proxyId}`);
    return response.data;
  },

  // 导入代理
  importProxies: async (
    proxies: ProxyImportItem[],
    source: string = 'manual'
  ): Promise<{ success: boolean; imported_count: number; failed_count: number; message: string }> => {
    const response = await client.post('/api/proxy/import', { proxies, source });
    return response.data;
  },

  // 删除代理
  deleteProxy: async (proxyId: string): Promise<{ success: boolean; message: string }> => {
    const response = await client.delete(`/api/proxy/${proxyId}`);
    return response.data;
  },

  // 批量删除代理
  batchDeleteProxies: async (
    proxyIds: string[]
  ): Promise<{ success: boolean; message: string }> => {
    const response = await client.post('/api/proxy/batch-delete', { proxy_ids: proxyIds });
    return response.data;
  },

  // 更新代理状态
  updateProxyStatus: async (
    proxyId: string,
    isActive: boolean
  ): Promise<{ success: boolean; message: string }> => {
    const response = await client.patch(`/api/proxy/${proxyId}/status`, { is_active: isActive });
    return response.data;
  },

  // ==================== 绑定管理 ====================

  // 获取绑定列表
  getBindingList: async (params?: {
    platform?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<BindingListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.platform) searchParams.set('platform', params.platform);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));

    const query = searchParams.toString();
    const response = await client.get(`/api/proxy/bindings/list${query ? `?${query}` : ''}`);
    return response.data;
  },

  // 创建绑定
  createBinding: async (data: {
    account_id: string;
    platform: string;
    proxy_id: string;
    is_sticky?: boolean;
    allow_auto_rebind?: boolean;
  }): Promise<{ success: boolean; message: string }> => {
    const response = await client.post('/api/proxy/bindings/bind', data);
    return response.data;
  },

  // 删除绑定
  deleteBinding: async (
    accountId: string,
    platform: string
  ): Promise<{ success: boolean; message: string }> => {
    const response = await client.delete(`/api/proxy/bindings/${accountId}/${platform}`);
    return response.data;
  },

  // 批量绑定
  batchBind: async (
    bindings: Array<{
      account_id: string;
      platform: string;
      proxy_id: string;
      is_sticky?: boolean;
    }>
  ): Promise<{ success: boolean; message: string }> => {
    const response = await client.post('/api/proxy/bindings/batch-bind', { bindings });
    return response.data;
  },

  // 批量解绑
  batchUnbind: async (
    accountIds: string[],
    platform: string
  ): Promise<{ success: boolean; message: string }> => {
    const response = await client.post('/api/proxy/bindings/batch-unbind', {
      account_ids: accountIds,
      platform,
    });
    return response.data;
  },

  // ==================== 统计 ====================

  // 获取概览统计
  getOverviewStats: async (): Promise<OverviewStats> => {
    const response = await client.get('/api/proxy/statistics/overview');
    return response.data;
  },

  // 获取代理统计
  getProxyStats: async (proxyId: string): Promise<QualityMetrics> => {
    const response = await client.get(`/api/proxy/statistics/proxy/${proxyId}`);
    return response.data;
  },

  // ==================== 设置 ====================

  // 获取代理设置
  getProxySettings: async (): Promise<ProxySettings> => {
    const response = await client.get('/api/proxy/settings');
    return response.data;
  },

  // 获取代理来源
  getProxySources: async (): Promise<{ sources: SourceConfig[] }> => {
    const response = await client.get('/api/proxy/sources');
    return response.data;
  },

  // ==================== 工具函数 ====================

  formatProxyUrl: (proxy: ProxyInfo): string => {
    if (proxy.username) {
      return `${proxy.protocol}://${proxy.username}:****@${proxy.ip}:${proxy.port}`;
    }
    return `${proxy.protocol}://${proxy.ip}:${proxy.port}`;
  },

  getQualityColor: (score: number): string => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    if (score >= 40) return 'text-orange-500';
    return 'text-red-500';
  },

  getStatusBadgeVariant: (status: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status) {
      case 'active':
        return 'default';
      case 'expired':
        return 'destructive';
      case 'unbound':
        return 'secondary';
      default:
        return 'outline';
    }
  },
};
