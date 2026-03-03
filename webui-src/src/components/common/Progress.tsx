import { cn } from '../../lib/utils';

export interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  color?: 'primary' | 'success' | 'warning' | 'error';
  showLabel?: boolean;
}

export function Progress({
  value,
  max = 100,
  size = 'md',
  color = 'primary',
  showLabel = false,
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  
  return (
    <div className="w-full space-y-2">
      {showLabel && (
        <div className="flex justify-between text-xs text-text-secondary">
          <span>进度</span>
          <span>{Math.round(percentage)}%</span>
        </div>
      )}
      <div
        className={cn(
          'w-full bg-slate-100 rounded-full overflow-hidden',
          {
            'h-1': size === 'sm',
            'h-2': size === 'md',
            'h-3': size === 'lg',
          }
        )}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300',
            {
              'bg-primary': color === 'primary',
              'bg-success': color === 'success',
              'bg-warning': color === 'warning',
              'bg-error': color === 'error',
            }
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
