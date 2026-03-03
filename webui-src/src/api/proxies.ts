/**
 * 代理管理 API 服务
 */
import { client } from './client'
import type {
  Proxy,
  ProxyListResponse,
  ProxyStats,
  ProxyImportRequest,
  ProxyStatus,
  ProxyProtocol,
} from '../types'

/**
 * 获取代理列表
 */
export async function getProxies(params?: {
  status?: ProxyStatus
  protocol?: ProxyProtocol
  region?: string
  page?: number
  page_size?: number
}): Promise<ProxyListResponse> {
  const response = await client.get<ProxyListResponse>('/api/proxy/pool/', { params })
  return response.data
}

/**
 * 获取单个代理
 */
export async function getProxy(proxyId: string): Promise<Proxy> {
  const response = await client.get<Proxy>(`/api/proxy/pool/${proxyId}`)
  return response.data
}

/**
 * 创建代理
 */
export async function createProxy(data: Partial<Proxy>): Promise<Proxy> {
  const response = await client.post<Proxy>('/api/proxy/pool/', data)
  return response.data
}

/**
 * 更新代理
 */
export async function updateProxy(proxyId: string, data: Partial<Proxy>): Promise<Proxy> {
  const response = await client.put<Proxy>(`/api/proxy/pool/${proxyId}`, data)
  return response.data
}

/**
 * 删除代理
 */
export async function deleteProxy(proxyId: string): Promise<{ message: string }> {
  const response = await client.delete<{ message: string }>(`/api/proxy/pool/${proxyId}`)
  return response.data
}

/**
 * 批量导入代理
 */
export async function importProxies(data: ProxyImportRequest): Promise<{
  message: string
  imported: number
  failed: number
}> {
  const response = await client.post('/api/proxy/pool/import', data)
  return response.data
}

/**
 * 测试代理
 */
export async function testProxy(proxyId: string): Promise<{
  success: boolean
  response_time?: number
  error?: string
}> {
  const response = await client.post(`/api/proxy/pool/${proxyId}/test`)
  return response.data
}

/**
 * 批量测试代理
 */
export async function batchTestProxies(proxyIds: string[]): Promise<{ message: string }> {
  const response = await client.post('/api/proxy/pool/batch/test', {
    proxy_ids: proxyIds,
  })
  return response.data
}

/**
 * 批量删除代理
 */
export async function batchDeleteProxies(proxyIds: string[]): Promise<{ message: string }> {
  const response = await client.post('/api/proxy/pool/batch/delete', {
    proxy_ids: proxyIds,
  })
  return response.data
}

/**
 * 获取代理统计
 */
export async function getProxyStats(): Promise<ProxyStats> {
  const response = await client.get<ProxyStats>('/api/proxy/stats')
  return response.data
}
