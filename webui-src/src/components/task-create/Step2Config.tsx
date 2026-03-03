import { Check } from 'lucide-react';
import { Input, Select } from '../common';
import { Switch } from '../common';
import { cn } from '../../lib/utils';
import { Platform, TaskConfig } from '../../types';
import {
  CRAWL_MODE_OPTIONS,
  PLATFORM_CRAWL_MODES,
  PLATFORM_FIELDS,
  PlatformFieldDef,
  PLATFORMS,
} from '../../lib/constants';

const DATA_OPTIONS = [
  { value: 'enable_comments', label: '评论数据' },
  { value: 'enable_media', label: '媒体文件' },
];

interface Step2ConfigProps {
  platform: Platform;
  config: Partial<TaskConfig>;
  onChange: (config: Partial<TaskConfig>) => void;
}

function parseTextareaToList(text: string): string[] {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
}

function listToTextarea(list?: string[]): string {
  return list?.join('\n') || '';
}

function PlatformField({
  field,
  config,
  onChange,
}: {
  field: PlatformFieldDef;
  config: Partial<TaskConfig>;
  onChange: (updates: Partial<TaskConfig>) => void;
}) {
  const value = (config as Record<string, unknown>)[field.key];

  if (field.type === 'select' && field.options) {
    return (
      <Select
        label={field.label}
        options={field.options}
        value={(value as string) ?? field.defaultValue ?? ''}
        onChange={(e) => onChange({ [field.key]: e.target.value })}
      />
    );
  }

  if (field.type === 'textarea') {
    const textValue =
      Array.isArray(value) ? listToTextarea(value as string[]) : (value as string) ?? '';
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-text-primary">{field.label}</label>
        <textarea
          className={cn(
            'w-full min-h-[120px] px-4 py-3 rounded-lg bg-slate-50 border border-slate-200',
            'text-sm text-text-primary placeholder:text-slate-400',
            'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
            'transition-colors resize-y'
          )}
          placeholder={field.placeholder}
          value={textValue}
          onChange={(e) => {
            const list = parseTextareaToList(e.target.value);
            if (field.key === 'note_urls' || field.key === 'creator_ids' || field.key === 'vip_creator_ids') {
              onChange({ [field.key]: list });
            } else {
              onChange({ [field.key]: e.target.value });
            }
          }}
        />
        {field.hint && <p className="text-xs text-text-secondary">{field.hint}</p>}
      </div>
    );
  }

  if (field.type === 'switch') {
    const checked = (value as boolean) ?? (field.defaultValue as boolean) ?? false;
    return (
      <div className="flex items-center justify-between py-2">
        <div className="space-y-0.5">
          <label className="block text-sm font-medium text-text-primary">{field.label}</label>
          {field.hint && <p className="text-xs text-text-secondary">{field.hint}</p>}
        </div>
        <Switch checked={checked} onChange={(val) => onChange({ [field.key]: val })} />
      </div>
    );
  }

  if (field.type === 'number') {
    return (
      <Input
        label={field.label}
        type="number"
        placeholder={field.placeholder}
        value={(value as number) ?? field.defaultValue ?? ''}
        onChange={(e) => onChange({ [field.key]: parseFloat(e.target.value) })}
      />
    );
  }

  return (
    <Input
      label={field.label}
      placeholder={field.placeholder}
      value={(value as string) ?? field.defaultValue ?? ''}
      onChange={(e) => onChange({ [field.key]: e.target.value })}
    />
  );
}

export function Step2Config({ platform, config, onChange }: Step2ConfigProps) {
  const supportedModes = PLATFORM_CRAWL_MODES[platform] || ['search'];
  const filteredModeOptions = CRAWL_MODE_OPTIONS.filter((opt) => supportedModes.includes(opt.value));
  const platformInfo = PLATFORMS.find((p) => p.id === platform);

  const crawlerType = config.crawler_type || 'search';
  const platformFields = (PLATFORM_FIELDS[platform] || []).filter(
    (f) => !f.showWhen || f.showWhen.includes(crawlerType)
  );

  const handleCrawlerTypeChange = (newType: string) => {
    const updates: Partial<TaskConfig> = { crawler_type: newType as TaskConfig['crawler_type'] };
    if (newType !== 'search') {
      updates.keywords = [];
    }
    onChange(updates);
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{platformInfo?.icon}</span>
          <div>
            <h2 className="text-2xl font-semibold font-display text-text-primary">
              配置爬取参数
            </h2>
            <p className="text-sm text-text-secondary">
              {platformInfo?.name} - 设置数据采集的范围和类型
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        {/* 左列 - 基础配置 */}
        <div className="space-y-6">
          <Select
            label="采集模式"
            options={filteredModeOptions}
            value={crawlerType}
            onChange={(e) => handleCrawlerTypeChange(e.target.value)}
          />

          {crawlerType === 'search' && (
            <Input
              label="关键词"
              placeholder="输入搜索关键词，多个用逗号分隔"
              value={config.keywords?.join(', ') || ''}
              onChange={(e) =>
                onChange({
                  keywords: e.target.value
                    .split(',')
                    .map((k) => k.trim())
                    .filter(Boolean),
                })
              }
            />
          )}

          <Input
            label="采集数量"
            type="number"
            placeholder="100"
            value={config.max_notes || ''}
            onChange={(e) => onChange({ max_notes: parseInt(e.target.value) || 100 })}
          />

          {/* 平台特有字段 - textarea 类型放在左列 */}
          {platformFields
            .filter((f) => f.type === 'textarea')
            .map((field) => (
              <PlatformField key={field.key} field={field} config={config} onChange={onChange} />
            ))}
        </div>

        {/* 右列 - 高级配置 */}
        <div className="space-y-6">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text-primary">数据选项</label>
            <div className="grid grid-cols-2 gap-3">
              {DATA_OPTIONS.map((option) => {
                const isSelected =
                  option.value === 'enable_comments'
                    ? config.enable_comments
                    : config.enable_media;
                return (
                  <button
                    key={option.value}
                    onClick={() =>
                      onChange({
                        [option.value]: !isSelected,
                      })
                    }
                    className={cn(
                      'flex items-center gap-2 px-4 py-3 rounded-lg border transition-colors',
                      isSelected
                        ? 'bg-primary-50 border-primary text-primary'
                        : 'bg-white border-slate-200 text-text-secondary hover:border-slate-300'
                    )}
                  >
                    <div
                      className={cn(
                        'w-5 h-5 rounded flex items-center justify-center border',
                        isSelected ? 'bg-primary border-primary' : 'border-slate-300'
                      )}
                    >
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <span className="text-sm">{option.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <Select
            label="存储方式"
            options={[
              { value: 'db', label: 'MySQL 数据库' },
              { value: 'sqlite', label: 'SQLite 数据库' },
              { value: 'postgres', label: 'PostgreSQL 数据库' },
              { value: 'json', label: 'JSON 文件' },
              { value: 'csv', label: 'CSV 文件' },
              { value: 'excel', label: 'Excel 文件' },
            ]}
            value={config.save_option || 'db'}
            onChange={(e) => onChange({ save_option: e.target.value as TaskConfig['save_option'] })}
          />

          <Input
            label="并发数"
            type="number"
            placeholder="3"
            value={config.concurrency || ''}
            onChange={(e) => onChange({ concurrency: parseInt(e.target.value) || 3 })}
          />

          <Input
            label="请求间隔 (秒)"
            type="number"
            placeholder="1.0"
            value={config.crawl_interval || ''}
            onChange={(e) => onChange({ crawl_interval: parseFloat(e.target.value) || 1.0 })}
          />

          {/* 平台特有字段 - select/switch/number 类型放在右列 */}
          {platformFields
            .filter((f) => f.type !== 'textarea')
            .map((field) => (
              <PlatformField key={field.key} field={field} config={config} onChange={onChange} />
            ))}
        </div>
      </div>
    </div>
  );
}
