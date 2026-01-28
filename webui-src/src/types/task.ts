/**
 * 任务相关类型定义
 */

// 任务状态
export type TaskStatus = 
  | 'pending' 
  | 'running' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

// 平台
export type Platform = 'xhs' | 'dy' | 'bili' | 'wb' | 'wechat' | 'ks' | 'tieba' | 'zhihu';

// 爬取类型
export type CrawlerType = 'search' | 'creator' | 'detail' | 'creator_vip' | 'album';

// 日志级别
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// 任务配置
export interface TaskConfig {
  // 基本配置
  platform: Platform;
  crawler_type: CrawlerType;
  
  // 搜索配置
  keywords?: string[];                         // 搜索关键词列表
  
  // 创作者配置
  creator_ids?: string[];                      // 创作者 ID 或 URL 列表
  
  // 详情配置
  note_urls?: string[];                        // 笔记/视频 URL 列表
  
  // 爬取数量配置
  max_notes: number;                           // 最大爬取笔记数
  enable_comments: boolean;                    // 是否爬取评论
  max_comments_per_note?: number;              // 每个笔记最大评论数
  enable_media?: boolean;                      // 是否下载图片/视频
  
  // 执行配置
  concurrency?: number;                        // 并发数
  crawl_interval?: number;                     // 请求间隔（秒）
  
  // 登录配置
  login_type?: 'cookie' | 'qrcode';            // 登录类型
  cookies?: string;                            // Cookie 字符串
  
  // 存储配置
  save_option: 'csv' | 'json' | 'excel' | 'db' | 'sqlite';
  
  // 可扩展字段
  extra?: Record<string, unknown>;
}

// 任务进度
export interface TaskProgress {
  current: number;
  total: number;
  percentage: number;
  items_crawled: number;
  comments_crawled: number;
}

// 任务结果
export interface TaskResult {
  success: boolean;
  error_message?: string;
  output_path?: string;
  statistics?: Record<string, unknown>;
}

// 任务元数据
export interface TaskMetadata {
  sign_server_used: boolean;
  execution_node?: string;
  resource_usage?: Record<string, unknown>;
}

// 任务实体
export interface Task {
  task_id: string;
  session_id: string;
  task_name?: string;
  status: TaskStatus;
  priority: number;
  retry_count: number;
  max_retries: number;
  idempotency_key?: string;
  cancel_requested: boolean;
  created_at: string;
  scheduled_at?: string;
  started_at?: string;
  finished_at?: string;
  last_heartbeat_at?: string;
  config: TaskConfig;
  progress: TaskProgress;
  result: TaskResult;
  metadata: TaskMetadata;
  version: number;
}

// 创建任务请求
export interface TaskCreateRequest {
  task_name?: string;
  config: TaskConfig;
  priority?: number;
  scheduled_at?: string;
  idempotency_key?: string;
}

// 任务列表查询
export interface TaskListRequest {
  status?: TaskStatus;
  platform?: Platform;
  page?: number;
  page_size?: number;
}

// 任务列表响应
export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}

// 任务统计
export interface TaskStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

// 日志条目
export interface LogEntry {
  log_id: string;
  task_id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  extra?: Record<string, unknown>;
}

// 任务事件
export interface TaskEvent {
  event_id: string;
  event_type: string;
  task_id: string;
  session_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

// 会话配额
export interface SessionQuota {
  max_concurrent_tasks: number;
  max_daily_tasks: number;
  used_daily_tasks: number;
  quota_reset_at: string;
}

// 会话响应
export interface SessionResponse {
  session_id: string;
  user_id?: string;
  created_at: string;
  expires_at: string;
  quota: SessionQuota;
}

// 平台信息
export interface PlatformInfo {
  value: Platform;
  label: string;
  icon?: string;
}

// 爬取类型信息
export interface CrawlerTypeInfo {
  value: CrawlerType;
  label: string;
}

// 优先级
export const TaskPriority = {
  LOW: 1,
  NORMAL: 5,
  HIGH: 8,
  URGENT: 10,
} as const;

// 状态显示配置
export const TaskStatusConfig: Record<TaskStatus, { label: string; color: string; bgColor: string }> = {
  pending: { label: '等待中', color: 'text-gray-700', bgColor: 'bg-gray-100' },
  running: { label: '运行中', color: 'text-blue-700', bgColor: 'bg-blue-100' },
  completed: { label: '已完成', color: 'text-green-700', bgColor: 'bg-green-100' },
  failed: { label: '已失败', color: 'text-red-700', bgColor: 'bg-red-100' },
  cancelled: { label: '已取消', color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
};

// 平台显示配置
export const PlatformConfig: Record<Platform, PlatformInfo> = {
  xhs: { value: 'xhs', label: '小红书', icon: 'book-open' },
  dy: { value: 'dy', label: '抖音', icon: 'music' },
  bili: { value: 'bili', label: 'B站', icon: 'tv' },
  wb: { value: 'wb', label: '微博', icon: 'message-circle' },
  wechat: { value: 'wechat', label: '微信公众号', icon: 'message-square' },
  ks: { value: 'ks', label: '快手', icon: 'video' },
  tieba: { value: 'tieba', label: '百度贴吧', icon: 'messages-square' },
  zhihu: { value: 'zhihu', label: '知乎', icon: 'help-circle' },
};

// 爬取类型配置
export const CrawlerTypeConfig: Record<CrawlerType, CrawlerTypeInfo> = {
  search: { value: 'search', label: '关键词搜索' },
  creator: { value: 'creator', label: '创作者主页' },
  detail: { value: 'detail', label: '帖子详情' },
  creator_vip: { value: 'creator_vip', label: 'VIP内容（微博）' },
  album: { value: 'album', label: '合集模式（微信）' },
};

