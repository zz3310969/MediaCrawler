/**
 * 数据管理 Hooks
 */
import { useCallback } from 'react'
import { useApi } from './useApi'
import {
  getDataFiles,
  getFileContent,
  getDataStats,
  type DataFile,
  type DataStats,
  type FileContentResponse,
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
