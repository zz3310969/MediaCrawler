import { PLATFORMS } from '../../lib/constants';
import { PlatformStats } from '../../types';
import { PlatformIcon } from '../common/PlatformIcon';

interface PlatformSupportProps {
  stats?: PlatformStats[];
}

export function PlatformSupport({ stats }: PlatformSupportProps) {
  // 将平台分成两行
  const firstRow = PLATFORMS.slice(0, 4);
  const secondRow = PLATFORMS.slice(4);

  const getStats = (platformId: string) => {
    return stats?.find((s) => s.platform === platformId);
  };

  return (
    <div className="bg-white rounded-lg border border-border p-5 space-y-4">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold font-display text-text-primary">支持平台</h3>
        <span className="text-xs text-text-secondary">共 {PLATFORMS.length} 个平台</span>
      </div>

      {/* 平台网格 */}
      <div className="space-y-3">
        <div className="grid grid-cols-4 gap-3">
          {firstRow.map((platform) => {
            const platformStats = getStats(platform.id);
            return (
              <div
                key={platform.id}
                className="flex flex-col items-center gap-2 p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <PlatformIcon platformId={platform.id} size={44} withBackground />
                <span className="text-xs font-medium text-text-primary">{platform.name}</span>
                {platformStats && (
                  <span className="text-xs text-text-secondary">
                    {platformStats.task_count} 任务
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div className="grid grid-cols-4 gap-3">
          {secondRow.map((platform) => {
            const platformStats = getStats(platform.id);
            return (
              <div
                key={platform.id}
                className="flex flex-col items-center gap-2 p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <PlatformIcon platformId={platform.id} size={44} withBackground />
                <span className="text-xs font-medium text-text-primary">{platform.name}</span>
                {platformStats && (
                  <span className="text-xs text-text-secondary">
                    {platformStats.task_count} 任务
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
