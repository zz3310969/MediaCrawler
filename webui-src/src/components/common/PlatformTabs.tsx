import { cn } from '../../lib/utils';
import { Platform } from '../../types';
import { PLATFORMS } from '../../lib/constants';
import { PlatformIcon } from './PlatformIcon';

export interface PlatformTabsProps {
  value: Platform | 'all';
  onChange: (value: Platform | 'all') => void;
  showAll?: boolean;
  counts?: Record<string, number>;
}

export function PlatformTabs({ value, onChange, showAll = false, counts }: PlatformTabsProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {showAll && (
        <button
          onClick={() => onChange('all')}
          className={cn(
            'flex items-center gap-2 px-4 h-9 rounded-lg text-sm transition-colors',
            value === 'all'
              ? 'bg-primary text-white font-medium'
              : 'text-text-secondary hover:bg-slate-100'
          )}
        >
          <span className="w-2 h-2 rounded-full bg-current" />
          <span>全部平台</span>
          {counts?.all !== undefined && (
            <span className="text-xs opacity-70">{counts.all}</span>
          )}
        </button>
      )}
      
      {PLATFORMS.map((platform) => (
        <button
          key={platform.id}
          onClick={() => onChange(platform.id)}
          className={cn(
            'flex items-center gap-2 px-4 h-9 rounded-lg text-sm transition-colors',
            value === platform.id
              ? 'bg-primary text-white font-medium'
              : 'text-text-secondary hover:bg-slate-100'
          )}
        >
          <PlatformIcon platformId={platform.id} size={16} />
          <span>{platform.name}</span>
          {counts?.[platform.id] !== undefined && (
            <span className="text-xs opacity-70">{counts[platform.id]}</span>
          )}
        </button>
      ))}
    </div>
  );
}
