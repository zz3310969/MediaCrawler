/**
 * 数据管理 API 服务
 */
import { client } from './client'

// 数据文件信息
export interface DataFile {
  name: string
  path: string
  size: number
  modified_at: number
  record_count: number | null
  type: string
}

// 数据统计
export interface DataStats {
  total_files: number
  total_size: number
  by_platform: Record<string, number>
  by_type: Record<string, number>
}

// 文件内容响应
export interface FileContentResponse {
  data: Record<string, unknown>[]
  total: number
  columns?: string[]
}

/**
 * 获取数据文件列表
 */
export async function getDataFiles(params?: {
  platform?: string
  file_type?: string
}): Promise<{ files: DataFile[] }> {
  const response = await client.get<{ files: DataFile[] }>('/api/data/files', { params })
  return response.data
}

/**
 * 获取文件内容预览
 */
export async function getFileContent(
  filePath: string,
  params?: { preview?: boolean; limit?: number }
): Promise<FileContentResponse> {
  const response = await client.get<FileContentResponse>(
    `/api/data/files/${encodeURIComponent(filePath)}`,
    { params: { preview: true, limit: 100, ...params } }
  )
  return response.data
}

/**
 * 下载文件
 */
export function getDownloadUrl(filePath: string): string {
  const baseUrl = import.meta.env.DEV ? 'http://127.0.0.1:8080' : ''
  return `${baseUrl}/api/data/download/${encodeURIComponent(filePath)}`
}

/**
 * 获取数据统计
 */
export async function getDataStats(): Promise<DataStats> {
  const response = await client.get<DataStats>('/api/data/stats')
  return response.data
}
