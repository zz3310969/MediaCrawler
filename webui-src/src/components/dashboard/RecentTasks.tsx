import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { Badge } from '../common';
import { TASK_STATUS_CONFIG, PLATFORMS } from '../../lib/constants';
import type { Task } from '../../types/task';

interface RecentTasksProps {
  tasks: Task[];
}

export function RecentTasks({ tasks }: RecentTasksProps) {
  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden h-full flex flex-col">
      {/* 头部 */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <h3 className="text-base font-semibold font-display text-text-primary">最近任务</h3>
        <Link
          to="/tasks"
          className="flex items-center gap-1 text-sm text-primary hover:underline"
        >
          查看全部
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      {/* 任务列表 */}
      <div className="flex-1 overflow-y-auto">
        {tasks.map((task) => {
          const platform = PLATFORMS.find((p) => p.id === task.platform);
          const statusConfig = TASK_STATUS_CONFIG[task.status];
          const keywords = task.config?.keywords || [];

          return (
            <div
              key={task.task_id}
              className="flex items-center gap-4 px-5 py-4 border-b border-border last:border-b-0 hover:bg-slate-50 transition-colors"
            >
              {/* 平台图标 */}
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-lg">
                {platform?.icon}
              </div>

              {/* 任务信息 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-text-primary truncate">
                    {task.task_name || `任务 ${task.task_id.slice(0, 8)}`}
                  </span>
                  <Badge variant={statusConfig.color as any}>
                    {statusConfig.label}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 text-xs text-text-secondary">
                  <span>{platform?.name}</span>
                  {keywords.length > 0 && (
                    <span className="truncate">关键词: {keywords.join(', ')}</span>
                  )}
                </div>
              </div>

              {/* 进度/数量 */}
              <div className="flex-shrink-0 text-right">
                {task.status === 'running' && task.progress?.percentage !== undefined ? (
                  <span className="text-sm font-medium text-primary">{task.progress.percentage}%</span>
                ) : (
                  <span className="text-sm font-medium text-text-primary">
                    {task.progress?.items_crawled?.toLocaleString() || 0}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
