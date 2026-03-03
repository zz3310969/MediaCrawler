import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Plus, SlidersHorizontal, Loader2 } from 'lucide-react';
import { PageHeader } from '../components/layout';
import { Button } from '../components/common';
import { TaskCard, TaskTabs } from '../components/tasks';
import type { TaskStatus, Task } from '../types/task';
import { useTasks, useStartTask, useCancelTask, useRetryTask, useDeleteTask } from '../hooks';

export function Tasks() {
  const [activeTab, setActiveTab] = useState<TaskStatus | 'all'>('all');
  
  // 获取任务列表
  const { data: tasksData, loading, error, refetch } = useTasks({
    status: activeTab === 'all' ? undefined : activeTab,
    page: 1,
    page_size: 50,
  });

  // 任务操作
  const { mutate: startTask } = useStartTask();
  const { mutate: cancelTask } = useCancelTask();
  const { mutate: retryTask } = useRetryTask();
  const { mutate: deleteTask } = useDeleteTask();

  const tasks = (tasksData?.tasks || []) as Task[];

  // 计算各状态数量
  const counts = useMemo(() => ({
    all: tasksData?.total || 0,
    running: tasks.filter((t) => t.status === 'running').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
    pending: tasks.filter((t) => t.status === 'pending').length,
    cancelled: tasks.filter((t) => t.status === 'cancelled').length,
  }), [tasks, tasksData?.total]);

  const handleTaskAction = async (action: 'start' | 'pause' | 'restart' | 'delete', taskId: string) => {
    try {
      switch (action) {
        case 'start':
          await startTask(taskId);
          break;
        case 'pause':
          await cancelTask(taskId);
          break;
        case 'restart':
          await retryTask(taskId);
          break;
        case 'delete':
          if (window.confirm('确定要删除这个任务吗？')) {
            await deleteTask(taskId);
          } else {
            return;
          }
          break;
      }
      refetch();
    } catch (err: any) {
      const message = err?.message || '操作失败';
      alert(message);
    }
  };

  // 加载状态
  if (loading && tasks.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载任务列表...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error && tasks.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <p className="text-error">加载失败: {error.message}</p>
          <Button onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* 页面头部 */}
        <PageHeader
          title="任务管理"
          subtitle="管理和监控所有爬取任务"
          actions={
            <>
              <Button variant="secondary">
                <SlidersHorizontal className="w-4 h-4" />
                筛选
              </Button>
              <Link to="/tasks/create">
                <Button>
                  <Plus className="w-[18px] h-[18px]" />
                  新建任务
                </Button>
              </Link>
            </>
          }
        />

        {/* 标签页 */}
        <TaskTabs
          activeTab={activeTab}
          onChange={setActiveTab}
          counts={counts}
        />

        {/* 任务网格 */}
        <div className="grid grid-cols-3 gap-5">
          {tasks.map((task) => (
            <TaskCard
              key={task.task_id}
              task={task}
              onAction={handleTaskAction}
            />
          ))}
        </div>

        {/* 空状态 */}
        {tasks.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-text-secondary mb-4">暂无任务</p>
            <Link to="/tasks/create">
              <Button>
                <Plus className="w-4 h-4" />
                新建任务
              </Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
