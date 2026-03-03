import { Check } from 'lucide-react';
import { Input, Select } from '../common';
import { cn } from '../../lib/utils';
import { TaskConfig } from '../../types';
import { CRAWL_MODE_OPTIONS } from '../../lib/constants';

// 数据类型选项（用于UI显示）
const DATA_OPTIONS = [
  { value: 'enable_comments', label: '评论数据' },
  { value: 'enable_media', label: '媒体文件' },
];

interface Step2ConfigProps {
  config: Partial<TaskConfig>;
  onChange: (config: Partial<TaskConfig>) => void;
}

export function Step2Config({ config, onChange }: Step2ConfigProps) {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold font-display text-text-primary">
          配置爬取参数
        </h2>
        <p className="text-sm text-text-secondary">
          设置数据采集的范围和类型
        </p>
      </div>

      <div className="grid grid-cols-2 gap-8">
        {/* 左列 */}
        <div className="space-y-6">
          <Select
            label="采集模式"
            options={CRAWL_MODE_OPTIONS}
            value={config.crawler_type || 'search'}
            onChange={(e) => onChange({ crawler_type: e.target.value as TaskConfig['crawler_type'] })}
          />

          <Input
            label="关键词"
            placeholder="输入搜索关键词，多个用逗号分隔"
            value={config.keywords?.join(', ') || ''}
            onChange={(e) => onChange({ keywords: e.target.value.split(',').map(k => k.trim()).filter(Boolean) })}
          />

          <Input
            label="采集数量"
            type="number"
            placeholder="100"
            value={config.max_notes || ''}
            onChange={(e) => onChange({ max_notes: parseInt(e.target.value) || 100 })}
          />
        </div>

        {/* 右列 */}
        <div className="space-y-6">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text-primary">
              数据选项
            </label>
            <div className="grid grid-cols-2 gap-3">
              {DATA_OPTIONS.map((option) => {
                const isSelected = option.value === 'enable_comments' 
                  ? config.enable_comments 
                  : config.enable_media;
                return (
                  <button
                    key={option.value}
                    onClick={() => onChange({ 
                      [option.value]: !isSelected 
                    })}
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
                        isSelected
                          ? 'bg-primary border-primary'
                          : 'border-slate-300'
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
        </div>
      </div>
    </div>
  );
}
