import { useState, useMemo } from 'react';
import { Search, Download, RefreshCw, FileText, Database, Loader2, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { PageHeader } from '../components/layout';
import { Button, PlatformTabs } from '../components/common';
import { Platform } from '../types';
import { useDataFiles, useDataStats, useDbTables, useDbStats } from '../hooks';
import { getDownloadUrl, queryDbTable } from '../api/data';
import type { DbQueryResponse } from '../api/data';

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

const PLATFORM_LABELS: Record<string, string> = {
  xhs: '小红书', dy: '抖音', bili: 'B站', wb: '微博',
  tieba: '贴吧', zhihu: '知乎', ks: '快手', wechat: '微信公众号',
};

type ViewMode = 'files' | 'database';

export function DataManagement() {
  const [viewMode, setViewMode] = useState<ViewMode>('database');
  const [activePlatform, setActivePlatform] = useState<Platform | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 文件数据
  const { data: filesData, loading: filesLoading, refetch: refetchFiles } = useDataFiles({
    platform: activePlatform === 'all' ? undefined : activePlatform,
  });
  const { data: statsData, loading: statsLoading } = useDataStats();

  // 数据库数据
  const dbPlatform = activePlatform === 'all' ? undefined : activePlatform;
  const { data: dbTablesData, loading: dbTablesLoading, refetch: refetchDbTables } = useDbTables(dbPlatform);
  const { data: dbStatsData, loading: dbStatsLoading } = useDbStats();

  // 数据库表查询状态
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [dbPage, setDbPage] = useState(1);
  const [dbSearch, setDbSearch] = useState('');
  const [dbQueryResult, setDbQueryResult] = useState<DbQueryResponse | null>(null);
  const [dbQueryLoading, setDbQueryLoading] = useState(false);

  const files = filesData?.files || [];
  const stats = statsData || { total_files: 0, total_size: 0, by_platform: {}, by_type: {} };
  const dbTables = dbTablesData?.tables || [];
  const dbAvailable = dbTablesData?.available ?? false;

  const filteredFiles = useMemo(() => {
    if (!searchQuery) return files;
    const query = searchQuery.toLowerCase();
    return files.filter(file => file.name.toLowerCase().includes(query));
  }, [files, searchQuery]);

  const platformCounts = useMemo(() => {
    if (viewMode === 'database') {
      const counts: Record<string, number> = { all: dbStatsData?.total_records || 0 };
      Object.entries(dbStatsData?.by_platform || {}).forEach(([p, c]) => { counts[p] = c; });
      return counts;
    }
    const counts: Record<string, number> = { all: stats.total_files };
    Object.entries(stats.by_platform).forEach(([p, c]) => { counts[p] = c; });
    return counts;
  }, [viewMode, stats, dbStatsData]);

  const handleDownload = (filePath: string) => {
    window.open(getDownloadUrl(filePath), '_blank');
  };

  const handleViewTable = async (table: string) => {
    setSelectedTable(table);
    setDbPage(1);
    setDbSearch('');
    setDbQueryLoading(true);
    try {
      const result = await queryDbTable({ table, page: 1, page_size: 50 });
      setDbQueryResult(result);
    } catch {
      setDbQueryResult(null);
    } finally {
      setDbQueryLoading(false);
    }
  };

  const handleDbPageChange = async (newPage: number) => {
    if (!selectedTable) return;
    setDbPage(newPage);
    setDbQueryLoading(true);
    try {
      const result = await queryDbTable({ table: selectedTable, page: newPage, page_size: 50, search: dbSearch || undefined });
      setDbQueryResult(result);
    } catch {
      setDbQueryResult(null);
    } finally {
      setDbQueryLoading(false);
    }
  };

  const handleDbSearch = async () => {
    if (!selectedTable) return;
    setDbPage(1);
    setDbQueryLoading(true);
    try {
      const result = await queryDbTable({ table: selectedTable, page: 1, page_size: 50, search: dbSearch || undefined });
      setDbQueryResult(result);
    } catch {
      setDbQueryResult(null);
    } finally {
      setDbQueryLoading(false);
    }
  };

  const handleRefresh = () => {
    if (viewMode === 'files') {
      refetchFiles();
    } else {
      refetchDbTables();
    }
  };

  const isLoading = viewMode === 'files'
    ? (filesLoading && files.length === 0)
    : (dbTablesLoading && dbTables.length === 0);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        <PageHeader
          title="数据管理"
          subtitle="管理各平台采集的数据"
          actions={
            <div className="flex items-center gap-3">
              {/* 视图切换 */}
              <div className="flex items-center bg-slate-100 rounded-lg p-1">
                <button
                  onClick={() => { setViewMode('database'); setSelectedTable(null); }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    viewMode === 'database' ? 'bg-white text-primary shadow-sm font-medium' : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  <Database className="w-4 h-4" />
                  数据库
                </button>
                <button
                  onClick={() => setViewMode('files')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    viewMode === 'files' ? 'bg-white text-primary shadow-sm font-medium' : 'text-text-secondary hover:text-text-primary'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  文件
                </button>
              </div>

              <Button variant="secondary" onClick={handleRefresh}>
                <RefreshCw className={`w-4 h-4 ${(filesLoading || dbTablesLoading) ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>
          }
        />

        {/* 统计卡片 */}
        {viewMode === 'files' ? (
          <div className="grid grid-cols-4 gap-4">
            <StatCard label="总文件数" value={statsLoading ? '-' : stats.total_files} />
            <StatCard label="总大小" value={statsLoading ? '-' : formatFileSize(stats.total_size)} />
            <StatCard label="JSON 文件" value={statsLoading ? '-' : (stats.by_type.json || 0)} />
            <StatCard label="CSV 文件" value={statsLoading ? '-' : (stats.by_type.csv || 0)} />
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-4">
            <StatCard label="数据库记录" value={dbStatsLoading ? '-' : (dbStatsData?.total_records?.toLocaleString() || '0')} />
            <StatCard label="数据表数" value={dbTablesLoading ? '-' : dbTables.length} />
            <StatCard label="存储类型" value={dbStatsLoading ? '-' : (dbTablesData?.db_type || '-').toUpperCase()} />
            <StatCard
              label="数据库状态"
              value={dbStatsLoading ? '-' : (dbAvailable ? '已连接' : '未连接')}
              valueColor={dbAvailable ? 'text-green-600' : 'text-red-500'}
            />
          </div>
        )}

        {/* 平台标签 */}
        <div className="border-b border-border pb-4">
          <PlatformTabs
            value={activePlatform}
            onChange={(value) => { setActivePlatform(value as Platform); setSelectedTable(null); }}
            showAll
            counts={platformCounts}
          />
        </div>

        {/* 内容区 */}
        {viewMode === 'files' ? (
          <FilesView
            files={filteredFiles}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onDownload={handleDownload}
          />
        ) : selectedTable && dbQueryResult ? (
          <DbTableView
            result={dbQueryResult}
            loading={dbQueryLoading}
            page={dbPage}
            search={dbSearch}
            onSearchChange={setDbSearch}
            onSearch={handleDbSearch}
            onPageChange={handleDbPageChange}
            onBack={() => setSelectedTable(null)}
          />
        ) : (
          <DbTablesListView
            tables={dbTables}
            available={dbAvailable}
            dbType={dbTablesData?.db_type}
            onViewTable={handleViewTable}
          />
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, valueColor }: { label: string; value: string | number; valueColor?: string }) {
  return (
    <div className="bg-slate-50 rounded-lg p-4">
      <div className="text-sm text-text-secondary mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${valueColor || 'text-text-primary'}`}>{value}</div>
    </div>
  );
}

function FilesView({ files, searchQuery, onSearchChange, onDownload }: {
  files: Array<{ name: string; path: string; size: number; modified_at: number; record_count: number | null; type: string }>;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  onDownload: (path: string) => void;
}) {
  return (
    <>
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="搜索文件名..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full h-10 pl-10 pr-4 rounded-lg bg-slate-50 border border-slate-200 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-text-secondary">共</span>
          <span className="text-primary font-semibold">{files.length}</span>
          <span className="text-text-secondary">个文件</span>
        </div>
      </div>

      <div className="flex-1">
        {files.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center bg-slate-50 rounded-lg">
            <FileText className="w-12 h-12 text-slate-300 mb-4" />
            <p className="text-text-secondary">暂无数据文件</p>
            <p className="text-sm text-slate-400 mt-1">运行爬虫任务后，数据将显示在这里</p>
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
                {files.map((file) => (
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
                    <td className="py-3 px-4 text-sm text-text-secondary">{formatFileSize(file.size)}</td>
                    <td className="py-3 px-4 text-sm text-text-secondary">{formatTime(file.modified_at)}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onDownload(file.path)}
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
    </>
  );
}

function DbTablesListView({ tables, available, dbType, onViewTable }: {
  tables: Array<{ table: string; label: string; platform: string; record_count: number }>;
  available: boolean;
  dbType?: string;
  onViewTable: (table: string) => void;
}) {
  if (!available) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center bg-slate-50 rounded-lg">
        <Database className="w-12 h-12 text-slate-300 mb-4" />
        <p className="text-text-secondary">数据库未连接</p>
        <p className="text-sm text-slate-400 mt-1">
          当前存储方式为 {dbType?.toUpperCase() || '文件'}，请检查数据库配置
        </p>
      </div>
    );
  }

  if (tables.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center bg-slate-50 rounded-lg">
        <Database className="w-12 h-12 text-slate-300 mb-4" />
        <p className="text-text-secondary">暂无数据库记录</p>
        <p className="text-sm text-slate-400 mt-1">运行爬虫任务后，数据将显示在这里</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-border overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 border-b border-border">
            <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">数据表</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">平台</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">记录数</th>
            <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">操作</th>
          </tr>
        </thead>
        <tbody>
          {tables.map((t) => (
            <tr key={t.table} className="border-b border-border last:border-0 hover:bg-slate-50">
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-slate-400" />
                  <div>
                    <span className="text-sm text-text-primary font-medium">{t.label}</span>
                    <div className="text-xs text-slate-400 mt-0.5">{t.table}</div>
                  </div>
                </div>
              </td>
              <td className="py-3 px-4">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                  {PLATFORM_LABELS[t.platform] || t.platform}
                </span>
              </td>
              <td className="py-3 px-4 text-sm text-text-secondary font-medium">
                {t.record_count.toLocaleString()}
              </td>
              <td className="py-3 px-4 text-right">
                <button
                  onClick={() => onViewTable(t.table)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-primary hover:bg-primary/10 rounded transition-colors"
                >
                  <Eye className="w-4 h-4" />
                  查看
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const DISPLAY_COLUMNS: Record<string, string> = {
  id: 'ID', note_id: '笔记ID', content: '内容', title: '标题',
  nickname: '昵称', user_id: '用户ID', note_url: '链接',
  liked_count: '点赞', comments_count: '评论数', shared_count: '分享',
  add_ts: '创建时间', last_modify_ts: '更新时间', source_keyword: '关键词',
  comment_id: '评论ID', create_date_time: '发布时间', vuid: 'VIP创作者',
  page_view: '浏览量', poster_url: '封面', money: '价格', date: '日期',
  avatar: '头像', gender: '性别', ip_location: 'IP位置',
  desc: '简介', interact_info: '互动', tag_list: '标签',
};

function DbTableView({ result, loading, page, search, onSearchChange, onSearch, onPageChange, onBack }: {
  result: DbQueryResponse;
  loading: boolean;
  page: number;
  search: string;
  onSearchChange: (v: string) => void;
  onSearch: () => void;
  onPageChange: (p: number) => void;
  onBack: () => void;
}) {
  const visibleColumns = useMemo(() => {
    return result.columns.filter(col => !['add_ts', 'last_modify_ts'].includes(col)).slice(0, 8);
  }, [result.columns]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-text-secondary hover:text-primary transition-colors">
            <ChevronLeft className="w-4 h-4" />
            返回
          </button>
          <h3 className="text-lg font-medium text-text-primary">{result.label}</h3>
          <span className="text-sm text-text-secondary">
            共 {result.total.toLocaleString()} 条记录
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="搜索..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onSearch()}
              className="h-9 pl-9 pr-4 rounded-lg bg-slate-50 border border-slate-200 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
          </div>
          <Button variant="secondary" onClick={onSearch} className="h-9 text-sm">
            搜索
          </Button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-border overflow-x-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-border">
                {visibleColumns.map((col) => (
                  <th key={col} className="text-left py-3 px-4 text-sm font-medium text-text-secondary whitespace-nowrap">
                    {DISPLAY_COLUMNS[col] || col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.data.map((row, idx) => (
                <tr key={idx} className="border-b border-border last:border-0 hover:bg-slate-50">
                  {visibleColumns.map((col) => (
                    <td key={col} className="py-3 px-4 text-sm text-text-secondary max-w-[280px] truncate" title={String(row[col] ?? '')}>
                      {formatCellValue(col, row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 分页 */}
      {result.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">
            第 {page} / {result.total_pages} 页
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
            >
              <ChevronLeft className="w-4 h-4" />
              上一页
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= result.total_pages}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
            >
              下一页
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function formatCellValue(_col: string, value: unknown): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'string' && value.length > 60) return value.slice(0, 60) + '...';
  return String(value);
}
