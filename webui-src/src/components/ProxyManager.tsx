// 代理管理组件

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Select } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Switch } from './ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';
import { toast } from './ui/toast';
import {
  RefreshCw,
  Upload,
  Trash2,
  Link,
  Unlink,
  Settings,
  BarChart3,
  Shield,
  Globe,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';

import { proxyApi } from '../api/proxy';
import type {
  ProxyInfo,
  BindingInfo,
  OverviewStats,
  ProxySettings,
  ProxyImportItem,
} from '../types/proxy';

// ==================== 统计卡片组件 ====================

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
}

function StatCard({ title, value, description, icon }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

// ==================== 代理列表组件 ====================

interface ProxyTableProps {
  proxies: ProxyInfo[];
  selectedIds: Set<string>;
  onSelect: (id: string) => void;
  onSelectAll: () => void;
  onToggleStatus: (id: string, active: boolean) => void;
  onDelete: (id: string) => void;
}

function ProxyTable({
  proxies,
  selectedIds,
  onSelect,
  onSelectAll,
  onToggleStatus,
  onDelete,
}: ProxyTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">
              <input
                type="checkbox"
                checked={selectedIds.size === proxies.length && proxies.length > 0}
                onChange={onSelectAll}
                className="h-4 w-4"
              />
            </TableHead>
            <TableHead>地址</TableHead>
            <TableHead>协议</TableHead>
            <TableHead>来源</TableHead>
            <TableHead>地区</TableHead>
            <TableHead>质量分</TableHead>
            <TableHead>状态</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {proxies.map((proxy) => (
            <TableRow key={proxy.proxy_id}>
              <TableCell>
                <input
                  type="checkbox"
                  checked={selectedIds.has(proxy.proxy_id)}
                  onChange={() => onSelect(proxy.proxy_id)}
                  className="h-4 w-4"
                />
              </TableCell>
              <TableCell className="font-mono text-sm">
                {proxy.ip}:{proxy.port}
              </TableCell>
              <TableCell>
                <Badge variant="outline">{proxy.protocol.toUpperCase()}</Badge>
              </TableCell>
              <TableCell>{proxy.source}</TableCell>
              <TableCell>
                {[proxy.country, proxy.province, proxy.city].filter(Boolean).join(' ')}
              </TableCell>
              <TableCell>
                <span className={proxyApi.getQualityColor(proxy.quality_score)}>
                  {proxy.quality_score.toFixed(1)}
                </span>
              </TableCell>
              <TableCell>
                <Badge variant={proxy.is_active ? 'default' : 'secondary'}>
                  {proxy.is_active ? '可用' : '禁用'}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onToggleStatus(proxy.proxy_id, !proxy.is_active)}
                  >
                    {proxy.is_active ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(proxy.proxy_id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
          {proxies.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                暂无代理数据
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}

// ==================== 绑定列表组件 ====================

interface BindingTableProps {
  bindings: BindingInfo[];
  onUnbind: (accountId: string, platform: string) => void;
}

function BindingTable({ bindings, onUnbind }: BindingTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>账号ID</TableHead>
            <TableHead>平台</TableHead>
            <TableHead>代理</TableHead>
            <TableHead>粘性</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>绑定时间</TableHead>
            <TableHead>重绑次数</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {bindings.map((binding) => (
            <TableRow key={binding.binding_id}>
              <TableCell className="font-mono text-sm">{binding.account_id}</TableCell>
              <TableCell>
                <Badge variant="outline">{binding.platform.toUpperCase()}</Badge>
              </TableCell>
              <TableCell className="font-mono text-sm">
                {binding.proxy_ip}:{binding.proxy_port}
              </TableCell>
              <TableCell>
                {binding.is_sticky ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-muted-foreground" />
                )}
              </TableCell>
              <TableCell>
                <Badge variant={proxyApi.getStatusBadgeVariant(binding.status)}>
                  {binding.status}
                </Badge>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {binding.bound_at ? new Date(binding.bound_at).toLocaleString() : '-'}
              </TableCell>
              <TableCell>{binding.rebind_count}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onUnbind(binding.account_id, binding.platform)}
                >
                  <Unlink className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {bindings.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                暂无绑定关系
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}

// ==================== 导入对话框组件 ====================

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (proxies: ProxyImportItem[]) => void;
}

function ImportDialog({ open, onOpenChange, onImport }: ImportDialogProps) {
  const [inputText, setInputText] = useState('');
  const [protocol, setProtocol] = useState('http');

  const handleImport = () => {
    const lines = inputText.trim().split('\n').filter(Boolean);
    const proxies: ProxyImportItem[] = [];

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;

      // 尝试解析格式: ip:port[:user:password]
      const parts = trimmed.split(':');
      if (parts.length >= 2) {
        const ip = parts[0];
        const port = parseInt(parts[1], 10);
        if (!isNaN(port)) {
          proxies.push({
            ip,
            port,
            protocol,
            username: parts[2] || undefined,
            password: parts[3] || undefined,
          });
        }
      }
    }

    if (proxies.length > 0) {
      onImport(proxies);
      setInputText('');
      onOpenChange(false);
    } else {
      toast({
        title: '导入失败',
        description: '未解析到有效的代理地址',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>导入代理</DialogTitle>
          <DialogDescription>
            每行一个代理，格式：ip:port 或 ip:port:user:password
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>默认协议</Label>
            <Select value={protocol} onChange={(e) => setProtocol(e.target.value)}>
              <option value="http">HTTP</option>
              <option value="https">HTTPS</option>
              <option value="socks5">SOCKS5</option>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>代理列表</Label>
            <textarea
              className="w-full h-48 p-3 rounded-md border bg-background font-mono text-sm"
              placeholder="192.168.1.1:8080
192.168.1.2:8080:user:password
# 以 # 开头的行会被忽略"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleImport}>导入</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================== 主组件 ====================

export function ProxyManager() {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [proxies, setProxies] = useState<ProxyInfo[]>([]);
  const [bindings, setBindings] = useState<BindingInfo[]>([]);
  const [settings, setSettings] = useState<ProxySettings | null>(null);
  const [selectedProxyIds, setSelectedProxyIds] = useState<Set<string>>(new Set());
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsData, proxyData, bindingData, settingsData] = await Promise.all([
        proxyApi.getOverviewStats(),
        proxyApi.getProxyList({ limit: 100 }),
        proxyApi.getBindingList({ limit: 100 }),
        proxyApi.getProxySettings(),
      ]);
      setStats(statsData);
      setProxies(proxyData.items);
      setBindings(bindingData.items);
      setSettings(settingsData);
    } catch (error) {
      console.error('Failed to load proxy data:', error);
      toast({
        title: '加载失败',
        description: '无法加载代理数据',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 导入代理
  const handleImport = async (importProxies: ProxyImportItem[]) => {
    try {
      const result = await proxyApi.importProxies(importProxies);
      toast({
        title: '导入成功',
        description: result.message,
      });
      loadData();
    } catch (error) {
      toast({
        title: '导入失败',
        description: String(error),
        variant: 'destructive',
      });
    }
  };

  // 删除代理
  const handleDeleteProxy = async (proxyId: string) => {
    try {
      await proxyApi.deleteProxy(proxyId);
      toast({ title: '删除成功' });
      loadData();
    } catch (error) {
      toast({
        title: '删除失败',
        description: String(error),
        variant: 'destructive',
      });
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedProxyIds.size === 0) return;
    try {
      await proxyApi.batchDeleteProxies(Array.from(selectedProxyIds));
      toast({ title: '批量删除成功' });
      setSelectedProxyIds(new Set());
      loadData();
    } catch (error) {
      toast({
        title: '删除失败',
        description: String(error),
        variant: 'destructive',
      });
    }
  };

  // 切换代理状态
  const handleToggleStatus = async (proxyId: string, active: boolean) => {
    try {
      await proxyApi.updateProxyStatus(proxyId, active);
      toast({ title: active ? '已启用' : '已禁用' });
      loadData();
    } catch (error) {
      toast({
        title: '操作失败',
        description: String(error),
        variant: 'destructive',
      });
    }
  };

  // 解绑
  const handleUnbind = async (accountId: string, platform: string) => {
    try {
      await proxyApi.deleteBinding(accountId, platform);
      toast({ title: '已解绑' });
      loadData();
    } catch (error) {
      toast({
        title: '解绑失败',
        description: String(error),
        variant: 'destructive',
      });
    }
  };

  // 选择代理
  const handleSelectProxy = (id: string) => {
    const newSelected = new Set(selectedProxyIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedProxyIds(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedProxyIds.size === proxies.length) {
      setSelectedProxyIds(new Set());
    } else {
      setSelectedProxyIds(new Set(proxies.map((p) => p.proxy_id)));
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">代理管理</h1>
          <p className="text-muted-foreground">管理代理池、账号绑定和质量监控</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button size="sm" onClick={() => setImportDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            导入代理
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="代理总数"
            value={stats.total_proxies}
            description={`${stats.active_proxies} 个可用`}
            icon={<Globe className="h-4 w-4 text-muted-foreground" />}
          />
          <StatCard
            title="绑定数"
            value={stats.total_bindings}
            description={`${stats.active_bindings} 个活跃`}
            icon={<Link className="h-4 w-4 text-muted-foreground" />}
          />
          <StatCard
            title="今日请求"
            value={stats.today_requests}
            description={`成功率 ${(stats.today_success_rate * 100).toFixed(1)}%`}
            icon={<Activity className="h-4 w-4 text-muted-foreground" />}
          />
          <StatCard
            title="平均质量分"
            value={stats.avg_quality_score.toFixed(1)}
            icon={<Shield className="h-4 w-4 text-muted-foreground" />}
          />
        </div>
      )}

      {/* 主要内容 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <Globe className="h-4 w-4 mr-2" />
            代理列表
          </TabsTrigger>
          <TabsTrigger value="bindings">
            <Link className="h-4 w-4 mr-2" />
            账号绑定
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            配置设置
          </TabsTrigger>
          <TabsTrigger value="statistics">
            <BarChart3 className="h-4 w-4 mr-2" />
            统计分析
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* 工具栏 */}
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                disabled={selectedProxyIds.size === 0}
                onClick={handleBatchDelete}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                批量删除 ({selectedProxyIds.size})
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">共 {proxies.length} 个代理</span>
            </div>
          </div>

          <ProxyTable
            proxies={proxies}
            selectedIds={selectedProxyIds}
            onSelect={handleSelectProxy}
            onSelectAll={handleSelectAll}
            onToggleStatus={handleToggleStatus}
            onDelete={handleDeleteProxy}
          />
        </TabsContent>

        <TabsContent value="bindings" className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <span className="text-sm text-muted-foreground">共 {bindings.length} 个绑定</span>
            </div>
          </div>
          <BindingTable bindings={bindings} onUnbind={handleUnbind} />
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          {settings && (
            <div className="grid gap-6 md:grid-cols-2">
              {/* 全局设置 */}
              <Card>
                <CardHeader>
                  <CardTitle>全局设置</CardTitle>
                  <CardDescription>代理池基本配置</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>启用代理</Label>
                    <Switch checked={settings.global_settings.enable_proxy} disabled />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>代理池大小</Label>
                    <span className="text-sm">{settings.global_settings.proxy_pool_size}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>启用账号绑定</Label>
                    <Switch checked={settings.global_settings.enable_binding} disabled />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>粘性绑定</Label>
                    <Switch checked={settings.global_settings.binding_sticky} disabled />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>自动重绑</Label>
                    <Switch checked={settings.global_settings.auto_rebind} disabled />
                  </div>
                </CardContent>
              </Card>

              {/* 质量评估 */}
              <Card>
                <CardHeader>
                  <CardTitle>质量评估</CardTitle>
                  <CardDescription>代理质量检测配置</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>启用质量评估</Label>
                    <Switch checked={settings.quality.enabled} disabled />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>最低质量分</Label>
                    <span className="text-sm">{settings.quality.min_quality_score}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>自动淘汰</Label>
                    <Switch checked={settings.quality.auto_retire_enabled} disabled />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>最大连续失败</Label>
                    <span className="text-sm">{settings.quality.max_consecutive_failures}</span>
                  </div>
                </CardContent>
              </Card>

              {/* 故障转移 */}
              <Card>
                <CardHeader>
                  <CardTitle>故障转移</CardTitle>
                  <CardDescription>代理失败处理配置</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label>启用故障转移</Label>
                    <Switch checked={settings.failover.enabled} disabled />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>转移策略</Label>
                    <Badge variant="outline">{settings.failover.strategy}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>最大重试次数</Label>
                    <span className="text-sm">{settings.failover.max_retries}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label>重试延迟</Label>
                    <span className="text-sm">{settings.failover.retry_delay_seconds}s</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="statistics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>统计分析</CardTitle>
              <CardDescription>代理使用情况和性能分析</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12 text-muted-foreground">
                <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>统计图表功能开发中...</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 导入对话框 */}
      <ImportDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onImport={handleImport}
      />
    </div>
  );
}

export default ProxyManager;

