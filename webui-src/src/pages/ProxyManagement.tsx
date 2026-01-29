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
} from 'lucide-react';
import { PageHeader } from '../components/layout';
import { ProxyTable, AddProxyModal } from '../components/proxy';
import { useMockData } from '../mock/api';
import { Proxy } from '../types';

export function ProxyManagement() {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editProxy, setEditProxy] = useState<Proxy | null>(null);
  const { proxyStats, proxies } = useMockData();

  const handleAddProxy = (proxyData: Omit<Proxy, 'id' | 'status' | 'createdAt'>) => {
    console.log('Add proxy:', proxyData);
    // 实际实现时调用 API
  };

  const handleEditProxy = (proxy: Proxy) => {
    setEditProxy(proxy);
    setAddModalOpen(true);
  };

  const handleDeleteProxy = (proxy: Proxy) => {
    console.log('Delete proxy:', proxy);
    // 实际实现时调用 API
  };

  const handleTestProxy = (proxy: Proxy) => {
    console.log('Test proxy:', proxy);
    // 实际实现时调用 API
  };

  const handleRefresh = () => {
    console.log('Refresh proxy list');
    // 实际实现时刷新数据
  };

  const handleImport = () => {
    console.log('Import proxies');
    // 实际实现时打开导入弹窗
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
              <RefreshCw className="w-5 h-5 text-text-secondary" />
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
              className="h-10 px-5 flex items-center gap-2 rounded-lg bg-primary text-sm font-medium text-white hover:bg-primary/90 transition-colors"
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
              {proxyStats.total}
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-xs text-emerald-500 font-medium">
                +{proxyStats.weeklyChange.total} 本周新增
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
              {proxyStats.online}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-emerald-500 font-medium">
                {((proxyStats.online / proxyStats.total) * 100).toFixed(1)}% 在线率
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
              {proxyStats.offline}
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingDown className="w-3.5 h-3.5 text-red-500" />
              <span className="text-xs text-red-500 font-medium">
                {proxyStats.weeklyChange.offline} 本周减少
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
              {proxyStats.avgResponseTime}ms
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-xs text-emerald-500 font-medium">
                {proxyStats.weeklyChange.responseTime}ms 比上周更快
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
