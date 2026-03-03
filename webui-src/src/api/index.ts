/**
 * API 服务统一导出
 */

// 基础客户端
export { client } from './client'

// Session 管理
export {
  getStoredSessionId,
  setStoredSessionId,
  clearStoredSessionId,
  isLoggedIn,
  redirectToLogin,
  getRedirectPath,
  LOGIN_PATH,
} from './session'

// 任务 API
export { tasksApi, createSession, logout, getCurrentUser, refreshSession } from './tasks'

// 仪表盘 API
export {
  getDashboard,
  getTaskStats,
  getProxyStats as getDashboardProxyStats,
  getAccountStats as getDashboardAccountStats,
  getSystemStatus,
  getPlatformStats,
  getOverview,
  type DashboardResponse,
} from './dashboard'

// 账号 API
export {
  getAccounts,
  getAccount,
  createAccount,
  updateAccount,
  deleteAccount,
  validateAccount,
  batchDeleteAccounts,
  getAccountStats,
  getActiveAccountsByPlatform,
} from './accounts'

// 代理 API
export {
  getProxies,
  getProxy,
  createProxy,
  updateProxy,
  deleteProxy as deleteProxyApi,
  importProxies,
  testProxy,
  batchTestProxies,
  batchDeleteProxies,
  getProxyStats,
} from './proxies'

// 数据管理 API
export {
  getDataFiles,
  getFileContent,
  getDownloadUrl,
  getDataStats,
} from './data'

// 系统配置 API
export { configApi } from './config'
export type { ConfigType, ConfigDict, ConfigItem, ConfigListResponse } from './config'
