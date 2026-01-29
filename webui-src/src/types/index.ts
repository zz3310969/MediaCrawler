// 平台类型
export type Platform = 
  | 'xiaohongshu' 
  | 'douyin' 
  | 'bilibili' 
  | 'weibo' 
  | 'wechat' 
  | 'zhihu' 
  | 'tieba' 
  | 'kuaishou';

// 平台信息
export interface PlatformInfo {
  id: Platform;
  name: string;
  icon: string;
  description: string;
  color: string;
}

// 任务状态
export type TaskStatus = 'running' | 'completed' | 'failed' | 'pending' | 'cancelled';

// 任务类型
export interface Task {
  id: string;
  name: string;
  platform: Platform;
  status: TaskStatus;
  progress?: number;
  keywords?: string[];
  dataCount?: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
  config?: TaskConfig;
}

// 任务配置
export interface TaskConfig {
  crawlMode: 'search' | 'user' | 'detail' | 'hot';
  keywords?: string;
  userId?: string;
  maxCount: number;
  dataTypes: DataType[];
  timeRange: TimeRange;
  sortBy: SortBy;
  enableProxy: boolean;
  proxyConfig?: ProxyConfig;
}

// 数据类型
export type DataType = 'post' | 'comment' | 'user' | 'video';

// 时间范围
export type TimeRange = 'all' | 'day' | 'week' | 'month' | 'year';

// 排序方式
export type SortBy = 'latest' | 'hot' | 'relevance';

// 代理配置
export interface ProxyConfig {
  proxyPool: string;
  rotateStrategy: 'random' | 'round-robin' | 'weighted';
  retryCount: number;
  timeout: number;
}

// 账号状态
export type AccountStatus = 'active' | 'inactive' | 'pending' | 'expired';

// 登录方式
export type LoginMethod = 'qrcode' | 'cookie' | 'phone';

// 账号类型
export interface Account {
  id: string;
  platform: Platform;
  username: string;
  nickname: string;
  avatar?: string;
  status: AccountStatus;
  loginMethod: LoginMethod;
  lastUsedAt?: string;
  createdAt: string;
  expiresAt?: string;
}

// 统计数据
export interface DashboardStats {
  runningTasks: number;
  runningTasksChange: number;
  completedTasks: number;
  completedTasksChange: number;
  totalData: string;
  totalDataChange: string;
  activeProxies: number;
  proxyHealth: string;
}

// 平台数据统计
export interface PlatformStats {
  platform: Platform;
  taskCount: number;
  dataCount: number;
  trend: 'up' | 'down' | 'stable';
}

// 系统状态
export interface SystemStatus {
  cpu: number;
  memory: number;
  network: string;
  uptime: string;
}

// 小红书笔记
export interface XiaohongshuNote {
  id: string;
  title: string;
  content: string;
  cover?: string;
  type: 'image' | 'video';
  likeCount: number;
  commentCount: number;
  collectCount: number;
  author: {
    id: string;
    nickname: string;
    avatar: string;
  };
  createdAt: string;
  tags?: string[];
}

// 抖音视频
export interface DouyinVideo {
  id: string;
  title: string;
  cover: string;
  playCount: number;
  likeCount: number;
  commentCount: number;
  shareCount: number;
  duration: number;
  author: {
    id: string;
    nickname: string;
    avatar: string;
  };
  createdAt: string;
}

// 微信公众号文章
export interface WechatArticle {
  id: string;
  title: string;
  digest: string;
  cover?: string;
  readCount: number;
  likeCount: number;
  author: {
    id: string;
    name: string;
    avatar: string;
  };
  publishedAt: string;
  url: string;
}

// API 响应
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// 分页参数
export interface PaginationParams {
  page: number;
  pageSize: number;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// 导航项
export interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
}

// 代理状态
export type ProxyStatus = 'online' | 'offline' | 'testing';

// 代理协议
export type ProxyProtocol = 'HTTP' | 'HTTPS' | 'SOCKS5';

// 代理信息
export interface Proxy {
  id: string;
  ip: string;
  port: number;
  protocol: ProxyProtocol;
  username?: string;
  password?: string;
  region?: string;
  remark?: string;
  status: ProxyStatus;
  responseTime?: number;
  successRate?: number;
  lastCheckedAt?: string;
  createdAt: string;
}

// 代理池统计
export interface ProxyStats {
  total: number;
  online: number;
  offline: number;
  avgResponseTime: number;
  weeklyChange: {
    total: number;
    online: number;
    offline: number;
    responseTime: number;
  };
}
