/**
 * 账号管理 Hooks
 */
import { useCallback } from 'react'
import { useApi, useMutation } from './useApi'
import {
  getAccounts,
  getAccount,
  createAccount,
  updateAccount,
  deleteAccount,
  validateAccount,
  batchDeleteAccounts,
} from '../api/accounts'
import type {
  Account,
  AccountCreateRequest,
  AccountUpdateRequest,
  AccountListResponse,
  Platform,
} from '../types'

/**
 * 获取账号列表
 */
export function useAccounts(params?: {
  platform?: Platform
  status?: string
  page?: number
  page_size?: number
}) {
  const fetcher = useCallback(
    () => getAccounts(params),
    [params?.platform, params?.status, params?.page, params?.page_size]
  )
  return useApi<AccountListResponse>(fetcher, [
    params?.platform,
    params?.status,
    params?.page,
    params?.page_size,
  ])
}

/**
 * 获取单个账号
 */
export function useAccount(accountId: string) {
  const fetcher = useCallback(() => getAccount(accountId), [accountId])
  return useApi<Account>(fetcher, [accountId])
}

/**
 * 创建账号
 */
export function useCreateAccount() {
  return useMutation<Account, AccountCreateRequest>(createAccount)
}

/**
 * 更新账号
 */
export function useUpdateAccount() {
  const mutator = useCallback(
    (params: { accountId: string; data: AccountUpdateRequest }) =>
      updateAccount(params.accountId, params.data),
    []
  )
  return useMutation<Account, { accountId: string; data: AccountUpdateRequest }>(mutator)
}

/**
 * 删除账号
 */
export function useDeleteAccount() {
  return useMutation<{ message: string }, string>(deleteAccount)
}

/**
 * 验证账号
 */
export function useValidateAccount() {
  return useMutation<Account, string>(validateAccount)
}

/**
 * 批量删除账号
 */
export function useBatchDeleteAccounts() {
  return useMutation<{ message: string }, string[]>(batchDeleteAccounts)
}
