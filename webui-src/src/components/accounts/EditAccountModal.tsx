import { useState, useEffect } from 'react';
import { Modal, Button } from '../common';
import { Account, AccountUpdateRequest, AccountStatus } from '../../types';
import { PLATFORMS, ACCOUNT_STATUS_CONFIG } from '../../lib/constants';
import { updateAccount } from '../../api/accounts';

interface EditAccountModalProps {
  open: boolean;
  onClose: () => void;
  account: Account | null;
  onSuccess: () => void;
}

const STATUS_OPTIONS: { value: AccountStatus; label: string }[] = [
  { value: 'active', label: '正常' },
  { value: 'inactive', label: '失效' },
  { value: 'expired', label: '已过期' },
  { value: 'banned', label: '已封禁' },
];

export function EditAccountModal({ open, onClose, account, onSuccess }: EditAccountModalProps) {
  const [nickname, setNickname] = useState('');
  const [status, setStatus] = useState<AccountStatus>('active');
  const [cookies, setCookies] = useState('');
  const [remark, setRemark] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (account && open) {
      setNickname(account.nickname || '');
      setStatus(account.status);
      setCookies('');
      setRemark(account.remark || '');
      setError('');
    }
  }, [account, open]);

  if (!account) return null;

  const platform = PLATFORMS.find((p) => p.id === account.platform);
  const currentStatusConfig = ACCOUNT_STATUS_CONFIG[account.status] || ACCOUNT_STATUS_CONFIG['inactive'];

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const data: AccountUpdateRequest = {};
      if (nickname !== (account.nickname || '')) data.nickname = nickname;
      if (status !== account.status) data.status = status;
      if (cookies.trim()) data.cookies = cookies.trim();
      if (remark !== (account.remark || '')) data.remark = remark;

      if (Object.keys(data).length === 0) {
        onClose();
        return;
      }

      await updateAccount(account.account_id, data);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="编辑账号"
      width="md"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} className="flex-1">
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving} className="flex-1">
            {saving ? '保存中...' : '保存'}
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* 账号基本信息（只读） */}
        <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
          <span className="text-xl">{platform?.icon}</span>
          <div>
            <p className="text-sm font-medium text-text-primary">{platform?.name}</p>
            <p className="text-xs text-text-secondary">
              {account.username ? `@${account.username}` : `ID: ${account.account_id.slice(0, 8)}...`}
            </p>
          </div>
          <span className={`ml-auto px-2.5 py-1 rounded-full text-xs font-medium ${currentStatusConfig.bgColor} ${currentStatusConfig.textColor}`}>
            {currentStatusConfig.label}
          </span>
        </div>

        {/* 昵称 */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-text-primary">昵称</label>
          <input
            type="text"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="输入昵称"
            className="w-full h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>

        {/* 状态 */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-text-primary">状态</label>
          <div className="flex gap-2">
            {STATUS_OPTIONS.map((opt) => {
              const cfg = ACCOUNT_STATUS_CONFIG[opt.value];
              const selected = status === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => setStatus(opt.value)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    selected
                      ? `${cfg.bgColor} ${cfg.textColor} border-current`
                      : 'bg-white text-text-secondary border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Cookie */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-text-primary">
            Cookie
            <span className="text-xs text-text-secondary font-normal ml-2">留空则不修改</span>
          </label>
          <textarea
            value={cookies}
            onChange={(e) => setCookies(e.target.value)}
            placeholder="粘贴新的 Cookie 以更新..."
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary font-mono"
          />
        </div>

        {/* 备注 */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-text-primary">备注</label>
          <input
            type="text"
            value={remark}
            onChange={(e) => setRemark(e.target.value)}
            placeholder="输入备注信息"
            className="w-full h-10 px-3 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>

        {/* 错误提示 */}
        {error && (
          <p className="text-sm text-error bg-error-50 px-3 py-2 rounded-lg">{error}</p>
        )}
      </div>
    </Modal>
  );
}
