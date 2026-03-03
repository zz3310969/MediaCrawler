import { Play, Pause, RotateCcw, Trash2, AlertCircle, Clock } from 'lucide-react';
import { Badge, Progress } from '../common';
import type { Task } from '../../types/task';
import { TASK_STATUS_CONFIG, PLATFORMS } from '../../lib/constants';
import { formatRelativeTime } from '../../lib/utils';

interface TaskCardProps {
  task: Task;
  onAction?: (action: 'start' | 'pause' | 'restart' | 'delete', taskId: string) => void;
}

export function TaskCard({ task, onAction }: TaskCardProps) {
  const platform = PLATFORMS.find((p) => p.id === task.platform);
  const statusConfig = TASK_STATUS_CONFIG[task.status];
  const keywords = task.config?.keywords || [];

  return (
    <div className="bg-white rounded-lg border border-border p-5 space-y-4 hover:shadow-card-hover transition-shadow">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{platform?.icon}</span>
          <span className="text-sm text-text-secondary">{platform?.name}</span>
        </div>
        <Badge variant={statusConfig.color as any}>
          {statusConfig.label}
        </Badge>
      </div>

      {/* 标题 */}
      <h3 className="text-[15px] font-semibold text-text-primary line-clamp-1">
        {task.task_name || `任务 ${task.task_id.slice(0, 8)}`}
      </h3>

      {/* 关键词标签 */}
      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {keywords.slice(0, 3).map((keyword: string, index: number) => (
            <span
              key={index}
              className="px-2 py-1 text-xs bg-slate-100 text-text-secondary rounded"
            >
              {keyword}
            </span>
          ))}
          {keywords.length > 3 && (
            <span className="px-2 py-1 text-xs bg-slate-100 text-text-secondary rounded">
              +{keywords.length - 3}
            </span>
          )}
        </div>
      )}

      {/* 进度/状态内容 */}
      {task.status === 'running' && task.progress?.percentage !== undefined && (
        <div className="space-y-2">
          <Progress value={task.progress.percentage} showLabel />
          <div className="flex items-center gap-4 text-xs text-text-secondary">
            <span>已采集 {task.progress.items_crawled?.toLocaleString() || 0}</span>
          </div>
        </div>
      )}

      {task.status === 'completed' && (
        <div className="flex items-center gap-4 text-sm">
          <span className="text-text-secondary">采集完成</span>
          <span className="text-text-primary font-medium">
            {task.progress?.items_crawled?.toLocaleString() || 0} 条数据
          </span>
        </div>
      )}

      {task.status === 'failed' && task.error_message && (
        <div className="flex items-start gap-2 p-3 bg-error-50 rounded-lg">
          <AlertCircle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
          <span className="text-xs text-error">{task.error_message}</span>
        </div>
      )}

      {task.status === 'pending' && (
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Clock className="w-4 h-4" />
          <span>等待执行中...</span>
        </div>
      )}

      {/* 底部 */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <span className="text-xs text-text-secondary">
          {task.finished_at
            ? `完成于 ${formatRelativeTime(new Date(task.finished_at * 1000))}`
            : task.started_at
            ? `开始于 ${formatRelativeTime(new Date(task.started_at * 1000))}`
            : `创建于 ${formatRelativeTime(new Date(task.created_at * 1000))}`}
        </span>
        
        <div className="flex items-center gap-2">
          {task.status === 'running' && (
            <button
              onClick={() => onAction?.('pause', task.task_id)}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
            >
              <Pause className="w-4 h-4 text-text-secondary" />
            </button>
          )}
          {task.status === 'failed' && (
            <button
              onClick={() => onAction?.('restart', task.task_id)}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
            >
              <RotateCcw className="w-4 h-4 text-text-secondary" />
            </button>
          )}
          {task.status === 'pending' && (
            <button
              onClick={() => onAction?.('start', task.task_id)}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
            >
              <Play className="w-4 h-4 text-text-secondary" />
            </button>
          )}
          <button
            onClick={() => onAction?.('delete', task.task_id)}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-error-50 transition-colors"
          >
            <Trash2 className="w-4 h-4 text-text-secondary hover:text-error" />
          </button>
        </div>
      </div>
    </div>
  );
}
