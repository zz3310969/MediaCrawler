import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Platform } from '../../types';
import { PLATFORMS } from '../../lib/constants';
import { PlatformIcon } from '../common/PlatformIcon';

interface Step1PlatformProps {
  selectedPlatform: Platform | null;
  onSelect: (platform: Platform) => void;
}

export function Step1Platform({ selectedPlatform, onSelect }: Step1PlatformProps) {
  // 将平台分成两行
  const firstRow = PLATFORMS.slice(0, 4);
  const secondRow = PLATFORMS.slice(4);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold font-display text-text-primary">
          选择爬取平台
        </h2>
        <p className="text-sm text-text-secondary">
          选择您要采集数据的社交媒体平台
        </p>
      </div>

      <div className="space-y-5">
        <div className="grid grid-cols-4 gap-5">
          {firstRow.map((platform) => (
            <PlatformCard
              key={platform.id}
              platform={platform}
              isSelected={selectedPlatform === platform.id}
              onSelect={() => onSelect(platform.id)}
            />
          ))}
        </div>
        <div className="grid grid-cols-4 gap-5">
          {secondRow.map((platform) => (
            <PlatformCard
              key={platform.id}
              platform={platform}
              isSelected={selectedPlatform === platform.id}
              onSelect={() => onSelect(platform.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

interface PlatformCardProps {
  platform: {
    id: Platform;
    name: string;
    icon: string;
    description: string;
  };
  isSelected: boolean;
  onSelect: () => void;
}

function PlatformCard({ platform, isSelected, onSelect }: PlatformCardProps) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        'relative flex flex-col items-center gap-4 p-6 rounded-2xl transition-all',
        isSelected
          ? 'bg-primary-50 border-2 border-primary'
          : 'bg-white border border-border hover:border-slate-300'
      )}
    >
      {/* 选中标记 */}
      {isSelected && (
        <div className="absolute top-4 right-4 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
          <Check className="w-3.5 h-3.5 text-white" />
        </div>
      )}

      {/* 图标 */}
      <PlatformIcon
        platformId={platform.id}
        size={64}
        withBackground
        className="rounded-2xl"
      />

      {/* 名称 */}
      <span className="text-base font-semibold text-text-primary">
        {platform.name}
      </span>

      {/* 描述 */}
      <span className="text-sm text-text-secondary text-center">
        {platform.description}
      </span>
    </button>
  );
}
