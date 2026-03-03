import { ReactNode } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface StatCardProps {
  label: string;
  value: string | number;
  change?: {
    value: string;
    trend: 'up' | 'down' | 'stable';
  };
  icon?: ReactNode;
  iconBgColor?: string;
}

export function StatCard({ label, value, change, icon, iconBgColor = 'bg-primary-100' }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg border border-border p-6 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-text-secondary">{label}</span>
        {icon && (
          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', iconBgColor)}>
            {icon}
          </div>
        )}
      </div>
      
      <div className="font-display text-4xl font-semibold text-text-primary">
        {value}
      </div>
      
      {change && (
        <div className="flex items-center gap-1.5">
          {change.trend === 'up' && (
            <ArrowUp className="w-3.5 h-3.5 text-success" />
          )}
          {change.trend === 'down' && (
            <ArrowDown className="w-3.5 h-3.5 text-error" />
          )}
          <span className="text-xs text-text-secondary">{change.value}</span>
        </div>
      )}
    </div>
  );
}
