// 常量定义

// WebSocket 配置
export const WEBSOCKET_CONFIG = {
  RECONNECT_INTERVAL: 3000, // 3秒
  HEARTBEAT_INTERVAL: 30000, // 30秒
} as const

// 查询配置
export const QUERY_CONFIG = {
  STATUS_REFETCH_INTERVAL: 1000, // 1秒
  RETRY_COUNT: 1,
} as const

// 日志配置
export const LOG_CONFIG = {
  MAX_LOGS: 500, // 最大日志条数
  AUTO_SCROLL: true,
} as const

// 数据文件配置
export const DATA_CONFIG = {
  MAX_FILENAME_LENGTH: 50,
  DEFAULT_PAGE_SIZE: 20,
} as const

