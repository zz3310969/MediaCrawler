import { cn } from '../../lib/utils';
import { TaskStatus } from '../../types';

interface TabItem {
  id: TaskStatus | 'all';
  label: string;
  count: number;
  variant?: 'default' | 'error';
}

interface TaskTabsProps {
  activeTab: TaskStatus | 'all';
  onChange: (tab: TaskStatus | 'all') => void;
  counts: {
    all: number;
    running: number;
    completed: number;
    failed: number;
    pending?: number;
  };
}

export function TaskTabs({ activeTab, onChange, counts }: TaskTabsProps) {
  const tabs: TabItem[] = [
    { id: 'all', label: '全部任务', count: counts.all },
    { id: 'running', label: '运行中', count: counts.running },
    { id: 'completed', label: '已完成', count: counts.completed },
    { id: 'failed', label: '失败', count: counts.failed, variant: 'error' },
  ];

  return (
    <div className="flex items-center border-b border-border">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            'flex items-center gap-2 px-5 py-3 text-sm transition-colors',
            activeTab === tab.id
              ? 'text-primary font-medium border-b-2 border-primary -mb-px'
              : 'text-text-secondary hover:text-text-primary'
          )}
        >
          {tab.label}
          <span
            className={cn(
              'px-2 py-0.5 rounded-full text-xs font-medium',
              activeTab === tab.id
                ? tab.variant === 'error'
                  ? 'bg-error-100 text-error'
                  : 'bg-primary-100 text-primary'
                : tab.variant === 'error'
                ? 'bg-error-100 text-error'
                : 'bg-slate-100 text-text-secondary'
            )}
          >
            {tab.count}
          </span>
        </button>
      ))}
    </div>
  );
}
