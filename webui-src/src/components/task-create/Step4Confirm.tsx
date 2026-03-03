import { useState, useEffect } from 'react';
import { Settings, FileText, Shield } from 'lucide-react';
import { Platform, TaskConfig } from '../../types';
import { PLATFORMS, CRAWL_MODE_OPTIONS, PLATFORM_FIELDS } from '../../lib/constants';
import { getAccount } from '../../api/accounts';

interface ProxyConfig {
  use_proxy: boolean;
  retry_count: number;
  timeout: number;
}

interface Step4ConfirmProps {
  platform: Platform | null;
  config: Partial<TaskConfig>;
  proxyConfig: ProxyConfig;
  selectedAccountId: string | null;
  onEdit: (step: number) => void;
}

function getPlatformExtraSummary(platform: Platform | null, config: Partial<TaskConfig>): { label: string; value: string }[] {
  if (!platform) return [];
  const items: { label: string; value: string }[] = [];
  const crawlerType = config.crawler_type || 'search';
  const fields = (PLATFORM_FIELDS[platform] || []).filter(
    (f) => !f.showWhen || f.showWhen.includes(crawlerType)
  );

  for (const field of fields) {
    const val = (config as Record<string, unknown>)[field.key];
    if (val === undefined || val === null || val === '') continue;

    if (field.type === 'textarea') {
      const list = Array.isArray(val) ? val as string[] : (val as string).split('\n').filter(Boolean);
      if (list.length > 0) {
        items.push({ label: field.label, value: `${list.length} 项` });
      }
    } else if (field.type === 'select' && field.options) {
      const opt = field.options.find((o) => o.value === String(val));
      items.push({ label: field.label, value: opt?.label || String(val) });
    } else if (field.type === 'switch') {
      items.push({ label: field.label, value: val ? '已开启' : '已关闭' });
    } else {
      items.push({ label: field.label, value: String(val) });
    }
  }
  return items;
}

export function Step4Confirm({ platform, config, proxyConfig, selectedAccountId, onEdit }: Step4ConfirmProps) {
  const platformInfo = PLATFORMS.find((p) => p.id === platform);
  const crawlModeLabel = CRAWL_MODE_OPTIONS.find((o) => o.value === config.crawler_type)?.label;

  const [accountName, setAccountName] = useState<string>('加载中...');
  useEffect(() => {
    if (!selectedAccountId) {
      setAccountName('未选择（使用本地登录态）');
      return;
    }
    getAccount(selectedAccountId)
      .then((a) => setAccountName(a.nickname || a.username || selectedAccountId.slice(0, 8)))
      .catch(() => setAccountName(selectedAccountId.slice(0, 8)));
  }, [selectedAccountId]);

  const dataOptions = [];
  if (config.enable_comments) dataOptions.push('评论');
  if (config.enable_media) dataOptions.push('媒体文件');

  const crawlerType = config.crawler_type || 'search';
  const platformExtras = getPlatformExtraSummary(platform, config);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold font-display text-text-primary">
          确认任务配置
        </h2>
        <p className="text-sm text-text-secondary">
          请检查以下配置信息，确认无误后点击开始执行
        </p>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* 平台 & 账号 */}
        <SummaryCard
          icon={<span className="text-2xl">{platformInfo?.icon}</span>}
          iconBgColor="bg-error-100"
          title="平台与账号"
          onEdit={() => onEdit(1)}
        >
          <div className="space-y-3">
            <SummaryItem label="目标平台" value={platformInfo?.name || '-'} />
            <SummaryItem label="登录账号" value={accountName} />
          </div>
        </SummaryCard>

        {/* 爬取参数 */}
        <SummaryCard
          icon={<Settings className="w-5 h-5 text-primary" />}
          iconBgColor="bg-primary-100"
          title="爬取参数"
          onEdit={() => onEdit(3)}
        >
          <div className="space-y-3">
            <SummaryItem label="采集模式" value={crawlModeLabel || '-'} />
            {crawlerType === 'search' && (
              <SummaryItem label="关键词" value={config.keywords?.join(', ') || '-'} />
            )}
            {crawlerType === 'detail' && (
              <SummaryItem label="指定内容" value={`${config.note_urls?.length || 0} 项`} />
            )}
            {(crawlerType === 'creator') && (
              <SummaryItem label="创作者" value={`${config.creator_ids?.length || 0} 个`} />
            )}
            <SummaryItem label="采集数量" value={config.max_notes?.toString() || '100'} />
            <SummaryItem label="数据选项" value={dataOptions.length > 0 ? dataOptions.join('、') : '仅基础数据'} />
            <SummaryItem label="存储方式" value={
              { db: 'MySQL 数据库', sqlite: 'SQLite 数据库', postgres: 'PostgreSQL 数据库', json: 'JSON 文件', csv: 'CSV 文件', excel: 'Excel 文件' }[config.save_option || 'db'] || config.save_option || 'db'
            } />
            {platformExtras.map((item) => (
              <SummaryItem key={item.label} label={item.label} value={item.value} />
            ))}
          </div>
        </SummaryCard>

        {/* 代理设置 */}
        <SummaryCard
          icon={<Shield className="w-5 h-5 text-purple-500" />}
          iconBgColor="bg-purple-100"
          title="代理设置"
          onEdit={() => onEdit(5)}
        >
          <div className="space-y-3">
            <SummaryItem
              label="代理状态"
              value={proxyConfig.use_proxy ? '已启用' : '未启用'}
            />
            {proxyConfig.use_proxy && (
              <>
                <SummaryItem label="重试次数" value={proxyConfig.retry_count?.toString() || '3'} />
                <SummaryItem label="超时时间" value={`${proxyConfig.timeout || 30}秒`} />
              </>
            )}
          </div>
        </SummaryCard>
      </div>
    </div>
  );
}

interface SummaryCardProps {
  icon: React.ReactNode;
  iconBgColor: string;
  title: string;
  onEdit: () => void;
  children: React.ReactNode;
}

function SummaryCard({ icon, iconBgColor, title, onEdit, children }: SummaryCardProps) {
  return (
    <div className="bg-slate-50 rounded-lg border border-slate-200 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-secondary" />
          <span className="text-sm font-medium text-text-primary">{title}</span>
        </div>
        <button
          onClick={onEdit}
          className="text-sm text-primary hover:underline"
        >
          编辑
        </button>
      </div>

      <div className="flex items-start gap-3 p-4 bg-white rounded-lg">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${iconBgColor}`}>
          {icon}
        </div>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}

interface SummaryItemProps {
  label: string;
  value: string;
}

function SummaryItem({ label, value }: SummaryItemProps) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-text-secondary">{label}</span>
      <span className="text-text-primary font-medium">{value}</span>
    </div>
  );
}
