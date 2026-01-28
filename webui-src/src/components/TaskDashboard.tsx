/**
 * 任务仪表盘组件
 */
import React, { useState, useEffect, useCallback } from 'react';
import { tasksApi } from '../api/tasks';
import { 
  Task, 
  TaskStats, 
  TaskStatusConfig,
  PlatformConfig 
} from '../types/task';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';

interface TaskDashboardProps {
  onTaskSelect?: (task: Task) => void;
  onCreateTask?: () => void;
}

export const TaskDashboard: React.FC<TaskDashboardProps> = ({
  onTaskSelect,
  onCreateTask,
}) => {
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [runningTasks, setRunningTasks] = useState<Task[]>([]);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [statsData, runningData, recentData] = await Promise.all([
        tasksApi.getStats(),
        tasksApi.list({ status: 'running', page_size: 10 }),
        tasksApi.list({ page_size: 5 }),
      ]);

      setStats(statsData);
      setRunningTasks(runningData.tasks);
      setRecentTasks(recentData.tasks.filter(t => t.status !== 'running').slice(0, 5));
    } catch (e) {
      console.error('Failed to load dashboard data:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 定时刷新
  useEffect(() => {
    if (runningTasks.length === 0) return;

    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [runningTasks.length, loadData]);

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return `${diff}秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-gray-500">加载中...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold">任务仪表盘</h2>
        {onCreateTask && (
          <Button onClick={onCreateTask}>
            + 创建任务
          </Button>
        )}
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-5 gap-4">
          {Object.entries(TaskStatusConfig).map(([status, config]) => (
            <Card key={status}>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-3xl font-bold">
                    {stats[status as keyof TaskStats]}
                  </p>
                  <p className={`text-sm ${config.color}`}>
                    {config.label}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 运行中的任务 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            运行中的任务
            {runningTasks.length > 0 && (
              <Badge variant="secondary">{runningTasks.length}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {runningTasks.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              当前没有运行中的任务
            </div>
          ) : (
            <div className="space-y-4">
              {runningTasks.map((task) => {
                const platformInfo = PlatformConfig[task.config.platform];
                return (
                  <div
                    key={task.task_id}
                    className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => onTaskSelect?.(task)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          {platformInfo?.label || task.config.platform}
                        </Badge>
                        <span className="font-medium">
                          {task.task_name || task.task_id.slice(0, 8)}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {task.progress.percentage}%
                      </span>
                    </div>
                    <Progress value={task.progress.percentage} className="h-2" />
                    <div className="flex justify-between mt-2 text-sm text-gray-500">
                      <span>
                        已爬取 {task.progress.items_crawled}/{task.progress.total}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onTaskSelect?.(task);
                        }}
                      >
                        查看详情
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 最近完成的任务 */}
      <Card>
        <CardHeader>
          <CardTitle>最近任务</CardTitle>
        </CardHeader>
        <CardContent>
          {recentTasks.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              暂无任务记录
            </div>
          ) : (
            <div className="space-y-2">
              {recentTasks.map((task) => {
                const statusConfig = TaskStatusConfig[task.status];
                const platformInfo = PlatformConfig[task.config.platform];
                return (
                  <div
                    key={task.task_id}
                    className="flex items-center justify-between py-2 border-b last:border-0 cursor-pointer hover:bg-gray-50"
                    onClick={() => onTaskSelect?.(task)}
                  >
                    <div className="flex items-center gap-3">
                      <Badge className={`${statusConfig.bgColor} ${statusConfig.color}`}>
                        {statusConfig.label}
                      </Badge>
                      <Badge variant="outline">
                        {platformInfo?.label || task.config.platform}
                      </Badge>
                      <span>
                        {task.task_name || task.task_id.slice(0, 8)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span>
                        {task.progress.items_crawled}条
                      </span>
                      <span>
                        {formatTime(task.finished_at || task.created_at)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TaskDashboard;

