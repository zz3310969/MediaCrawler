import { PlatformInfo, NavItem } from '../types';

// 平台列表
export const PLATFORMS: PlatformInfo[] = [
  {
    id: 'xiaohongshu',
    name: '小红书',
    icon: '📕',
    description: '生活方式分享平台',
    color: '#EF4444',
  },
  {
    id: 'douyin',
    name: '抖音',
    icon: '🎵',
    description: '短视频分享平台',
    color: '#0D0D0D',
  },
  {
    id: 'bilibili',
    name: 'B站',
    icon: '📺',
    description: '视频弹幕网站',
    color: '#FB7185',
  },
  {
    id: 'weibo',
    name: '微博',
    icon: '📰',
    description: '社交媒体平台',
    color: '#EF4444',
  },
  {
    id: 'wechat',
    name: '微信公众号',
    icon: '💬',
    description: '内容订阅平台',
    color: '#22C55E',
  },
  {
    id: 'zhihu',
    name: '知乎',
    icon: '❓',
    description: '知识问答平台',
    color: '#0084FF',
  },
  {
    id: 'tieba',
    name: '贴吧',
    icon: '📝',
    description: '综合论坛平台',
    color: '#3B82F6',
  },
  {
    id: 'kuaishou',
    name: '快手',
    icon: '⚡',
    description: '短视频平台',
    color: '#FF6600',
  },
];

// 导航菜单
export const NAV_ITEMS: NavItem[] = [
  {
    id: 'dashboard',
    label: '仪表盘',
    icon: 'LayoutDashboard',
    path: '/',
  },
  {
    id: 'tasks',
    label: '任务管理',
    icon: 'ListTodo',
    path: '/tasks',
  },
  {
    id: 'data',
    label: '数据管理',
    icon: 'FolderOpen',
    path: '/data',
  },
  {
    id: 'proxy',
    label: '代理池管理',
    icon: 'Server',
    path: '/proxy',
  },
  {
    id: 'accounts',
    label: '账号管理',
    icon: 'Users',
    path: '/accounts',
  },
  {
    id: 'settings',
    label: '系统设置',
    icon: 'Settings',
    path: '/settings',
  },
];

// 时间范围选项
export const TIME_RANGE_OPTIONS = [
  { value: 'all', label: '全部时间' },
  { value: 'day', label: '最近一天' },
  { value: 'week', label: '最近一周' },
  { value: 'month', label: '最近一月' },
  { value: 'year', label: '最近一年' },
];

// 排序方式选项
export const SORT_OPTIONS = [
  { value: 'latest', label: '最新发布' },
  { value: 'hot', label: '最热门' },
  { value: 'relevance', label: '相关度' },
];

// 数据类型选项
export const DATA_TYPE_OPTIONS = [
  { value: 'post', label: '帖子/笔记' },
  { value: 'comment', label: '评论' },
  { value: 'user', label: '用户信息' },
  { value: 'video', label: '视频' },
];

// 采集模式选项
export const CRAWL_MODE_OPTIONS = [
  { value: 'search', label: '关键词搜索' },
  { value: 'user', label: '指定用户' },
  { value: 'detail', label: '指定内容' },
  { value: 'hot', label: '热门推荐' },
];

// 任务状态配置
export const TASK_STATUS_CONFIG = {
  running: {
    label: '运行中',
    color: 'primary',
    bgColor: 'bg-primary-100',
    textColor: 'text-primary',
  },
  completed: {
    label: '已完成',
    color: 'success',
    bgColor: 'bg-success-100',
    textColor: 'text-success',
  },
  failed: {
    label: '失败',
    color: 'error',
    bgColor: 'bg-error-100',
    textColor: 'text-error',
  },
  pending: {
    label: '等待中',
    color: 'warning',
    bgColor: 'bg-warning-100',
    textColor: 'text-warning',
  },
  cancelled: {
    label: '已取消',
    color: 'gray',
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-500',
  },
};

// 账号状态配置
export const ACCOUNT_STATUS_CONFIG = {
  active: {
    label: '正常',
    bgColor: 'bg-success-100',
    textColor: 'text-success',
  },
  inactive: {
    label: '失效',
    bgColor: 'bg-error-100',
    textColor: 'text-error',
  },
  pending: {
    label: '待验证',
    bgColor: 'bg-warning-100',
    textColor: 'text-warning',
  },
  expired: {
    label: '已过期',
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-500',
  },
};

// 登录方式配置
export const LOGIN_METHOD_CONFIG = {
  qrcode: {
    label: '扫码登录',
    icon: 'QrCode',
    bgColor: 'bg-primary-100',
  },
  cookie: {
    label: 'Cookie',
    icon: 'Cookie',
    bgColor: 'bg-slate-100',
  },
  phone: {
    label: '手机验证',
    icon: 'Smartphone',
    bgColor: 'bg-purple-100',
  },
};

// API 配置
export const API_CONFIG = {
  BASE_URL: '/api',
  TIMEOUT: 30000,
};

// 查询配置
export const QUERY_CONFIG = {
  RETRY_COUNT: 3,
  STATUS_REFETCH_INTERVAL: 5000,
  STALE_TIME: 1000 * 60, // 1 minute
};

// WebSocket 配置
export const WEBSOCKET_CONFIG = {
  RECONNECT_INTERVAL: 3000,
  HEARTBEAT_INTERVAL: 30000,
};
