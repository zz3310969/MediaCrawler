import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Loader2, AlertCircle, CheckCircle2,
  Clock, Play, RotateCcw, Wifi, WifiOff, Filter, Square,
} from 'lucide-react';
import { Badge, Progress, Button } from '../components/common';
import { useTask, useStartTask, useCancelTask, useRetryTask } from '../hooks';
import { useTaskEvents } from '../hooks/useTaskEvents';
import { TASK_STATUS_CONFIG, PLATFORMS } from '../lib/constants';
import { formatRelativeTime } from '../lib/utils';
import { toast } from '../components/ui/toast';
import type { TaskEvent } from '../types/task';

interface LogItem {
  timestamp: string;
  level: string;
  message: string;
}

const LOG_LEVEL_STYLES: Record<string, string> = {
  error: 'text-red-400',
  warn: 'text-yellow-400',
  warning: 'text-yellow-400',
  info: 'text-green-400',
  debug: 'text-gray-500',
};

const LOG_LEVEL_LABEL: Record<string, string> = {
  error: 'ERROR',
  warn: 'WARN',
  warning: 'WARN',
  info: 'INFO',
  debug: 'DEBUG',
};

function formatLogTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString('zh-CN', { hour12: false });
  } catch {
    return '';
  }
}

export function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const { data: task, loading: taskLoading, refetch: refetchTask } = useTask(taskId || '');

  const { mutate: startTask } = useStartTask();
  const { mutate: cancelTask } = useCancelTask();
  const { mutate: retryTask } = useRetryTask();

  const [logs, setLogs] = useState<LogItem[]>([]);
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  const logContainerRef = useRef<HTMLDivElement>(null);

  const isActive = task?.status === 'running' || task?.status === 'pending';

  const handleEvent = useCallback((event: TaskEvent) => {
    if (event.event_type === 'task.log') {
      const payload = event.payload as { level?: string; message?: string };
      setLogs((prev) => [
        ...prev,
        {
          timestamp: event.timestamp,
          level: payload.level || 'info',
          message: payload.message || '',
        },
      ]);
      return;
    }

    if (event.event_type === 'task.status') {
      refetchTask();
      return;
    }

    if (
      event.event_type === 'task.progress' ||
      event.event_type === 'task.completed' ||
      event.event_type === 'task.failed' ||
      event.event_type === 'task.cancelled' ||
      event.event_type === 'task.started'
    ) {
      refetchTask();
    }
  }, [refetchTask]);

  const { connected } = useTaskEvents({
    taskId: taskId || undefined,
    enabled: !!taskId,
    onEvent: handleEvent,
  });

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    const el = logContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(atBottom);
  };

  const scrollToBottom = () => {
    setAutoScroll(true);
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  };

  const filteredLogs = useMemo(() => {
    if (levelFilter === 'all') return logs;
    return logs.filter((l) => {
      if (levelFilter === 'warn') return l.level === 'warn' || l.level === 'warning';
      return l.level === levelFilter;
    });
  }, [logs, levelFilter]);

  useEffect(() => {
    if (task && task.status !== 'running') {
      setCancelling(false);
    }
  }, [task?.status]);

  const handleAction = async (action: string) => {
    if (!taskId) return;
    try {
      if (action === 'start') {
        await startTask(taskId);
        toast.success('任务已启动');
      }
      if (action === 'pause') {
        setCancelling(true);
        await cancelTask(taskId);
        toast.info('正在停止任务，请稍候...');
      }
      if (action === 'restart') {
        await retryTask(taskId);
        toast.success('任务已重新提交');
      }
      refetchTask();
    } catch (err: any) {
      setCancelling(false);
      toast.error(err?.message || '操作失败');
    }
  };

  if (taskLoading && !task) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载任务信息...</p>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <AlertCircle className="w-8 h-8 text-error" />
          <p className="text-text-secondary">任务不存在</p>
          <Link to="/tasks">
            <Button variant="secondary">返回任务列表</Button>
          </Link>
        </div>
      </div>
    );
  }

  const platform = PLATFORMS.find((p) => p.id === task.platform);
  const statusConfig = TASK_STATUS_CONFIG[task.status];

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/tasks')}
              className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-text-secondary" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-text-primary">
                {task.task_name || `任务 ${task.task_id.slice(0, 8)}`}
              </h1>
              <p className="text-sm text-text-secondary mt-0.5">
                {task.task_id}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {task.status === 'pending' && (
              <Button onClick={() => handleAction('start')} className="gap-1.5">
                <Play className="w-4 h-4" /> 启动
              </Button>
            )}
            {task.status === 'running' && (
              <Button
                variant="secondary"
                onClick={() => handleAction('pause')}
                disabled={cancelling}
                className="gap-1.5"
              >
                {cancelling ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> 正在停止...
                  </>
                ) : (
                  <>
                    <Square className="w-4 h-4" /> 停止
                  </>
                )}
              </Button>
            )}
            {task.status === 'failed' && (
              <Button onClick={() => handleAction('restart')} className="gap-1.5">
                <RotateCcw className="w-4 h-4" /> 重试
              </Button>
            )}
            <Badge variant={statusConfig.color as any}>
              {statusConfig.label}
            </Badge>
          </div>
        </div>

        {/* Info cards */}
        <div className="grid grid-cols-4 gap-4">
          <InfoCard label="平台" value={
            <span className="flex items-center gap-1.5">
              <span>{platform?.icon}</span>
              <span>{platform?.name || task.platform}</span>
            </span>
          } />
          <InfoCard label="创建时间" value={formatRelativeTime(new Date(task.created_at))} />
          <InfoCard label="开始时间" value={task.started_at ? formatRelativeTime(new Date(task.started_at)) : '-'} />
          <InfoCard label="完成时间" value={task.finished_at ? formatRelativeTime(new Date(task.finished_at)) : '-'} />
        </div>

        {/* Progress */}
        {task.status === 'running' && task.progress && (
          <div className="bg-slate-50 rounded-lg border border-border p-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-secondary">采集进度</span>
              <span className="text-text-primary font-medium">
                已采集 {task.progress.items_crawled?.toLocaleString() || 0} 条
              </span>
            </div>
            <Progress value={task.progress.percentage ?? 0} showLabel />
          </div>
        )}

        {task.status === 'completed' && task.progress && (
          <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg p-4">
            <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
            <span className="text-sm text-green-700">
              任务完成，共采集 {task.progress.items_crawled?.toLocaleString() || 0} 条数据
            </span>
          </div>
        )}

        {task.status === 'failed' && task.error_message && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg p-4">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-red-700">{task.error_message}</span>
          </div>
        )}

        {/* Log panel */}
        <div className="bg-gray-900 rounded-lg border border-gray-700 flex flex-col relative" style={{ height: '480px' }}>
          {/* Log toolbar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-700">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-300">执行日志</span>
              <span className="text-xs text-gray-500">{filteredLogs.length} 条</span>
            </div>
            <div className="flex items-center gap-3">
              {/* Level filter */}
              <div className="flex items-center gap-1">
                <Filter className="w-3.5 h-3.5 text-gray-500" />
                {['all', 'info', 'warn', 'error'].map((level) => (
                  <button
                    key={level}
                    onClick={() => setLevelFilter(level)}
                    className={`px-2 py-0.5 text-xs rounded transition-colors ${
                      levelFilter === level
                        ? 'bg-gray-700 text-gray-200'
                        : 'text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {level === 'all' ? '全部' : level.toUpperCase()}
                  </button>
                ))}
              </div>
              {/* Connection status */}
              <div className="flex items-center gap-1.5" title={connected ? 'WebSocket 已连接' : 'WebSocket 未连接'}>
                {connected ? (
                  <Wifi className="w-3.5 h-3.5 text-green-500" />
                ) : (
                  <WifiOff className="w-3.5 h-3.5 text-gray-600" />
                )}
                <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-600'}`} />
              </div>
            </div>
          </div>

          {/* Log content */}
          <div
            ref={logContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-4 font-mono text-[13px] leading-5 select-text"
          >
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-600">
                {isActive ? (
                  <span className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    等待日志输出...
                  </span>
                ) : (
                  <span>暂无日志</span>
                )}
              </div>
            ) : (
              filteredLogs.map((log, i) => {
                const levelStyle = LOG_LEVEL_STYLES[log.level] || 'text-gray-400';
                const levelLabel = LOG_LEVEL_LABEL[log.level] || log.level.toUpperCase();
                return (
                  <div key={i} className="flex gap-2 hover:bg-gray-800/50 rounded px-1 -mx-1">
                    <span className="text-gray-600 flex-shrink-0 select-none">
                      {formatLogTime(log.timestamp)}
                    </span>
                    <span className={`flex-shrink-0 w-12 text-right select-none ${levelStyle}`}>
                      {levelLabel}
                    </span>
                    <span className="text-gray-200 break-all">{log.message}</span>
                  </div>
                );
              })
            )}
          </div>

          {/* Scroll-to-bottom button */}
          {!autoScroll && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-20 right-12 px-3 py-1.5 bg-gray-700 text-gray-300 text-xs rounded-lg hover:bg-gray-600 shadow-lg transition-colors"
            >
              滚动到底部
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-slate-50 rounded-lg border border-border px-4 py-3">
      <p className="text-xs text-text-secondary mb-1">{label}</p>
      <div className="text-sm font-medium text-text-primary">{value}</div>
    </div>
  );
}
