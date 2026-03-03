/**
 * 代理管理 Hooks
 */
import { useCallback } from 'react'
import { useApi, useMutation } from './useApi'
import {
  getProxies,
  getProxy,
  createProxy,
  updateProxy,
  deleteProxy,
  testProxy,
  batchTestProxies,
  batchDeleteProxies,
  getProxyStats,
} from '../api/proxies'
import type {
  Proxy,
  ProxyListResponse,
  ProxyStats,
  ProxyStatus,
  ProxyProtocol,
} from '../types'

/**
 * 获取代理列表
 */
export function useProxies(params?: {
  status?: ProxyStatus
  protocol?: ProxyProtocol
  region?: string
  page?: number
  page_size?: number
}) {
  const fetcher = useCallback(
    () => getProxies(params),
    [params?.status, params?.protocol, params?.region, params?.page, params?.page_size]
  )
  return useApi<ProxyListResponse>(fetcher, [
    params?.status,
    params?.protocol,
    params?.region,
    params?.page,
    params?.page_size,
  ])
}

/**
 * 获取单个代理
 */
export function useProxy(proxyId: string) {
  const fetcher = useCallback(() => getProxy(proxyId), [proxyId])
  return useApi<Proxy>(fetcher, [proxyId])
}

/**
 * 获取代理统计
 */
export function useProxyStats() {
  const fetcher = useCallback(() => getProxyStats(), [])
  return useApi<ProxyStats>(fetcher, [])
}

/**
 * 创建代理
 */
export function useCreateProxy() {
  return useMutation<Proxy, Partial<Proxy>>(createProxy)
}

/**
 * 更新代理
 */
export function useUpdateProxy() {
  const mutator = useCallback(
    (params: { proxyId: string; data: Partial<Proxy> }) =>
      updateProxy(params.proxyId, params.data),
    []
  )
  return useMutation<Proxy, { proxyId: string; data: Partial<Proxy> }>(mutator)
}

/**
 * 删除代理
 */
export function useDeleteProxy() {
  return useMutation<{ message: string }, string>(deleteProxy)
}

/**
 * 测试代理
 */
export function useTestProxy() {
  return useMutation<{ success: boolean; response_time?: number; error?: string }, string>(
    testProxy
  )
}

/**
 * 批量测试代理
 */
export function useBatchTestProxies() {
  return useMutation<{ message: string }, string[]>(batchTestProxies)
}

/**
 * 批量删除代理
 */
export function useBatchDeleteProxies() {
  return useMutation<{ message: string }, string[]>(batchDeleteProxies)
}
