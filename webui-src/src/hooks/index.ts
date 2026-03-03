/**
 * Hooks 统一导出
 */

// 通用 API hooks
export { useApi, usePollingApi, useMutation } from './useApi'

// 仪表盘 hooks
export {
  useDashboard,
  useDashboardPolling,
  useTaskStats,
  useProxyStats as useDashboardProxyStats,
  useAccountStats as useDashboardAccountStats,
  useSystemStatus,
  usePlatformStats,
} from './useDashboard'

// 账号 hooks
export {
  useAccounts,
  useAccount,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  useValidateAccount,
  useBatchDeleteAccounts,
} from './useAccounts'

// 代理 hooks
export {
  useProxies,
  useProxy,
  useProxyStats,
  useCreateProxy,
  useUpdateProxy,
  useDeleteProxy,
  useTestProxy,
  useBatchTestProxies,
  useBatchDeleteProxies,
} from './useProxies'

// 任务 hooks
export {
  useTasks,
  useTask,
  useTaskStats as useTasksStats,
  useTaskLogs,
  useCreateTask,
  useCancelTask,
  useRetryTask,
  useDeleteTask,
  useUpdateTaskPriority,
} from './useTasks'

// 数据 hooks
export {
  useDataFiles,
  useFileContent,
  useDataStats,
} from './useData'
