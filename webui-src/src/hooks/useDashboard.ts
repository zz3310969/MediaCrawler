/**
 * 仪表盘数据 Hooks
 */
import { useCallback } from 'react'
import { useApi, usePollingApi } from './useApi'
import {
  getDashboard,
  getTaskStats,
  getProxyStats,
  getAccountStats,
  getSystemStatus,
  getPlatformStats,
  type DashboardResponse,
} from '../api/dashboard'
import type { TaskStatsResponse, ProxyStats, AccountStats, SystemStatus, PlatformStats } from '../types'

/**
 * 获取完整仪表盘数据
 */
export function useDashboard() {
  const fetcher = useCallback(() => getDashboard(), [])
  return useApi<DashboardResponse>(fetcher, [])
}

/**
 * 获取仪表盘数据（带轮询）
 */
export function useDashboardPolling(intervalMs: number = 30000) {
  const fetcher = useCallback(() => getDashboard(), [])
  return usePollingApi<DashboardResponse>(fetcher, intervalMs)
}

/**
 * 获取任务统计
 */
export function useTaskStats() {
  const fetcher = useCallback(() => getTaskStats(), [])
  return useApi<TaskStatsResponse>(fetcher, [])
}

/**
 * 获取代理统计
 */
export function useProxyStats() {
  const fetcher = useCallback(() => getProxyStats(), [])
  return useApi<ProxyStats>(fetcher, [])
}

/**
 * 获取账号统计
 */
export function useAccountStats() {
  const fetcher = useCallback(() => getAccountStats(), [])
  return useApi<AccountStats>(fetcher, [])
}

/**
 * 获取系统状态（带轮询）
 */
export function useSystemStatus(intervalMs: number = 5000) {
  const fetcher = useCallback(() => getSystemStatus(), [])
  return usePollingApi<SystemStatus>(fetcher, intervalMs)
}

/**
 * 获取各平台统计
 */
export function usePlatformStats() {
  const fetcher = useCallback(() => getPlatformStats(), [])
  return useApi<{ items: PlatformStats[] }>(fetcher, [])
}
