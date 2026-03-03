/**
 * 账号管理 API 服务
 */
import { client } from './client'
import type {
  Account,
  AccountCreateRequest,
  AccountUpdateRequest,
  AccountListResponse,
  AccountStats,
  Platform,
} from '../types'

/**
 * 获取账号列表
 */
export async function getAccounts(params?: {
  platform?: Platform
  status?: string
  page?: number
  page_size?: number
}): Promise<AccountListResponse> {
  const response = await client.get<AccountListResponse>('/api/accounts/', { params })
  return response.data
}

/**
 * 获取单个账号
 */
export async function getAccount(accountId: string): Promise<Account> {
  const response = await client.get<Account>(`/api/accounts/${accountId}`)
  return response.data
}

/**
 * 创建账号
 */
export async function createAccount(data: AccountCreateRequest): Promise<Account> {
  const response = await client.post<Account>('/api/accounts/', data)
  return response.data
}

/**
 * 更新账号
 */
export async function updateAccount(accountId: string, data: AccountUpdateRequest): Promise<Account> {
  const response = await client.put<Account>(`/api/accounts/${accountId}`, data)
  return response.data
}

/**
 * 删除账号
 */
export async function deleteAccount(accountId: string): Promise<{ message: string }> {
  const response = await client.delete<{ message: string }>(`/api/accounts/${accountId}`)
  return response.data
}

/**
 * 验证账号
 */
export async function validateAccount(accountId: string): Promise<Account> {
  const response = await client.post<Account>(`/api/accounts/${accountId}/validate`)
  return response.data
}

/**
 * 批量删除账号
 */
export async function batchDeleteAccounts(accountIds: string[]): Promise<{ message: string }> {
  const response = await client.post<{ message: string }>('/api/accounts/batch/delete', {
    account_ids: accountIds,
  })
  return response.data
}

/**
 * 获取账号统计
 */
export async function getAccountStats(): Promise<AccountStats> {
  const response = await client.get<AccountStats>('/api/accounts/stats')
  return response.data
}

/**
 * 获取指定平台的活跃账号
 */
export async function getActiveAccountsByPlatform(platform: Platform): Promise<{
  items: Account[]
  total: number
}> {
  const response = await client.get<{ items: Account[]; total: number }>(
    `/api/accounts/platform/${platform}/active`
  )
  return response.data
}
