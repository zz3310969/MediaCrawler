// 爬虫 API 接口
import { client } from './client'

// 类型定义（对应后端的Schema）
export type Platform = 'xhs' | 'dy' | 'ks' | 'bili' | 'wb' | 'wechat' | 'tieba' | 'zhihu'
export type LoginType = 'qrcode' | 'phone' | 'cookie' | 'mp_qrcode'
export type CrawlerType = 'search' | 'detail' | 'creator' | 'creator_vip' | 'album'
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
  // 微信专用配置
  wechat_enable_content?: boolean  // 是否下载文章HTML内容
  wechat_enable_reading_stats?: boolean  // 是否获取阅读量
  wechat_enable_export?: boolean  // 是否启用导出
  wechat_export_format?: 'html' | 'markdown' | 'txt' | 'docx' | 'json' | 'excel'  // 导出格式
  wechat_album_ids?: string  // 合集ID列表
  wechat_credentials_uin?: string  // 微信凭证 uin
  wechat_credentials_key?: string  // 微信凭证 key
  wechat_credentials_pass_ticket?: string  // 微信凭证 pass_ticket
  wechat_token?: string // 微信后台 token
  // 仅登录模式
  login_only?: boolean  // 是否只登录获取Cookie/Token，不进行数据爬取
}

export interface CrawlerStatus {
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform?: string
  crawler_type?: string
  started_at?: string
  error_message?: string
  // 进度信息
  progress?: CrawlerProgress
  new_cookies?: string // 登录成功后获取的新Cookie
  new_token?: string // 登录成功后获取的新Token
  qrcode_img?: string // 扫码登录的二维码 (base64)
}

export interface CrawlerProgress {
  articles_crawled?: number
  articles_total?: number
  comments_crawled?: number
  resources_downloaded?: number
  exports_completed?: number
  current_account?: string
  current_album?: string
  percentage?: number
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

// 微信文章类型
export interface WeChatArticleItem {
  id: number
  article_id: string
  title: string
  account_name: string
  read_num: number
  like_num: number
  comment_count: number
  create_time: number
  link: string
  cover?: string
}

// 微信文章列表响应
export interface WeChatArticleListResponse {
  articles: WeChatArticleItem[]
  total: number
  page: number
  page_size: number
}

// 微信统计数据
export interface WeChatStats {
  total_articles: number
  total_reads: number
  total_likes: number
  total_accounts: number
  today_articles: number
  today_reads: number
}

// 热门文章
export interface WeChatTopArticle {
  id: number
  title: string
  account_name: string
  read_num: number
  create_time: number
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
  
  // 微信公众号搜索 (需登录)
  searchWeChatAccount: (keyword: string, cookies: string, token: string) => {
    return client.post<{ list: any[] }>('/api/wechat/search_account', { 
      keyword, 
      cookies, 
      token 
    })
  },
  
  // 获取微信文章列表
  getWeChatArticles: (params: {
    page?: number
    page_size?: number
    search?: string
    time_range?: 'today' | 'week' | 'month' | 'all'
    order_by?: 'create_time' | 'read_num' | 'like_num'
    order_dir?: 'asc' | 'desc'
  } = {}) => {
    const queryParams = new URLSearchParams()
    if (params.page) queryParams.append('page', params.page.toString())
    if (params.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params.search) queryParams.append('search', params.search)
    if (params.time_range) queryParams.append('time_range', params.time_range)
    if (params.order_by) queryParams.append('order_by', params.order_by)
    if (params.order_dir) queryParams.append('order_dir', params.order_dir)
    return client.get<WeChatArticleListResponse>(`/api/wechat/articles?${queryParams.toString()}`)
  },
  
  // 获取微信统计数据
  getWeChatStats: () => {
    return client.get<WeChatStats>('/api/wechat/stats')
  },
  
  // 获取热门文章
  getWeChatTopArticles: (limit = 5) => {
    return client.get<WeChatTopArticle[]>(`/api/wechat/top_articles?limit=${limit}`)
  },
}

