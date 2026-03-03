import { PlatformInfo, NavItem, Platform } from '../types';

// 平台列表（使用后端平台代码）
export const PLATFORMS: PlatformInfo[] = [
  {
    id: 'xhs',
    name: '小红书',
    icon: '📕',
    description: '生活方式分享平台',
    color: '#EF4444',
  },
  {
    id: 'dy',
    name: '抖音',
    icon: '🎵',
    description: '短视频分享平台',
    color: '#0D0D0D',
  },
  {
    id: 'bili',
    name: 'B站',
    icon: '📺',
    description: '视频弹幕网站',
    color: '#FB7185',
  },
  {
    id: 'wb',
    name: '微博',
    icon: '✍️',
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
    id: 'ks',
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
    id: 'schedules',
    label: '定时调度',
    icon: 'Clock',
    path: '/schedules',
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

// 采集模式选项（对应后端 crawler_type）
export const CRAWL_MODE_OPTIONS = [
  { value: 'search', label: '关键词搜索' },
  { value: 'creator', label: '创作者主页' },
  { value: 'detail', label: '指定内容' },
  { value: 'creator_vip', label: 'VIP内容（微博）' },
  { value: 'album', label: '合集模式（微信）' },
];

// 每个平台支持的采集模式
export const PLATFORM_CRAWL_MODES: Record<Platform, string[]> = {
  xhs: ['search', 'detail', 'creator'],
  dy: ['search', 'detail', 'creator'],
  bili: ['search', 'detail', 'creator'],
  wb: ['search', 'detail', 'creator', 'creator_vip'],
  wechat: ['search', 'detail', 'creator', 'album'],
  ks: ['search', 'detail', 'creator'],
  tieba: ['search', 'detail', 'creator'],
  zhihu: ['search', 'detail', 'creator'],
};

// 平台特有参数配置定义
export interface PlatformFieldDef {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'number' | 'switch';
  placeholder?: string;
  hint?: string;
  options?: { value: string; label: string }[];
  defaultValue?: string | number | boolean;
  showWhen?: string[];  // 仅在指定 crawler_type 下显示
}

// 各平台在不同采集模式下需要的特有字段
export const PLATFORM_FIELDS: Record<Platform, PlatformFieldDef[]> = {
  xhs: [
    {
      key: 'sort_type',
      label: '排序方式',
      type: 'select',
      options: [
        { value: 'general', label: '综合排序' },
        { value: 'popularity_descending', label: '热度降序' },
        { value: 'time_descending', label: '时间降序' },
      ],
      defaultValue: 'general',
      showWhen: ['search'],
    },
    {
      key: 'note_urls',
      label: '笔记URL列表',
      type: 'textarea',
      placeholder: '每行一个URL（需携带 xsec_token 参数）\n例如: https://www.xiaohongshu.com/explore/64b95d01...?xsec_token=xxx',
      hint: 'URL 必须包含 xsec_token 参数',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '创作者URL列表',
      type: 'textarea',
      placeholder: '每行一个创作者主页URL（需携带 xsec_token 参数）\n例如: https://www.xiaohongshu.com/user/profile/xxx?xsec_token=xxx',
      hint: 'URL 必须包含 xsec_token 和 xsec_source 参数',
      showWhen: ['creator'],
    },
  ],
  dy: [
    {
      key: 'publish_time_type',
      label: '发布时间筛选',
      type: 'select',
      options: [
        { value: '0', label: '不限' },
        { value: '1', label: '一天内' },
        { value: '7', label: '一周内' },
        { value: '180', label: '半年内' },
      ],
      defaultValue: '0',
      showWhen: ['search'],
    },
    {
      key: 'note_urls',
      label: '视频URL/ID列表',
      type: 'textarea',
      placeholder: '每行一个，支持多种格式:\n完整URL: https://www.douyin.com/video/xxx\n短链接: https://v.douyin.com/xxx/\n纯ID: 7280854932641664319',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '创作者URL/ID列表',
      type: 'textarea',
      placeholder: '每行一个，支持格式:\n完整URL: https://www.douyin.com/user/xxx\nsec_user_id: MS4wLjABxxx',
      showWhen: ['creator'],
    },
  ],
  bili: [
    {
      key: 'bili_search_mode',
      label: '搜索模式',
      type: 'select',
      options: [
        { value: 'normal', label: '普通搜索' },
      ],
      defaultValue: 'normal',
      showWhen: ['search'],
    },
    {
      key: 'bili_qn',
      label: '视频清晰度',
      type: 'select',
      options: [
        { value: '16', label: '360P' },
        { value: '32', label: '480P' },
        { value: '64', label: '720P' },
        { value: '80', label: '1080P' },
        { value: '112', label: '1080P 高码率' },
        { value: '116', label: '1080P 60帧' },
      ],
      defaultValue: '80',
      showWhen: ['search', 'detail', 'creator'],
    },
    {
      key: 'note_urls',
      label: '视频URL/BV号列表',
      type: 'textarea',
      placeholder: '每行一个，支持格式:\n完整URL: https://www.bilibili.com/video/BVxxx\nBV号: BV1Sz4y1U77N',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '创作者URL/UID列表',
      type: 'textarea',
      placeholder: '每行一个，支持格式:\n完整URL: https://space.bilibili.com/434377496\nUID: 20813884',
      showWhen: ['creator'],
    },
  ],
  wb: [
    {
      key: 'weibo_search_type',
      label: '搜索类型',
      type: 'select',
      options: [
        { value: 'default', label: '综合' },
        { value: 'realtime', label: '实时' },
        { value: 'hot', label: '热门' },
      ],
      defaultValue: 'default',
      showWhen: ['search'],
    },
    {
      key: 'enable_full_text',
      label: '获取微博全文',
      type: 'switch',
      hint: '开启后会增加请求数量，被风控概率更高',
      defaultValue: true,
      showWhen: ['search'],
    },
    {
      key: 'note_urls',
      label: '微博ID列表',
      type: 'textarea',
      placeholder: '每行一个微博ID\n例如: 4982041758140155',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '用户ID列表',
      type: 'textarea',
      placeholder: '每行一个微博用户ID\n例如: 5756404150',
      showWhen: ['creator'],
    },
    {
      key: 'vip_creator_ids',
      label: 'VIP创作者ID列表',
      type: 'textarea',
      placeholder: '每行一个VIP创作者ID\n例如: 7948230240',
      showWhen: ['creator_vip'],
    },
  ],
  wechat: [
    {
      key: 'note_urls',
      label: '文章链接列表',
      type: 'textarea',
      placeholder: '每行一个文章链接\n例如: https://mp.weixin.qq.com/s/xxxxx',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '公众号 fakeid 列表',
      type: 'textarea',
      placeholder: '每行一个公众号 fakeid（__biz 参数）\n例如: MzAwNDk4NjkzNw==',
      hint: '从公众号主页URL中的 __biz 参数获取',
      showWhen: ['creator'],
    },
    {
      key: 'wechat_album_ids',
      label: '合集配置',
      type: 'textarea',
      placeholder: '每行一个，格式: 公众号biz:合集ID\n例如: MzAwNDk4NjkzNw==:1234567890',
      showWhen: ['album'],
    },
    {
      key: 'wechat_enable_content',
      label: '下载文章内容',
      type: 'switch',
      hint: '是否下载文章HTML全文内容',
      defaultValue: false,
    },
    {
      key: 'wechat_enable_reading_stats',
      label: '获取阅读统计',
      type: 'switch',
      hint: '需要微信凭证（uin, key, pass_ticket）',
      defaultValue: false,
    },
  ],
  ks: [
    {
      key: 'note_urls',
      label: '视频URL/ID列表',
      type: 'textarea',
      placeholder: '每行一个，支持格式:\n完整URL: https://www.kuaishou.com/short-video/xxx\n纯ID: 3xf8enb8dbj6uig',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '创作者URL/ID列表',
      type: 'textarea',
      placeholder: '每行一个，支持格式:\n完整URL: https://www.kuaishou.com/profile/xxx\n纯ID: 3x4sm73aye7jq7i',
      showWhen: ['creator'],
    },
  ],
  tieba: [
    {
      key: 'tieba_name_list',
      label: '贴吧名称列表',
      type: 'textarea',
      placeholder: '每行一个贴吧名称\n例如: 盗墓笔记',
      showWhen: ['search'],
    },
    {
      key: 'note_urls',
      label: '帖子ID列表',
      type: 'textarea',
      placeholder: '每行一个帖子ID',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '用户主页URL列表',
      type: 'textarea',
      placeholder: '每行一个用户主页URL\n例如: https://tieba.baidu.com/home/main/?id=tb.1.xxx',
      showWhen: ['creator'],
    },
  ],
  zhihu: [
    {
      key: 'note_urls',
      label: '内容URL列表',
      type: 'textarea',
      placeholder: '每行一个URL，支持回答/文章/视频:\nhttps://www.zhihu.com/question/xxx/answer/xxx\nhttps://zhuanlan.zhihu.com/p/xxx\nhttps://www.zhihu.com/zvideo/xxx',
      showWhen: ['detail'],
    },
    {
      key: 'creator_ids',
      label: '用户主页URL列表',
      type: 'textarea',
      placeholder: '每行一个用户主页URL\n例如: https://www.zhihu.com/people/xxx',
      showWhen: ['creator'],
    },
  ],
};

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
export const ACCOUNT_STATUS_CONFIG: Record<string, { label: string; bgColor: string; textColor: string }> = {
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
  expired: {
    label: '已过期',
    bgColor: 'bg-slate-100',
    textColor: 'text-slate-500',
  },
  banned: {
    label: '已封禁',
    bgColor: 'bg-red-100',
    textColor: 'text-red-600',
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
