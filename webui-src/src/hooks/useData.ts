/**
 * 数据管理 Hooks
 */
import { useCallback } from 'react'
import { useApi } from './useApi'
import {
  getDataFiles,
  getFileContent,
  getDataStats,
  getDbTables,
  queryDbTable,
  getDbStats,
  type DataFile,
  type DataStats,
  type FileContentResponse,
  type DbTablesResponse,
  type DbQueryResponse,
  type DbStatsResponse,
} from '../api/data'

/**
 * 获取数据文件列表
 */
export function useDataFiles(params?: { platform?: string; file_type?: string }) {
  const fetcher = useCallback(
    () => getDataFiles(params),
    [params?.platform, params?.file_type]
  )
  return useApi<{ files: DataFile[] }>(fetcher, [params?.platform, params?.file_type])
}

/**
 * 获取文件内容
 */
export function useFileContent(filePath: string | null, limit: number = 100) {
  const fetcher = useCallback(
    () => (filePath ? getFileContent(filePath, { limit }) : Promise.resolve({ data: [], total: 0 })),
    [filePath, limit]
  )
  return useApi<FileContentResponse>(fetcher, [filePath, limit])
}

/**
 * 获取数据统计
 */
export function useDataStats() {
  const fetcher = useCallback(() => getDataStats(), [])
  return useApi<DataStats>(fetcher, [])
}

/**
 * 获取数据库表列表
 */
export function useDbTables(platform?: string) {
  const fetcher = useCallback(() => getDbTables(platform), [platform])
  return useApi<DbTablesResponse>(fetcher, [platform])
}

/**
 * 查询数据库表数据
 */
export function useDbQuery(params: { table: string; page?: number; page_size?: number; search?: string } | null) {
  const fetcher = useCallback(
    () => (params ? queryDbTable(params) : Promise.resolve({ data: [], total: 0, page: 1, page_size: 50, total_pages: 0, columns: [], table: '', label: '' })),
    [params?.table, params?.page, params?.page_size, params?.search]
  )
  return useApi<DbQueryResponse>(fetcher, [params?.table, params?.page, params?.page_size, params?.search])
}

/**
 * 获取数据库统计
 */
export function useDbStats() {
  const fetcher = useCallback(() => getDbStats(), [])
  return useApi<DbStatsResponse>(fetcher, [])
}
