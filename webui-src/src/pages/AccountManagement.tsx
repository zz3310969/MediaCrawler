import { useState, useMemo } from 'react';
import { Plus, Loader2 } from 'lucide-react';
import { PageHeader } from '../components/layout';
import { StatCard, Button, PlatformTabs } from '../components/common';
import { AccountTable, AddAccountModal, QRLoginModal } from '../components/accounts';
import { Account, Platform, LoginMethod } from '../types';
import { useAccounts, useDeleteAccount, useValidateAccount } from '../hooks';

export function AccountManagement() {
  const [activePlatform, setActivePlatform] = useState<Platform | 'all'>('all');
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);

  // 获取账号列表
  const { data: accountsData, loading, error, refetch } = useAccounts({
    platform: activePlatform === 'all' ? undefined : activePlatform,
    page: 1,
    page_size: 100,
  });

  // 账号操作
  const { mutate: deleteAccount } = useDeleteAccount();
  const { mutate: validateAccount } = useValidateAccount();

  const accounts = accountsData?.items || [];

  // 计算统计数据
  const stats = useMemo(() => ({
    total: accountsData?.total || accounts.length,
    active: accounts.filter((a) => a.status === 'active').length,
    inactive: accounts.filter((a) => a.status === 'inactive' || a.status === 'expired').length,
    banned: accounts.filter((a) => a.status === 'banned').length,
  }), [accounts, accountsData?.total]);

  // 按平台统计
  const platformCounts = useMemo(() => {
    const counts: Record<string, number> = { all: accountsData?.total || accounts.length };
    accounts.forEach((account) => {
      counts[account.platform] = (counts[account.platform] || 0) + 1;
    });
    return counts;
  }, [accounts, accountsData?.total]);

  const handleAddAccount = (platform: Platform, method: LoginMethod) => {
    setSelectedPlatform(platform);
    setAddModalOpen(false);
    
    if (method === 'qrcode') {
      setQrModalOpen(true);
    }
  };

  const handleEdit = (account: Account) => {
    console.log('Edit account:', account);
    // TODO: 打开编辑弹窗
  };

  const handleDelete = async (account: Account) => {
    if (window.confirm(`确定要删除账号 ${account.nickname || account.username} 吗？`)) {
      try {
        await deleteAccount(account.account_id);
        refetch();
      } catch (err) {
        console.error('Delete account failed:', err);
      }
    }
  };

  const handleRelogin = (account: Account) => {
    setSelectedPlatform(account.platform);
    setQrModalOpen(true);
  };

  const handleVerify = async (account: Account) => {
    try {
      await validateAccount(account.account_id);
      refetch();
    } catch (err) {
      console.error('Validate account failed:', err);
    }
  };

  // 加载状态
  if (loading && accounts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
          <p className="text-text-secondary">加载账号列表...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error && accounts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <p className="text-error">加载失败: {error.message}</p>
          <Button onClick={() => refetch()}>重试</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-50 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* 页面头部 */}
        <PageHeader
          title="账号池管理"
          subtitle="管理各平台爬虫账号，支持多种登录方式"
          actions={
            <Button onClick={() => setAddModalOpen(true)}>
              <Plus className="w-4 h-4" />
              添加账号
            </Button>
          }
        />

        {/* 统计卡片 */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            label="总账号数"
            value={stats.total}
          />
          <StatCard
            label="正常账号"
            value={stats.active}
            change={{ 
              value: stats.total > 0 ? `${Math.round((stats.active / stats.total) * 100)}%` : '0%', 
              trend: 'stable' 
            }}
          />
          <StatCard
            label="失效账号"
            value={stats.inactive}
            change={{ value: stats.inactive > 0 ? '需处理' : '无', trend: stats.inactive > 0 ? 'down' : 'stable' }}
          />
          <StatCard
            label="已封禁"
            value={stats.banned}
            change={{ value: stats.banned > 0 ? '需处理' : '无', trend: stats.banned > 0 ? 'down' : 'stable' }}
          />
        </div>

        {/* 平台筛选 */}
        <div className="py-2">
          <PlatformTabs
            value={activePlatform}
            onChange={(value) => setActivePlatform(value)}
            showAll
            counts={platformCounts}
          />
        </div>

        {/* 账号列表 */}
        {accounts.length > 0 ? (
          <AccountTable
            accounts={accounts}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRelogin={handleRelogin}
            onVerify={handleVerify}
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-lg border border-border">
            <p className="text-text-secondary mb-4">暂无账号</p>
            <Button onClick={() => setAddModalOpen(true)}>
              <Plus className="w-4 h-4" />
              添加账号
            </Button>
          </div>
        )}
      </div>

      {/* 添加账号弹窗 */}
      <AddAccountModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSubmit={handleAddAccount}
      />

      {/* 扫码登录弹窗 */}
      <QRLoginModal
        open={qrModalOpen}
        onClose={() => setQrModalOpen(false)}
        platform={selectedPlatform}
        onBack={() => {
          setQrModalOpen(false);
          setAddModalOpen(true);
        }}
        onSuccess={() => {
          setQrModalOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
