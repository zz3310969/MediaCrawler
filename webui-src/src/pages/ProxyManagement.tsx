import { useState } from 'react';
import {
  RefreshCw,
  Upload,
  Plus,
  Server,
  Wifi,
  WifiOff,
  Timer,
  TrendingUp,
  TrendingDown,
  Loader2,
} from 'lucide-react';
import { ProxyTable, AddProxyModal } from '../components/proxy';
import { useProxies, useProxyStats, useCreateProxy, useDeleteProxy, useTestProxy } from '../hooks';
import { Proxy } from '../types';
import { toast } from '../components/ui/toast';
import { confirm } from '../components/ui/confirm';

export function ProxyManagement() {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editProxy, setEditProxy] = useState<Proxy | null>(null);

  // 获取代理列表和统计
  const { data: proxiesData, loading: proxiesLoading, refetch: refetchProxies } = useProxies({
    page: 1,
    page_size: 100,
  });
  const { data: proxyStats, loading: statsLoading, refetch: refetchStats } = useProxyStats();

  // 代理操作
  const { mutate: createProxy } = useCreateProxy();
  const { mutate: deleteProxy } = useDeleteProxy();
  const { mutate: testProxy } = useTestProxy();

  const proxies = proxiesData?.items || [];
  const loading = proxiesLoading || statsLoading;

  const handleAddProxy = async (proxyData: Partial<Proxy>) => {
    try {
      await createProxy(proxyData);
      setAddModalOpen(false);
      setEditProxy(null);
      refetchProxies();
      refetchStats();
    } catch (err) {
      console.error('Add proxy failed:', err);
    }
  };

  const handleEditProxy = (proxy: Proxy) => {
    setEditProxy(proxy);
    setAddModalOpen(true);
  };

  const handleDeleteProxy = async (proxy: Proxy) => {
    const ok = await confirm({
      title: '删除代理',
      message: `确定要删除代理 ${proxy.ip}:${proxy.port} 吗？`,
      confirmText: '删除',
      variant: 'danger',
    });
    if (!ok) return;
    try {
      await deleteProxy(proxy.proxy_id);
      refetchProxies();
      refetchStats();
    } catch (err) {
      console.error('Delete proxy failed:', err);
    }
  };

  const handleTestProxy = async (proxy: Proxy) => {
    try {
      const result = await testProxy(proxy.proxy_id);
      if (result.success) {
        toast.success(`测试成功！响应时间: ${result.response_time}ms`);
      } else {
        toast.error(`测试失败: ${result.error || '未知错误'}`);
      }
      refetchProxies();
    } catch (err) {
      console.error('Test proxy failed:', err);
    }
  };

  const handleRefresh = () => {
    refetchProxies();
    refetchStats();
  };

  const handleImport = () => {
    console.log('Import proxies');
    // TODO: 打开导入弹窗
  };

  // 加载状态
  if (loading && proxies.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载代理列表...</p>
        </div>
      </div>
    );
  }

  const stats = proxyStats || {
    total: 0,
    online: 0,
    offline: 0,
    testing: 0,
    banned: 0,
    avg_response_time: 0,
    avg_success_rate: 0,
  };

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* 页面头部 */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-[28px] font-semibold font-display text-text-primary">
              代理池配置
            </h1>
            <p className="text-sm text-text-secondary">
              管理和配置您的代理池，确保爬取任务稳定运行
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              className="w-10 h-10 flex items-center justify-center rounded-lg border border-border hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className={`w-5 h-5 text-text-secondary ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleImport}
              className="h-10 px-5 flex items-center gap-2 rounded-lg border border-border text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Upload className="w-[18px] h-[18px]" />
              导入代理
            </button>
            <button
              onClick={() => {
                setEditProxy(null);
                setAddModalOpen(true);
              }}
              className="h-10 px-5 flex items-center gap-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-[18px] h-[18px]" />
              添加代理
            </button>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-5">
          {/* 总代理数 */}
          <div className="bg-white rounded-xl border border-border p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-secondary">总代理数</span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                <Server className="w-4 h-4 text-primary" />
              </div>
            </div>
            <div className="font-display text-4xl font-semibold text-text-primary">
              {stats.total}
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-xs text-emerald-500 font-medium">
                {stats.avg_success_rate.toFixed(1)}% 平均成功率
              </span>
            </div>
          </div>

          {/* 在线代理 */}
          <div className="bg-white rounded-xl border border-border p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-secondary">在线代理</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <Wifi className="w-4 h-4 text-emerald-500" />
              </div>
            </div>
            <div className="font-display text-4xl font-semibold text-text-primary">
              {stats.online}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-emerald-500 font-medium">
                {stats.total > 0 ? ((stats.online / stats.total) * 100).toFixed(1) : 0}% 在线率
              </span>
            </div>
          </div>

          {/* 离线代理 */}
          <div className="bg-white rounded-xl border border-border p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-secondary">离线代理</span>
              <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
                <WifiOff className="w-4 h-4 text-red-500" />
              </div>
            </div>
            <div className="font-display text-4xl font-semibold text-text-primary">
              {stats.offline}
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingDown className="w-3.5 h-3.5 text-red-500" />
              <span className="text-xs text-red-500 font-medium">
                {stats.banned} 已封禁
              </span>
            </div>
          </div>

          {/* 平均响应 */}
          <div className="bg-white rounded-xl border border-border p-6 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-secondary">平均响应</span>
              <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
                <Timer className="w-4 h-4 text-amber-500" />
              </div>
            </div>
            <div className="font-display text-4xl font-semibold text-text-primary">
              {stats.avg_response_time}ms
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-xs text-emerald-500 font-medium">
                {stats.testing} 检测中
              </span>
            </div>
          </div>
        </div>

        {/* 代理列表 */}
        <div className="flex-1">
          <ProxyTable
            proxies={proxies}
            onEdit={handleEditProxy}
            onDelete={handleDeleteProxy}
            onTest={handleTestProxy}
          />
        </div>
      </div>

      {/* 添加/编辑代理弹窗 */}
      <AddProxyModal
        open={addModalOpen}
        onClose={() => {
          setAddModalOpen(false);
          setEditProxy(null);
        }}
        onSubmit={handleAddProxy}
        editProxy={editProxy}
      />
    </div>
  );
}
