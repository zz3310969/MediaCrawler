/**
 * 系统配置 API
 */
import { client } from './client'

export type ConfigType =
  | 'crawler'
  | 'browser'
  | 'proxy'
  | 'account'
  | 'system'
  | 'webhook'
  | 'external'

export interface ConfigItem {
  config_key: string
  config_value: unknown
  config_type: string
  description: string
  created_at?: number
  updated_at?: number
}

export interface ConfigListResponse {
  items: ConfigItem[]
  total: number
  page: number
  page_size: number
}

export type ConfigDict = Record<string, unknown>

export const configApi = {
  async getGroup(configType: ConfigType): Promise<ConfigDict> {
    const res = await client.get<ConfigDict>(`/api/config/${configType}`)
    return res.data
  },

  async updateGroup(configType: ConfigType, configs: ConfigDict): Promise<void> {
    await client.put(`/api/config/${configType}`, configs)
  },

  async getByKey(configKey: string): Promise<{ key: string; value: unknown }> {
    const res = await client.get<{ key: string; value: unknown }>(
      `/api/config/key/${configKey}`
    )
    return res.data
  },

  async set(
    configKey: string,
    configValue: unknown,
    configType: ConfigType = 'system',
    description = ''
  ): Promise<void> {
    await client.post('/api/config/', {
      config_key: configKey,
      config_value: configValue,
      config_type: configType,
      description,
    })
  },

  async deleteKey(configKey: string): Promise<void> {
    await client.delete(`/api/config/key/${configKey}`)
  },

  async initDefaults(): Promise<{ message: string }> {
    const res = await client.post<{ message: string }>('/api/config/init')
    return res.data
  },

  async list(params?: {
    config_type?: string
    keyword?: string
    page?: number
    page_size?: number
  }): Promise<ConfigListResponse> {
    const res = await client.get<ConfigListResponse>('/api/config/', { params })
    return res.data
  },

  async testCos(params: {
    secret_id: string
    secret_key: string
    region: string
    bucket_name: string
  }): Promise<{ success: boolean; message: string }> {
    const res = await client.post<{ success: boolean; message: string }>(
      '/api/config/test-cos',
      params
    )
    return res.data
  },
}
