import { useState, useMemo } from 'react';
import { Search, Download, RefreshCw, FileText, Loader2 } from 'lucide-react';
import { PageHeader } from '../components/layout';
import { Button, PlatformTabs } from '../components/common';
import { Platform } from '../types';
import { useDataFiles, useDataStats } from '../hooks';
import { getDownloadUrl } from '../api/data';

// 格式化文件大小
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化时间
function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function DataManagement() {
  const [activePlatform, setActivePlatform] = useState<Platform | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // 获取数据文件列表
  const { data: filesData, loading: filesLoading, refetch: refetchFiles } = useDataFiles({
    platform: activePlatform === 'all' ? undefined : activePlatform,
  });
  
  // 获取数据统计
  const { data: statsData, loading: statsLoading } = useDataStats();

  const files = filesData?.files || [];
  const stats = statsData || { total_files: 0, total_size: 0, by_platform: {}, by_type: {} };

  // 筛选文件
  const filteredFiles = useMemo(() => {
    if (!searchQuery) return files;
    const query = searchQuery.toLowerCase();
    return files.filter(file => file.name.toLowerCase().includes(query));
  }, [files, searchQuery]);

  // 计算平台统计用于 tabs
  const platformCounts = useMemo(() => {
    const counts: Record<string, number> = { all: stats.total_files };
    Object.entries(stats.by_platform).forEach(([platform, count]) => {
      counts[platform] = count;
    });
    return counts;
  }, [stats]);

  // 处理下载
  const handleDownload = (filePath: string) => {
    window.open(getDownloadUrl(filePath), '_blank');
  };

  // 加载状态
  if (filesLoading && files.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载数据文件...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* 页面头部 */}
        <PageHeader
          title="数据管理"
          subtitle="管理各平台采集的数据文件"
          actions={
            <Button variant="secondary" onClick={() => refetchFiles()}>
              <RefreshCw className={`w-4 h-4 ${filesLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          }
        />

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-50 rounded-lg p-4">
            <div className="text-sm text-text-secondary mb-1">总文件数</div>
            <div className="text-2xl font-semibold text-text-primary">
              {statsLoading ? '-' : stats.total_files}
            </div>
          </div>
          <div className="bg-slate-50 rounded-lg p-4">
            <div className="text-sm text-text-secondary mb-1">总大小</div>
            <div className="text-2xl font-semibold text-text-primary">
              {statsLoading ? '-' : formatFileSize(stats.total_size)}
            </div>
          </div>
          <div className="bg-slate-50 rounded-lg p-4">
            <div className="text-sm text-text-secondary mb-1">JSON 文件</div>
            <div className="text-2xl font-semibold text-text-primary">
              {statsLoading ? '-' : (stats.by_type.json || 0)}
            </div>
          </div>
          <div className="bg-slate-50 rounded-lg p-4">
            <div className="text-sm text-text-secondary mb-1">CSV 文件</div>
            <div className="text-2xl font-semibold text-text-primary">
              {statsLoading ? '-' : (stats.by_type.csv || 0)}
            </div>
          </div>
        </div>

        {/* 平台标签 */}
        <div className="border-b border-border pb-4">
          <PlatformTabs
            value={activePlatform}
            onChange={(value) => setActivePlatform(value as Platform)}
            showAll
            counts={platformCounts}
          />
        </div>

        {/* 搜索和筛选 */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-[300px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="搜索文件名..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 rounded-lg bg-slate-50 border border-slate-200 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1.5 text-sm">
              <span className="text-text-secondary">共</span>
              <span className="text-primary font-semibold">{filteredFiles.length}</span>
              <span className="text-text-secondary">个文件</span>
            </div>
          </div>
        </div>

        {/* 文件列表 */}
        <div className="flex-1">
          {filteredFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center bg-slate-50 rounded-lg">
              <FileText className="w-12 h-12 text-slate-300 mb-4" />
              <p className="text-text-secondary">暂无数据文件</p>
              <p className="text-sm text-slate-400 mt-1">
                运行爬虫任务后，数据将显示在这里
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-border overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50 border-b border-border">
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">文件名</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">类型</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">记录数</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">大小</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">修改时间</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFiles.map((file) => (
                    <tr key={file.path} className="border-b border-border last:border-0 hover:bg-slate-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-slate-400" />
                          <span className="text-sm text-text-primary font-medium">{file.name}</span>
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">{file.path}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          file.type === 'json' ? 'bg-blue-100 text-blue-700' :
                          file.type === 'csv' ? 'bg-green-100 text-green-700' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {file.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {file.record_count !== null ? file.record_count.toLocaleString() : '-'}
                      </td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {formatFileSize(file.size)}
                      </td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {formatTime(file.modified_at)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleDownload(file.path)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-primary hover:bg-primary/10 rounded transition-colors"
                        >
                          <Download className="w-4 h-4" />
                          下载
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
