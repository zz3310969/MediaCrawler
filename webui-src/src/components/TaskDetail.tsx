/**
 * 任务详情组件
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { tasksApi } from '../api/tasks';
import { useTaskEvents } from '../hooks/useTaskEvents';
import { 
  Task, 
  LogEntry, 
  TaskEvent, 
  TaskStatusConfig,
  PlatformConfig 
} from '../types/task';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { ScrollArea } from './ui/scroll-area';

interface TaskDetailProps {
  taskId: string;
  sessionId: string;
  onBack?: () => void;
}

export const TaskDetail: React.FC<TaskDetailProps> = ({
  taskId,
  sessionId,
  onBack,
}) => {
  const [task, setTask] = useState<Task | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // 加载任务详情
  const loadTask = useCallback(async () => {
    try {
      const data = await tasksApi.get(taskId);
      setTask(data);
    } catch (e) {
      console.error('Failed to load task:', e);
    }
  }, [taskId]);

  // 加载历史日志
  const loadLogs = useCallback(async () => {
    try {
      const data = await tasksApi.getLogs(taskId, { limit: 100 });
      setLogs(data);
    } catch (e) {
      console.error('Failed to load logs:', e);
    }
  }, [taskId]);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadTask(), loadLogs()]).finally(() => setLoading(false));
  }, [loadTask, loadLogs]);

  // WebSocket 订阅实时更新
  const { connected } = useTaskEvents({
    taskId,
    enabled: task?.status === 'running',
    onEvent: (event: TaskEvent) => {
      if (event.event_type === 'task.progress') {
        setTask((prev) =>
          prev ? { 
            ...prev, 
            progress: {
              ...prev.progress,
              ...(event.payload as Record<string, number>)
            }
          } : null
        );
      } else if (event.event_type === 'task.log') {
        const payload = event.payload as { level: string; message: string };
        setLogs((prev) => [
          ...prev,
          {
            log_id: event.event_id,
            task_id: taskId,
            timestamp: event.timestamp,
            level: payload.level as LogEntry['level'],
            message: payload.message,
          },
        ]);
      } else if (
        ['task.completed', 'task.failed', 'task.cancelled'].includes(event.event_type)
      ) {
        loadTask(); // 刷新任务状态
      }
    },
  });

  // 自动滚动到底部
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleCancel = async () => {
    if (!confirm('确定要取消此任务吗？')) return;
    
    try {
      await tasksApi.cancel(taskId);
      await loadTask();
    } catch (e) {
      console.error('Failed to cancel task:', e);
    }
  };

  const handleRetry = async () => {
    try {
      const newTask = await tasksApi.retry(taskId);
      // 可以跳转到新任务
      alert(`已创建重试任务: ${newTask.task_id.slice(0, 8)}`);
    } catch (e) {
      console.error('Failed to retry task:', e);
    }
  };

  const handleDelete = async () => {
    if (!confirm('确定要删除此任务吗？')) return;
    
    try {
      await tasksApi.delete(taskId);
      onBack?.();
    } catch (e) {
      console.error('Failed to delete task:', e);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'error': return 'text-red-400';
      case 'warn': return 'text-yellow-400';
      case 'debug': return 'text-gray-400';
      default: return 'text-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-gray-500">加载中...</span>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-gray-500">任务不存在</span>
      </div>
    );
  }

  const statusConfig = TaskStatusConfig[task.status];
  const platformInfo = PlatformConfig[task.config.platform];

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex justify-between items-center">
        <Button variant="ghost" onClick={onBack}>
          ← 返回
        </Button>
        <div className="flex gap-2">
          {task.status === 'running' && (
            <Button variant="destructive" onClick={handleCancel}>
              取消任务
            </Button>
          )}
          {['failed', 'cancelled'].includes(task.status) && (
            <Button onClick={handleRetry}>
              重试
            </Button>
          )}
          {['completed', 'failed', 'cancelled'].includes(task.status) && (
            <Button variant="outline" onClick={handleDelete}>
              删除
            </Button>
          )}
        </div>
      </div>

      {/* 基本信息 */}
      <Card>
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-500">任务ID</label>
              <p className="font-mono text-sm">{task.task_id}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">任务名称</label>
              <p>{task.task_name || '-'}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">平台</label>
              <p>
                <Badge variant="outline">
                  {platformInfo?.label || task.config.platform.toUpperCase()}
                </Badge>
              </p>
            </div>
            <div>
              <label className="text-sm text-gray-500">状态</label>
              <p>
                <Badge className={`${statusConfig.bgColor} ${statusConfig.color}`}>
                  {statusConfig.label}
                </Badge>
                {connected && task.status === 'running' && (
                  <span className="ml-2 text-green-500 text-xs">● 实时更新中</span>
                )}
              </p>
            </div>
            <div>
              <label className="text-sm text-gray-500">创建时间</label>
              <p>{formatDate(task.created_at)}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">开始时间</label>
              <p>{formatDate(task.started_at)}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">完成时间</label>
              <p>{formatDate(task.finished_at)}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500">优先级</label>
              <p>{task.priority}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 执行进度 */}
      <Card>
        <CardHeader>
          <CardTitle>执行进度</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-blue-500 rounded-full h-4 transition-all duration-300"
                style={{ width: `${task.progress.percentage}%` }}
              />
            </div>
            <div className="flex justify-between text-sm">
              <span>
                已爬取: {task.progress.items_crawled} / {task.progress.total}
              </span>
              <span>{task.progress.percentage}%</span>
            </div>
            {task.progress.comments_crawled > 0 && (
              <p className="text-sm text-gray-500">
                评论数: {task.progress.comments_crawled}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 实时日志 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>实时日志</CardTitle>
          <span className="text-sm text-gray-500">
            {logs.length} 条日志
          </span>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-64 bg-gray-900 rounded-lg p-4 font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-gray-500 text-center py-8">
                暂无日志
              </div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.log_id}
                  className={`${getLogColor(log.level)} mb-1`}
                >
                  <span className="text-gray-500">
                    [{new Date(log.timestamp).toLocaleTimeString()}]
                  </span>
                  {' '}
                  <span className="text-gray-400">
                    [{log.level.toUpperCase()}]
                  </span>
                  {' '}
                  {log.message}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </ScrollArea>
        </CardContent>
      </Card>

      {/* 任务结果 */}
      {task.result.success !== undefined && (
        <Card>
          <CardHeader>
            <CardTitle>任务结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p>
                <span className="text-gray-500">状态：</span>
                {task.result.success ? (
                  <span className="text-green-600">成功</span>
                ) : (
                  <span className="text-red-600">失败</span>
                )}
              </p>
              {task.result.error_message && (
                <p>
                  <span className="text-gray-500">错误信息：</span>
                  <span className="text-red-600">{task.result.error_message}</span>
                </p>
              )}
              {task.result.output_path && (
                <p>
                  <span className="text-gray-500">输出路径：</span>
                  <code className="bg-gray-100 px-2 py-1 rounded">
                    {task.result.output_path}
                  </code>
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TaskDetail;

