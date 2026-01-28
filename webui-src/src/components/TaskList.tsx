/**
 * 任务列表组件
 */
import React, { useState, useEffect, useCallback } from 'react';
import { tasksApi } from '../api/tasks';
import { 
  Task, 
  TaskStatus, 
  Platform,
  TaskStatusConfig,
  PlatformConfig 
} from '../types/task';
import { Button } from './ui/button';
import { Select } from './ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Badge } from './ui/badge';

interface TaskListProps {
  onTaskSelect?: (task: Task) => void;
  onCreateTask?: () => void;
}

export const TaskList: React.FC<TaskListProps> = ({ onTaskSelect, onCreateTask }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  
  // 筛选
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [platformFilter, setPlatformFilter] = useState<Platform | 'all'>('all');

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await tasksApi.list({
        status: statusFilter === 'all' ? undefined : statusFilter,
        platform: platformFilter === 'all' ? undefined : platformFilter,
        page,
        page_size: 20,
      });
      setTasks(res.tasks);
      setTotal(res.total);
    } catch (e) {
      console.error('Failed to load tasks:', e);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, platformFilter]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // 定时刷新运行中的任务
  useEffect(() => {
    const hasRunning = tasks.some(t => t.status === 'running');
    if (!hasRunning) return;

    const interval = setInterval(loadTasks, 5000);
    return () => clearInterval(interval);
  }, [tasks, loadTasks]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-4">
      {/* 头部 */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">任务列表</h2>
        {onCreateTask && (
          <Button onClick={onCreateTask}>
            + 创建任务
          </Button>
        )}
      </div>

      {/* 筛选器 */}
      <div className="flex gap-4">
        <div className="w-[140px]">
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as TaskStatus | 'all');
              setPage(1);
            }}
          >
            <option value="all">全部状态</option>
            <option value="pending">等待中</option>
            <option value="running">运行中</option>
            <option value="completed">已完成</option>
            <option value="failed">已失败</option>
            <option value="cancelled">已取消</option>
          </Select>
        </div>
        
        <div className="w-[140px]">
          <Select
            value={platformFilter}
            onChange={(e) => {
              setPlatformFilter(e.target.value as Platform | 'all');
              setPage(1);
            }}
          >
            <option value="all">全部平台</option>
            <option value="xhs">小红书</option>
            <option value="dy">抖音</option>
            <option value="bili">B站</option>
            <option value="wb">微博</option>
            <option value="wechat">微信</option>
          </Select>
        </div>

        <Button variant="outline" onClick={loadTasks} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </Button>
      </div>

      {/* 任务表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>任务名称</TableHead>
              <TableHead>平台</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>进度</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  {loading ? '加载中...' : '暂无任务'}
                </TableCell>
              </TableRow>
            ) : (
              tasks.map((task) => {
                const statusConfig = TaskStatusConfig[task.status];
                const platformInfo = PlatformConfig[task.config.platform];
                
                return (
                  <TableRow
                    key={task.task_id}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => onTaskSelect?.(task)}
                  >
                    <TableCell className="font-medium">
                      {task.task_name || task.task_id.slice(0, 8)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {platformInfo?.label || task.config.platform.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={`${statusConfig.bgColor} ${statusConfig.color}`}>
                        {statusConfig.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 rounded-full h-2 transition-all"
                            style={{ width: `${task.progress.percentage}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-500">
                          {task.progress.percentage}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-500">
                      {formatDate(task.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onTaskSelect?.(task);
                        }}
                      >
                        详情
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {total > 0 && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-500">
            共 {total} 条
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              上一页
            </Button>
            <span className="px-3 py-1 text-sm">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskList;
