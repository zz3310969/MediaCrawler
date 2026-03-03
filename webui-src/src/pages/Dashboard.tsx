import { Link } from 'react-router-dom';
import { Plus, Search, Activity, CheckCircle, Database, Globe, Loader2 } from 'lucide-react';
import { PageHeader } from '../components/layout';
import { StatCard, Button } from '../components/common';
import { RecentTasks, PlatformSupport, SystemStatus } from '../components/dashboard';
import { useDashboardPolling, useTasks } from '../hooks';
import type { Task } from '../types/task';

export function Dashboard() {
  // 获取仪表盘数据（每30秒刷新）
  const { data: dashboardData, loading: dashboardLoading, error: dashboardError } = useDashboardPolling(30000);
  
  // 获取最近任务（用于展示）
  const { data: tasksData, loading: tasksLoading } = useTasks({ page: 1, page_size: 5 });

  // 加载状态
  if (dashboardLoading && !dashboardData) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载中...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (dashboardError && !dashboardData) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <p className="text-error">加载失败: {dashboardError.message}</p>
          <p className="text-text-secondary text-sm">请检查后端服务是否正常运行</p>
        </div>
      </div>
    );
  }

  const stats = dashboardData?.stats;
  const systemStatus = dashboardData?.system;
  const platformStats = dashboardData?.platform_stats;
  const recentTasks = (tasksData?.tasks || []) as Task[];

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* 页面头部 */}
        <PageHeader
          title="爬虫仪表盘"
          subtitle="监控和管理您的数据爬取任务"
          actions={
            <>
              <button className="w-10 h-10 flex items-center justify-center rounded-lg border border-border hover:bg-slate-50 transition-colors">
                <Search className="w-[18px] h-[18px] text-text-secondary" />
              </button>
              <Link to="/tasks/create">
                <Button>
                  <Plus className="w-[18px] h-[18px]" />
                  新建任务
                </Button>
              </Link>
            </>
          }
        />

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-5">
          <StatCard
            label="运行中"
            value={stats?.running_tasks ?? 0}
            change={{
              value: `${stats?.pending_tasks ?? 0} 等待中`,
              trend: 'up',
            }}
            icon={<Activity className="w-4 h-4 text-primary" />}
            iconBgColor="bg-primary-100"
          />
          <StatCard
            label="已完成"
            value={(stats?.completed_tasks ?? 0).toLocaleString()}
            change={{
              value: `${stats?.failed_tasks ?? 0} 失败`,
              trend: (stats?.failed_tasks ?? 0) > 0 ? 'down' : 'stable',
            }}
            icon={<CheckCircle className="w-4 h-4 text-success" />}
            iconBgColor="bg-success-100"
          />
          <StatCard
            label="采集数据"
            value={stats?.total_data ?? '0'}
            change={{
              value: `${(stats?.total_data_count ?? 0).toLocaleString()} 条`,
              trend: 'up',
            }}
            icon={<Database className="w-4 h-4 text-warning" />}
            iconBgColor="bg-warning-100"
          />
          <StatCard
            label="活跃代理"
            value={stats?.active_proxies ?? 0}
            change={{
              value: stats?.proxy_health ?? '0%',
              trend: 'stable',
            }}
            icon={<Globe className="w-4 h-4 text-purple-500" />}
            iconBgColor="bg-purple-100"
          />
        </div>

        {/* 内容区域 */}
        <div className="grid grid-cols-3 gap-6 flex-1">
          {/* 左侧 - 最近任务 */}
          <div className="col-span-2">
            {tasksLoading && recentTasks.length === 0 ? (
              <div className="bg-white rounded-lg border border-border p-8 flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              </div>
            ) : (
              <RecentTasks tasks={recentTasks} />
            )}
          </div>

          {/* 右侧 - 平台支持和系统状态 */}
          <div className="space-y-5">
            <PlatformSupport stats={platformStats} />
            {systemStatus && <SystemStatus status={systemStatus} />}
          </div>
        </div>
      </div>
    </div>
  );
}
