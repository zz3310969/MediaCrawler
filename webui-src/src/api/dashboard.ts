/**
 * 仪表盘 API 服务
 */
import { client } from './client'
import type {
  DashboardStats,
  SystemStatus,
  PlatformStats,
  TaskStatsResponse,
  ProxyStats,
  AccountStats,
} from '../types'

export interface DashboardResponse {
  stats: DashboardStats
  system: SystemStatus
  platform_stats: PlatformStats[]
  recent_activities: unknown[]
}

/**
 * 获取仪表盘完整数据
 */
export async function getDashboard(): Promise<DashboardResponse> {
  const response = await client.get<DashboardResponse>('/api/dashboard/')
  return response.data
}

/**
 * 获取任务统计
 */
export async function getTaskStats(): Promise<TaskStatsResponse> {
  const response = await client.get<TaskStatsResponse>('/api/dashboard/tasks')
  return response.data
}

/**
 * 获取代理统计
 */
export async function getProxyStats(): Promise<ProxyStats> {
  const response = await client.get<ProxyStats>('/api/dashboard/proxies')
  return response.data
}

/**
 * 获取账号统计
 */
export async function getAccountStats(): Promise<AccountStats> {
  const response = await client.get<AccountStats>('/api/dashboard/accounts')
  return response.data
}

/**
 * 获取系统状态
 */
export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await client.get<SystemStatus>('/api/dashboard/system')
  return response.data
}

/**
 * 获取各平台统计
 */
export async function getPlatformStats(): Promise<{ items: PlatformStats[] }> {
  const response = await client.get<{ items: PlatformStats[] }>('/api/dashboard/platforms')
  return response.data
}

/**
 * 获取总览数据
 */
export async function getOverview(): Promise<{
  tasks: { total: number; running: number; completed: number; failed: number }
  proxies: { total: number; online: number; health_rate: number }
  accounts: { total: number; active: number }
}> {
  const response = await client.get('/api/dashboard/overview')
  return response.data
}
