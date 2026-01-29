import { useState } from 'react';
import {
  MoreHorizontal,
  Edit2,
  Trash2,
  Zap,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Proxy, ProxyStatus, ProxyProtocol } from '../../types';

interface ProxyTableProps {
  proxies: Proxy[];
  onEdit?: (proxy: Proxy) => void;
  onDelete?: (proxy: Proxy) => void;
  onTest?: (proxy: Proxy) => void;
}

const statusConfig: Record<ProxyStatus, { label: string; bgColor: string; dotColor: string }> = {
  online: { label: '在线', bgColor: 'bg-emerald-50', dotColor: 'bg-emerald-500' },
  offline: { label: '离线', bgColor: 'bg-red-50', dotColor: 'bg-red-500' },
  testing: { label: '检测中', bgColor: 'bg-amber-50', dotColor: 'bg-amber-500' },
};

const protocolConfig: Record<ProxyProtocol, { bgColor: string; textColor: string }> = {
  HTTP: { bgColor: 'bg-blue-50', textColor: 'text-blue-600' },
  HTTPS: { bgColor: 'bg-emerald-50', textColor: 'text-emerald-600' },
  SOCKS5: { bgColor: 'bg-purple-50', textColor: 'text-purple-600' },
};

export function ProxyTable({ proxies, onEdit, onDelete, onTest }: ProxyTableProps) {
  const [statusFilter, setStatusFilter] = useState<'all' | ProxyStatus>('all');
  const [protocolFilter, setProtocolFilter] = useState<'all' | ProxyProtocol>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const pageSize = 10;

  // 筛选代理
  const filteredProxies = proxies.filter((proxy) => {
    if (statusFilter !== 'all' && proxy.status !== statusFilter) return false;
    if (protocolFilter !== 'all' && proxy.protocol !== protocolFilter) return false;
    return true;
  });

  // 分页
  const totalPages = Math.ceil(filteredProxies.length / pageSize);
  const paginatedProxies = filteredProxies.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleMenuToggle = (id: string) => {
    setOpenMenuId(openMenuId === id ? null : id);
  };

  return (
    <div className="bg-white rounded-xl border border-border overflow-hidden flex flex-col h-full">
      {/* 表头筛选区 */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold text-text-primary">代理列表</span>
          <span className="text-sm text-text-secondary">({filteredProxies.length})</span>
        </div>
        <div className="flex items-center gap-3">
          {/* 状态筛选 */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as 'all' | ProxyStatus);
              setCurrentPage(1);
            }}
            className="h-9 px-3 rounded-lg border border-border text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          >
            <option value="all">全部状态</option>
            <option value="online">在线</option>
            <option value="offline">离线</option>
            <option value="testing">检测中</option>
          </select>
          {/* 协议筛选 */}
          <select
            value={protocolFilter}
            onChange={(e) => {
              setProtocolFilter(e.target.value as 'all' | ProxyProtocol);
              setCurrentPage(1);
            }}
            className="h-9 px-3 rounded-lg border border-border text-sm text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          >
            <option value="all">全部协议</option>
            <option value="HTTP">HTTP</option>
            <option value="HTTPS">HTTPS</option>
            <option value="SOCKS5">SOCKS5</option>
          </select>
        </div>
      </div>

      {/* 表格 */}
      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              <th className="px-5 py-3 text-left text-sm font-medium text-text-secondary">代理地址</th>
              <th className="px-5 py-3 text-left text-sm font-medium text-text-secondary">协议</th>
              <th className="px-5 py-3 text-left text-sm font-medium text-text-secondary">地区</th>
              <th className="px-5 py-3 text-left text-sm font-medium text-text-secondary">响应时间</th>
              <th className="px-5 py-3 text-left text-sm font-medium text-text-secondary">成功率</th>
              <th className="px-5 py-3 text-left text-sm font-medium text-text-secondary">状态</th>
              <th className="px-5 py-3 text-right text-sm font-medium text-text-secondary">操作</th>
            </tr>
          </thead>
          <tbody>
            {paginatedProxies.map((proxy) => (
              <tr
                key={proxy.id}
                className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors"
              >
                <td className="px-5 py-4">
                  <span className="text-sm font-medium text-text-primary font-mono">
                    {proxy.ip}:{proxy.port}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span
                    className={cn(
                      'inline-flex px-2.5 py-1 rounded-md text-xs font-medium',
                      protocolConfig[proxy.protocol].bgColor,
                      protocolConfig[proxy.protocol].textColor
                    )}
                  >
                    {proxy.protocol}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className="text-sm text-text-secondary">{proxy.region || '-'}</span>
                </td>
                <td className="px-5 py-4">
                  <span className="text-sm text-text-primary">
                    {proxy.status === 'online' ? `${proxy.responseTime}ms` : '-'}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className="text-sm text-text-primary">
                    {proxy.status === 'online' ? `${proxy.successRate}%` : '-'}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                      statusConfig[proxy.status].bgColor
                    )}
                  >
                    <span
                      className={cn(
                        'w-1.5 h-1.5 rounded-full',
                        statusConfig[proxy.status].dotColor
                      )}
                    />
                    {statusConfig[proxy.status].label}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center justify-end gap-1 relative">
                    <button
                      onClick={() => onTest?.(proxy)}
                      className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
                      title="测试连接"
                    >
                      <Zap className="w-4 h-4 text-text-secondary" />
                    </button>
                    <button
                      onClick={() => onEdit?.(proxy)}
                      className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
                      title="编辑"
                    >
                      <Edit2 className="w-4 h-4 text-text-secondary" />
                    </button>
                    <button
                      onClick={() => onDelete?.(proxy)}
                      className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-red-50 transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      <div className="flex items-center justify-between px-5 py-4 border-t border-border">
        <span className="text-sm text-text-secondary">
          显示 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, filteredProxies.length)} 共 {filteredProxies.length} 条
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-border hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4 text-text-secondary" />
          </button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let page: number;
            if (totalPages <= 5) {
              page = i + 1;
            } else if (currentPage <= 3) {
              page = i + 1;
            } else if (currentPage >= totalPages - 2) {
              page = totalPages - 4 + i;
            } else {
              page = currentPage - 2 + i;
            }
            return (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={cn(
                  'w-8 h-8 flex items-center justify-center rounded-lg text-sm font-medium transition-colors',
                  currentPage === page
                    ? 'bg-primary text-white'
                    : 'border border-border hover:bg-slate-50 text-text-primary'
                )}
              >
                {page}
              </button>
            );
          })}
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-border hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4 text-text-secondary" />
          </button>
        </div>
      </div>
    </div>
  );
}
