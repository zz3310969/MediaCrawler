// 爬虫 API 接口
import { client } from './client'

// 类型定义（对应后端的Schema）
export type Platform = 'xhs' | 'dy' | 'ks' | 'bili' | 'wb' | 'tieba' | 'zhihu'
export type LoginType = 'qrcode' | 'phone' | 'cookie'
export type CrawlerType = 'search' | 'detail' | 'creator' | 'creator_vip'
export type SaveOption = 'json' | 'csv' | 'db' | 'sqlite' | 'mongodb' | 'excel'

export interface CrawlerStartRequest {
  platform: Platform
  login_type: LoginType
  crawler_type: CrawlerType
  keywords?: string
  specified_ids?: string
  creator_ids?: string
  vip_creator_ids?: string
  start_page?: number
  enable_comments?: boolean
  enable_sub_comments?: boolean
  save_option?: SaveOption
  cookies?: string
  headless?: boolean
  // 增量爬取配置
  enable_incremental?: boolean  // 是否启用增量爬取
  incremental_early_stop?: number  // 早停阈值
}

export interface CrawlerStatus {
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform?: string
  crawler_type?: string
  started_at?: string
  error_message?: string
}

export interface LogEntry {
  id: number
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success' | 'debug'
  message: string
}

// 配置选项类型
export interface PlatformOption {
  value: string
  label: string
  icon: string
}

export interface ConfigOption {
  value: string
  label: string
}

export interface IncrementalConfig {
  description: string
  supports_platforms: Platform[]
  supports_crawler_types: CrawlerType[]
  default_enabled: boolean
  default_threshold: number
  threshold_range: {
    min: number
    max: number
  }
}

export interface ConfigOptions {
  login_types: ConfigOption[]
  crawler_types: ConfigOption[]
  save_options: ConfigOption[]
  incremental_config?: IncrementalConfig
}

// 数据文件类型
export interface DataFile {
  name: string
  path: string
  size: number
  modified_at: number
  record_count: number | null
  type: string
}

// API 方法
export const crawlerApi = {
  // 启动爬虫
  start: (data: CrawlerStartRequest) => 
    client.post<void>('/api/crawler/start', data),
  
  // 停止爬虫
  stop: () => 
    client.post<void>('/api/crawler/stop'),
  
  // 获取状态
  getStatus: () => 
    client.get<CrawlerStatus>('/api/crawler/status'),
  
  // 获取日志
  getLogs: (limit = 100) => 
    client.get<{ logs: LogEntry[] }>(`/api/crawler/logs?limit=${limit}`),
  
  // 获取平台列表
  getPlatforms: () => 
    client.get<{ platforms: PlatformOption[] }>('/api/config/platforms'),
  
  // 获取配置选项
  getConfigOptions: () => 
    client.get<ConfigOptions>('/api/config/options'),
  
  // 获取数据文件列表
  getDataFiles: (platform?: string, fileType?: string) => {
    const params = new URLSearchParams()
    if (platform) params.append('platform', platform)
    if (fileType) params.append('file_type', fileType)
    return client.get<{ files: DataFile[] }>(`/api/data/files?${params.toString()}`)
  },
  
  // 下载数据文件
  downloadFile: (filePath: string) => {
    return `/api/data/download/${filePath}`
  },
}

