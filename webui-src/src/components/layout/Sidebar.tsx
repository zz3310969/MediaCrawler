import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ListTodo,
  FolderOpen,
  Server,
  Users,
  Settings,
  Bug,
  Clock,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { NAV_ITEMS } from '../../lib/constants';

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  ListTodo,
  FolderOpen,
  Server,
  Users,
  Settings,
  Clock,
};

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-[260px] h-full bg-sidebar border-r border-border flex flex-col">
      {/* Logo 区域 */}
      <div className="p-6 pb-8 space-y-8">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
            <Bug className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-semibold font-display text-text-primary">
            MediaCrawler
          </span>
        </div>

        {/* 导航列表 */}
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = iconMap[item.icon];
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));

            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={cn(
                  'flex items-center gap-3 px-4 h-11 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-white font-medium'
                    : 'text-text-secondary hover:bg-slate-100'
                )}
              >
                {Icon && <Icon className="w-5 h-5" />}
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* 底部用户区域 */}
      <div className="mt-auto p-6 pt-4 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
            <span className="text-sm font-semibold text-white">MC</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary truncate">Admin User</p>
            <p className="text-xs text-text-secondary">管理员</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
