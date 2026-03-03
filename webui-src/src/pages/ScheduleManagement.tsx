import { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Clock,
  Pause,
  Play,
  Trash2,
  Zap,
  Calendar,
  Timer,
  Globe,
} from 'lucide-react';
import { PageHeader } from '../components/layout';
import { Button, Badge, Modal, Input, Select, PlatformIcon } from '../components/common';
import { schedulesApi, type Schedule, type ScheduleCreateRequest, type ScheduleConfig } from '../api/schedules';
import { toast } from '../components/ui/toast';
import { confirm } from '../components/ui/confirm';
import { PLATFORMS, CRAWL_MODE_OPTIONS, PLATFORM_CRAWL_MODES } from '../lib/constants';
import type { Platform } from '../types';

const TRIGGER_TYPE_LABELS: Record<string, { label: string; icon: typeof Clock }> = {
  cron: { label: 'Cron 定时', icon: Calendar },
  interval: { label: '固定间隔', icon: Timer },
  once: { label: '一次性', icon: Zap },
};

const CRON_PRESETS = [
  { label: '每天 8:00', value: '0 8 * * *' },
  { label: '每天 12:00', value: '0 12 * * *' },
  { label: '每天 20:00', value: '0 20 * * *' },
  { label: '每 6 小时', value: '0 */6 * * *' },
  { label: '每 12 小时', value: '0 */12 * * *' },
  { label: '每周一 9:00', value: '0 9 * * 1' },
  { label: '周一三五 9:00', value: '0 9 * * 1,3,5' },
];

function formatDateTime(iso: string | undefined) {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleString('zh-CN');
  } catch {
    return iso;
  }
}

function describeTrigger(s: Schedule): string {
  if (s.trigger_type === 'cron' && s.cron_expression) {
    const preset = CRON_PRESETS.find((p) => p.value === s.cron_expression);
    return preset ? preset.label : `Cron: ${s.cron_expression}`;
  }
  if (s.trigger_type === 'interval' && s.interval_seconds) {
    const h = Math.floor(s.interval_seconds / 3600);
    const m = Math.floor((s.interval_seconds % 3600) / 60);
    if (h > 0 && m > 0) return `每 ${h}h${m}m`;
    if (h > 0) return `每 ${h} 小时`;
    return `每 ${m} 分钟`;
  }
  return '一次性';
}

export function ScheduleManagement() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const res = await schedulesApi.list({ page_size: 100 });
      setSchedules(res.schedules);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to fetch schedules:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  const handleToggle = async (s: Schedule) => {
    setActionLoading(s.schedule_id);
    try {
      if (s.enabled) {
        await schedulesApi.pause(s.schedule_id);
      } else {
        await schedulesApi.resume(s.schedule_id);
      }
      await fetchSchedules();
    } catch (err: any) {
      toast.error(err.message || '操作失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTrigger = async (s: Schedule) => {
    setActionLoading(s.schedule_id);
    try {
      const res = await schedulesApi.trigger(s.schedule_id);
      toast.success(`已触发任务: ${res.task_id}`);
      await fetchSchedules();
    } catch (err: any) {
      toast.error(err.message || '触发失败');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (s: Schedule) => {
    const ok = await confirm({
      title: '删除调度计划',
      message: `确定删除调度计划「${s.schedule_name}」？删除后不可恢复。`,
      confirmText: '删除',
      variant: 'danger',
    });
    if (!ok) return;
    setActionLoading(s.schedule_id);
    try {
      await schedulesApi.delete(s.schedule_id);
      await fetchSchedules();
    } catch (err: any) {
      toast.error(err.message || '删除失败');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      <div className="p-6 space-y-6 flex-1 overflow-auto">
        <PageHeader
          title="定时调度"
          subtitle={`管理周期性爬取计划，支持 Cron 定时、固定间隔等调度方式 (${total} 个计划)`}
          actions={
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4 mr-1.5" />
              新建调度
            </Button>
          }
        />

        {loading ? (
          <div className="flex items-center justify-center py-20 text-text-secondary">
            加载中...
          </div>
        ) : schedules.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-text-secondary space-y-3">
            <Clock className="w-12 h-12 text-slate-300" />
            <p>暂无调度计划</p>
            <Button variant="secondary" onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4 mr-1.5" />
              创建第一个调度
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {schedules.map((s) => {
              const TriggerIcon = TRIGGER_TYPE_LABELS[s.trigger_type]?.icon || Clock;
              const isLoading = actionLoading === s.schedule_id;
              return (
                <div
                  key={s.schedule_id}
                  className={`border rounded-xl p-5 transition-colors ${
                    s.enabled ? 'border-border bg-white' : 'border-slate-200 bg-slate-50 opacity-75'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-center gap-2.5">
                        <PlatformIcon platformId={s.platform as Platform} size={20} />
                        <h3 className="font-semibold text-text-primary truncate">
                          {s.schedule_name}
                        </h3>
                        <Badge variant={s.enabled ? 'success' : 'gray'}>
                          {s.enabled ? '运行中' : '已暂停'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-text-secondary">
                        <span className="flex items-center gap-1">
                          <TriggerIcon className="w-3.5 h-3.5" />
                          {describeTrigger(s)}
                        </span>
                        <span>已执行 {s.total_runs} 次</span>
                        {s.last_run_at && (
                          <span>上次: {formatDateTime(s.last_run_at)}</span>
                        )}
                        {s.webhook_url && (
                          <span className="flex items-center gap-1 text-primary">
                            <Globe className="w-3.5 h-3.5" />
                            Webhook
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleTrigger(s)}
                        disabled={isLoading}
                        title="立即触发一次"
                      >
                        <Zap className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggle(s)}
                        disabled={isLoading}
                        title={s.enabled ? '暂停' : '恢复'}
                      >
                        {s.enabled ? (
                          <Pause className="w-4 h-4" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(s)}
                        disabled={isLoading}
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4 text-error" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateScheduleModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            fetchSchedules();
          }}
        />
      )}
    </div>
  );
}

// ========== 创建调度弹窗 ==========

function CreateScheduleModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [platform, setPlatform] = useState<Platform>('xhs');
  const [crawlerType, setCrawlerType] = useState('search');
  const [keywords, setKeywords] = useState('');
  const [maxNotes, setMaxNotes] = useState(100);
  const [triggerType, setTriggerType] = useState<'cron' | 'interval'>('cron');
  const [cronExpression, setCronExpression] = useState('0 8 * * *');
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const availableModes = PLATFORM_CRAWL_MODES[platform] || ['search'];

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error('请输入调度名称');
      return;
    }

    setSubmitting(true);
    try {
      const taskConfig: ScheduleConfig = {
        platform,
        crawler_type: crawlerType,
        max_notes: maxNotes,
        enable_comments: false,
        max_comments_per_note: 20,
        enable_media: false,
        concurrency: 3,
        crawl_interval: 1.0,
        save_option: 'json',
      };

      if (crawlerType === 'search' && keywords.trim()) {
        taskConfig.keywords = keywords.split('\n').map((k) => k.trim()).filter(Boolean);
      }

      const req: ScheduleCreateRequest = {
        schedule_name: name,
        task_config: taskConfig,
        trigger_type: triggerType,
        timezone: 'Asia/Shanghai',
      };

      if (triggerType === 'cron') {
        req.cron_expression = cronExpression;
      } else {
        req.interval_seconds = intervalMinutes * 60;
      }

      if (webhookUrl.trim()) {
        req.webhook_url = webhookUrl.trim();
        req.webhook_secret = webhookSecret.trim();
      }

      await schedulesApi.create(req);
      onCreated();
    } catch (err: any) {
      toast.error(err.message || '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={true} onClose={onClose} title="新建定时调度" width="lg">
      <div className="space-y-5">
        {/* 基本信息 */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-1.5">调度名称</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：每日小红书热点监控"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">平台</label>
            <Select
              value={platform}
              onChange={(e) => {
                const p = e.target.value as Platform;
                setPlatform(p);
                const modes = PLATFORM_CRAWL_MODES[p] || ['search'];
                if (!modes.includes(crawlerType)) setCrawlerType(modes[0]);
              }}
              options={PLATFORMS.map((p) => ({ value: p.id, label: `${p.icon} ${p.name}` }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">采集模式</label>
            <Select
              value={crawlerType}
              onChange={(e) => setCrawlerType(e.target.value)}
              options={CRAWL_MODE_OPTIONS.filter((m) => availableModes.includes(m.value))}
            />
          </div>
        </div>

        {crawlerType === 'search' && (
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">搜索关键词（每行一个）</label>
            <textarea
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="AI绘画&#10;竞品分析"
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary resize-none"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-text-primary mb-1.5">最大爬取数量</label>
          <Input
            type="number"
            value={maxNotes}
            onChange={(e) => setMaxNotes(Number(e.target.value))}
            min={1}
            max={10000}
          />
        </div>

        {/* 调度配置 */}
        <div className="border-t border-border pt-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3">调度配置</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">触发方式</label>
              <div className="flex gap-3">
                <button
                  onClick={() => setTriggerType('cron')}
                  className={`flex-1 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                    triggerType === 'cron'
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-border text-text-secondary hover:bg-slate-50'
                  }`}
                >
                  <Calendar className="w-4 h-4 inline mr-1.5" />
                  Cron 定时
                </button>
                <button
                  onClick={() => setTriggerType('interval')}
                  className={`flex-1 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                    triggerType === 'interval'
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-border text-text-secondary hover:bg-slate-50'
                  }`}
                >
                  <Timer className="w-4 h-4 inline mr-1.5" />
                  固定间隔
                </button>
              </div>
            </div>

            {triggerType === 'cron' ? (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">Cron 表达式</label>
                <Input
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                  placeholder="0 8 * * *"
                />
                <div className="flex flex-wrap gap-2 mt-2">
                  {CRON_PRESETS.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => setCronExpression(p.value)}
                      className={`px-2.5 py-1 rounded-md text-xs border transition-colors ${
                        cronExpression === p.value
                          ? 'border-primary bg-primary/5 text-primary'
                          : 'border-border text-text-secondary hover:bg-slate-50'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">间隔（分钟）</label>
                <Input
                  type="number"
                  value={intervalMinutes}
                  onChange={(e) => setIntervalMinutes(Number(e.target.value))}
                  min={1}
                  placeholder="60"
                />
              </div>
            )}
          </div>
        </div>

        {/* Webhook */}
        <div className="border-t border-border pt-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-1.5">
            <Globe className="w-4 h-4" />
            Webhook 回调（可选）
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">回调 URL</label>
              <Input
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://your-agent.com/webhook"
              />
            </div>
            {webhookUrl && (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">签名密钥</label>
                <Input
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                  placeholder="用于 HMAC-SHA256 签名验证"
                />
              </div>
            )}
          </div>
        </div>

        {/* 提交 */}
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={onClose}>取消</Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? '创建中...' : '创建调度'}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
