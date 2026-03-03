// ==================== 通用类型 ====================

// 平台类型（后端使用简写）
export type Platform = 'xhs' | 'dy' | 'bili' | 'wb' | 'wechat' | 'zhihu' | 'tieba' | 'ks';

// 平台信息
export interface PlatformInfo {
  id: Platform;
  name: string;
  icon: string;
  description: string;
  color: string;
}

// ==================== 任务相关 ====================

// 任务状态
export type TaskStatus = 'running' | 'completed' | 'failed' | 'pending' | 'cancelled';

// 任务类型
export interface Task {
  task_id: string;
  task_name?: string;
  platform: Platform;
  crawler_type: string;
  status: TaskStatus;
  priority: number;
  retry_count: number;
  max_retries: number;
  error_message?: string;
  created_at: number;  // Unix 时间戳
  started_at?: number;
  finished_at?: number;
  config: TaskConfig;
  progress: TaskProgress;
  result: TaskResult;
}

// 任务配置
export interface TaskConfig {
  platform: string;
  crawler_type: 'search' | 'creator' | 'detail' | 'creator_vip' | 'album';
  keywords?: string[];
  creator_ids?: string[];
  note_urls?: string[];
  max_notes: number;
  enable_comments: boolean;
  max_comments_per_note: number;
  enable_media: boolean;
  concurrency: number;
  crawl_interval: number;
  login_type?: string;
  cookies?: string;
  save_option: string;
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
  statistics: Record<string, unknown>;
}

// 任务创建请求
export interface TaskCreateRequest {
  task_name?: string;
  config: TaskConfig;
  priority?: number;
  scheduled_at?: string;
  idempotency_key?: string;
}

// 任务列表请求
export interface TaskListRequest {
  status?: TaskStatus;
  platform?: string;
  crawler_type?: string;
  user_id?: string;
  keyword?: string;
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

// 任务统计响应
export interface TaskStatsResponse {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

// ==================== 账号相关 ====================

// 账号状态
export type AccountStatus = 'active' | 'inactive' | 'expired' | 'banned';

// 登录方式
export type LoginMethod = 'qrcode' | 'cookie' | 'phone';

// 账号类型
export interface Account {
  account_id: string;
  platform: Platform;
  username?: string;
  nickname?: string;
  avatar?: string;
  status: AccountStatus;
  login_method: LoginMethod;
  cookie_valid: number;
  use_count: number;
  last_used_at?: number;
  last_validated_at?: number;
  expires_at?: number;
  created_at: number;
  updated_at: number;
  remark?: string;
}

// 账号创建请求
export interface AccountCreateRequest {
  platform: Platform;
  username?: string;
  nickname?: string;
  login_method: LoginMethod;
  cookies?: string;
  remark?: string;
}

// 账号更新请求
export interface AccountUpdateRequest {
  nickname?: string;
  status?: AccountStatus;
  cookies?: string;
  remark?: string;
}

// 账号列表响应
export interface AccountListResponse {
  items: Account[];
  total: number;
  page: number;
  page_size: number;
}

// 账号统计
export interface AccountStats {
  total: number;
  active: number;
  inactive: number;
  expired: number;
  banned: number;
  by_platform: Record<string, number>;
}

// ==================== 代理相关 ====================

// 代理状态
export type ProxyStatus = 'online' | 'offline' | 'testing' | 'banned';

// 代理协议
export type ProxyProtocol = 'http' | 'https' | 'socks5';

// 代理信息
export interface Proxy {
  proxy_id: string;
  ip: string;
  port: number;
  protocol: ProxyProtocol;
  username?: string;
  password?: string;
  region?: string;
  isp?: string;
  status: ProxyStatus;
  response_time?: number;
  success_rate: number;
  total_requests: number;
  failed_requests: number;
  last_check_at?: number;
  last_used_at?: number;
  created_at: number;
  updated_at: number;
  remark?: string;
}

// 代理导入请求
export interface ProxyImportRequest {
  proxies: string;  // 代理列表文本，每行一个
  protocol?: ProxyProtocol;
}

// 代理列表响应
export interface ProxyListResponse {
  items: Proxy[];
  total: number;
  page: number;
  page_size: number;
}

// 代理池统计
export interface ProxyStats {
  total: number;
  online: number;
  offline: number;
  testing: number;
  banned: number;
  avg_response_time: number;
  avg_success_rate: number;
}

// 代理绑定
export interface ProxyBinding {
  binding_id: string;
  proxy_id: string;
  account_id: string;
  platform: Platform;
  sticky: number;
  created_at: number;
  updated_at: number;
}

// ==================== 仪表盘相关 ====================

// 仪表盘统计
export interface DashboardStats {
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  pending_tasks: number;
  total_data: string;
  total_data_count: number;
  active_proxies: number;
  proxy_health: string;
  proxy_health_value: number;
  active_accounts: number;
  total_accounts: number;
}

// 平台数据统计
export interface PlatformStats {
  platform: Platform;
  platform_name: string;
  task_count: number;
  data_count: number;
  account_count: number;
  trend: 'up' | 'down' | 'stable';
}

// 系统状态
export interface SystemStatus {
  cpu: number;
  memory: number;
  disk: number;
  network: string;
  uptime: string;
}

// 仪表盘响应
export interface DashboardResponse {
  stats: DashboardStats;
  system: SystemStatus;
  platform_stats: PlatformStats[];
  recent_activities: ActivityLog[];
}

// 活动日志
export interface ActivityLog {
  id: string;
  type: string;
  message: string;
  timestamp: number;
  details?: Record<string, unknown>;
}

// ==================== 用户相关 ====================

// 用户角色
export type UserRole = 'admin' | 'user';

// 用户状态
export type UserStatus = 'active' | 'inactive' | 'banned';

// 用户
export interface User {
  user_id: string;
  username: string;
  nickname?: string;
  email?: string;
  avatar?: string;
  role: UserRole;
  status: UserStatus;
  last_login_at?: number;
  last_login_ip?: string;
  created_at: number;
  updated_at: number;
}

// 用户创建请求
export interface UserCreateRequest {
  username: string;
  password: string;
  email?: string;
  nickname?: string;
  role?: UserRole;
}

// 用户更新请求
export interface UserUpdateRequest {
  email?: string;
  nickname?: string;
  avatar?: string;
  status?: UserStatus;
}

// 用户列表响应
export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

// ==================== 系统配置相关 ====================

// 配置项
export interface ConfigItem {
  config_key: string;
  config_value: unknown;
  config_type: string;
  description: string;
  created_at?: number;
  updated_at?: number;
}

// 配置列表响应
export interface ConfigListResponse {
  items: ConfigItem[];
  total: number;
  page: number;
  page_size: number;
}

// ==================== 通用响应 ====================

// 分页参数
export interface PaginationParams {
  page: number;
  page_size: number;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 消息响应
export interface MessageResponse {
  message: string;
}

// 导航项
export interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
}

// ==================== 数据类型（爬取结果） ====================

// 小红书笔记
export interface XiaohongshuNote {
  id: string;
  title: string;
  content: string;
  cover?: string;
  type: 'image' | 'video';
  like_count: number;
  comment_count: number;
  collect_count: number;
  author: {
    id: string;
    nickname: string;
    avatar: string;
  };
  created_at: string;
  tags?: string[];
}

// 抖音视频
export interface DouyinVideo {
  id: string;
  title: string;
  cover: string;
  play_count: number;
  like_count: number;
  comment_count: number;
  share_count: number;
  duration: number;
  author: {
    id: string;
    nickname: string;
    avatar: string;
  };
  created_at: string;
}

// 微信公众号文章
export interface WechatArticle {
  id: string;
  title: string;
  digest: string;
  cover?: string;
  read_count: number;
  like_count: number;
  author: {
    id: string;
    name: string;
    avatar: string;
  };
  published_at: string;
  url: string;
}
