import { Pencil, Trash2 } from 'lucide-react';
import { Account } from '../../types';
import { PLATFORMS, ACCOUNT_STATUS_CONFIG, LOGIN_METHOD_CONFIG } from '../../lib/constants';
import { formatRelativeTime, cn } from '../../lib/utils';

interface AccountTableProps {
  accounts: Account[];
  onEdit: (account: Account) => void;
  onDelete: (account: Account) => void;
}

export function AccountTable({ accounts, onEdit, onDelete }: AccountTableProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      {/* 表头 */}
      <div className="flex items-center h-[52px] px-5 border-b border-border bg-white">
        <div className="w-[100px] text-xs font-medium text-text-secondary">平台</div>
        <div className="flex-1 text-xs font-medium text-text-secondary">账号信息</div>
        <div className="w-[100px] text-xs font-medium text-text-secondary">登录方式</div>
        <div className="w-[80px] text-xs font-medium text-text-secondary">状态</div>
        <div className="w-[120px] text-xs font-medium text-text-secondary">最后使用</div>
        <div className="w-[120px] text-xs font-medium text-text-secondary text-center">操作</div>
      </div>

      {/* 表格内容 */}
      {accounts.map((account) => {
        const platform = PLATFORMS.find((p) => p.id === account.platform);
        const statusConfig = ACCOUNT_STATUS_CONFIG[account.status] || ACCOUNT_STATUS_CONFIG['inactive'];
        const methodConfig = LOGIN_METHOD_CONFIG[account.login_method] || LOGIN_METHOD_CONFIG['cookie'];
        const isError = account.status === 'inactive' || account.status === 'expired' || account.status === 'banned';
        const isPending = account.cookie_valid === 0 && account.status === 'active';

        return (
          <div
            key={account.account_id}
            className={cn(
              'flex items-center h-16 px-5 border-b border-slate-100 last:border-b-0',
              isError && 'bg-error-50 border-error-200',
              isPending && 'bg-warning-50 border-warning-200'
            )}
          >
            {/* 平台 */}
            <div className="w-[100px] flex items-center gap-2">
              <span>{platform?.icon}</span>
              <span className="text-sm text-text-primary">{platform?.name}</span>
            </div>

            {/* 账号信息 */}
            <div className="flex-1 flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-full flex-shrink-0"
                style={{ backgroundColor: getAvatarColor(account.account_id) }}
              >
                {account.avatar && (
                  <img
                    src={account.avatar}
                    alt={account.nickname}
                    className="w-full h-full rounded-full object-cover"
                  />
                )}
              </div>
              <div className="space-y-0.5">
                <p className="text-sm font-medium text-text-primary">{account.nickname}</p>
                <p className="text-xs text-text-secondary">@{account.username}</p>
              </div>
            </div>

            {/* 登录方式 */}
            <div className="w-[100px]">
              <span className={cn('px-2.5 py-1 rounded text-xs', methodConfig.bgColor)}>
                {methodConfig.label}
              </span>
            </div>

            {/* 状态 */}
            <div className="w-[80px]">
              <span className={cn(
                'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium',
                statusConfig.bgColor,
                statusConfig.textColor
              )}>
                {statusConfig.label}
              </span>
            </div>

            {/* 最后使用 */}
            <div className="w-[120px]">
              <span className={cn(
                'text-xs',
                isError ? 'text-error' : 'text-text-secondary'
              )}>
                {account.last_used_at ? formatRelativeTime(new Date(account.last_used_at * 1000)) : '-'}
              </span>
            </div>

            {/* 操作 */}
            <div className="w-[120px] flex items-center justify-center gap-2">
              <button
                onClick={() => onEdit(account)}
                className="w-8 h-8 flex items-center justify-center rounded-md border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                <Pencil className="w-4 h-4 text-text-secondary" />
              </button>
              <button
                onClick={() => onDelete(account)}
                className="w-8 h-8 flex items-center justify-center rounded-md border border-error-200 hover:bg-error-50 transition-colors"
              >
                <Trash2 className="w-4 h-4 text-error" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function getAvatarColor(id: string): string {
  const colors = ['#FEE2E2', '#DBEAFE', '#E0E7FF', '#FEF3C7', '#D1FAE5'];
  const index = id.charCodeAt(0) % colors.length;
  return colors[index];
}
