/**
 * 任务管理 Hooks
 */
import { useCallback } from 'react'
import { useApi, useMutation } from './useApi'
import { tasksApi } from '../api/tasks'
import type {
  Task,
  TaskCreateRequest,
  TaskListResponse,
  TaskStats,
  LogEntry,
  TaskStatus,
  Platform,
} from '../types/task'

/**
 * 获取任务列表
 */
export function useTasks(params?: {
  status?: TaskStatus
  platform?: Platform
  page?: number
  page_size?: number
}) {
  const fetcher = useCallback(
    () => tasksApi.list(params),
    [params?.status, params?.platform, params?.page, params?.page_size]
  )
  return useApi<TaskListResponse>(fetcher, [
    params?.status,
    params?.platform,
    params?.page,
    params?.page_size,
  ])
}

/**
 * 获取单个任务
 */
export function useTask(taskId: string) {
  const fetcher = useCallback(() => tasksApi.get(taskId), [taskId])
  return useApi<Task>(fetcher, [taskId])
}

/**
 * 获取任务统计
 */
export function useTaskStats() {
  const fetcher = useCallback(() => tasksApi.getStats(), [])
  return useApi<TaskStats>(fetcher, [])
}

/**
 * 获取任务日志
 */
export function useTaskLogs(
  taskId: string,
  params?: { limit?: number; offset?: number; level?: string }
) {
  const fetcher = useCallback(
    () => tasksApi.getLogs(taskId, params),
    [taskId, params?.limit, params?.offset, params?.level]
  )
  return useApi<LogEntry[]>(fetcher, [taskId, params?.limit, params?.offset, params?.level])
}

/**
 * 创建任务
 */
export function useCreateTask() {
  return useMutation<Task, TaskCreateRequest>(tasksApi.create)
}

/**
 * 启动任务
 */
export function useStartTask() {
  return useMutation<Task, string>(tasksApi.start)
}

/**
 * 取消任务
 */
export function useCancelTask() {
  return useMutation<{ message: string }, string>(tasksApi.cancel)
}

/**
 * 重试任务
 */
export function useRetryTask() {
  return useMutation<Task, string>(tasksApi.retry)
}

/**
 * 删除任务
 */
export function useDeleteTask() {
  return useMutation<{ message: string }, string>(tasksApi.delete)
}

/**
 * 更新任务优先级
 */
export function useUpdateTaskPriority() {
  const mutator = useCallback(
    (params: { taskId: string; priority: number }) =>
      tasksApi.updatePriority(params.taskId, params.priority),
    []
  )
  return useMutation<{ message: string }, { taskId: string; priority: number }>(mutator)
}
