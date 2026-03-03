import { useState, useEffect } from 'react';
import { User, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Platform } from '../../types';
import { getActiveAccountsByPlatform } from '../../api/accounts';
import { PLATFORMS } from '../../lib/constants';

interface AccountItem {
  account_id: string;
  platform: string;
  username?: string;
  nickname?: string;
  avatar?: string;
  status: string;
  login_method: string;
  cookie_valid: number;
  remark?: string;
}

interface StepAccountProps {
  platform: Platform;
  selectedAccountId: string | null;
  onSelect: (accountId: string | null) => void;
}

export function StepAccount({ platform, selectedAccountId, onSelect }: StepAccountProps) {
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const platformInfo = PLATFORMS.find((p) => p.id === platform);

  const fetchAccounts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getActiveAccountsByPlatform(platform);
      setAccounts(data.items || []);
    } catch (err: any) {
      setError(err?.message || '获取账号列表失败');
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [platform]);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold font-display text-text-primary">
          选择账号
        </h2>
        <p className="text-sm text-text-secondary">
          选择用于 {platformInfo?.name} 爬取的登录账号，账号需在「账号管理」中提前配置 Cookie
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button
            onClick={fetchAccounts}
            className="ml-auto flex items-center gap-1 text-amber-600 hover:text-amber-800"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            重试
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="w-6 h-6 text-text-secondary animate-spin" />
            <span className="text-sm text-text-secondary">加载账号列表...</span>
          </div>
        </div>
      ) : accounts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center">
            <User className="w-7 h-7 text-text-secondary" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-text-primary">
              暂无可用的 {platformInfo?.name} 账号
            </p>
            <p className="text-xs text-text-secondary">
              请先到「账号管理」页面添加账号并配置 Cookie
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* 跳过选项 */}
          <button
            onClick={() => onSelect(null)}
            className={cn(
              'w-full flex items-center gap-4 p-4 rounded-lg border-2 transition-all text-left',
              selectedAccountId === null
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-slate-300'
            )}
          >
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-text-secondary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary">不选择账号</p>
              <p className="text-xs text-text-secondary">使用本地已保存的登录状态（需先通过命令行登录过）</p>
            </div>
            {selectedAccountId === null && (
              <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
            )}
          </button>

          {/* 账号列表 */}
          <div className="grid grid-cols-2 gap-3">
            {accounts.map((account) => (
              <button
                key={account.account_id}
                onClick={() => onSelect(account.account_id)}
                className={cn(
                  'flex items-center gap-3 p-4 rounded-lg border-2 transition-all text-left',
                  selectedAccountId === account.account_id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-slate-300'
                )}
              >
                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0 overflow-hidden">
                  {account.avatar ? (
                    <img src={account.avatar} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <User className="w-5 h-5 text-text-secondary" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {account.nickname || account.username || account.account_id.slice(0, 8)}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={cn(
                      'inline-flex items-center gap-1 text-xs',
                      account.cookie_valid ? 'text-green-600' : 'text-amber-600'
                    )}>
                      <span className={cn(
                        'w-1.5 h-1.5 rounded-full',
                        account.cookie_valid ? 'bg-green-500' : 'bg-amber-500'
                      )} />
                      {account.cookie_valid ? 'Cookie 有效' : 'Cookie 待验证'}
                    </span>
                    {account.remark && (
                      <span className="text-xs text-text-secondary truncate">· {account.remark}</span>
                    )}
                  </div>
                </div>
                {selectedAccountId === account.account_id && (
                  <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
