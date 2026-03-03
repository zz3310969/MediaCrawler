import { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import { Modal, Button } from '../common';
import { Platform } from '../../types';
import { PLATFORMS } from '../../lib/constants';

interface QRLoginModalProps {
  open: boolean;
  onClose: () => void;
  platform: Platform | null;
  onBack: () => void;
  onSuccess?: () => void;
}

type QRStatus = 'loading' | 'waiting' | 'scanned' | 'success' | 'expired';

export function QRLoginModal({ open, onClose, platform, onBack, onSuccess: _onSuccess }: QRLoginModalProps) {
  const [status, setStatus] = useState<QRStatus>('loading');
  const platformInfo = PLATFORMS.find((p) => p.id === platform);

  // 模拟二维码加载
  useEffect(() => {
    if (open) {
      setStatus('loading');
      const timer = setTimeout(() => setStatus('waiting'), 1000);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const handleRefresh = () => {
    setStatus('loading');
    setTimeout(() => setStatus('waiting'), 1000);
  };

  const statusConfig = {
    loading: { icon: <Loader2 className="w-6 h-6 animate-spin" />, text: '加载中...', color: 'text-slate-500' },
    waiting: { icon: '⏳', text: '等待扫码...', color: 'text-warning' },
    scanned: { icon: '✅', text: '已扫码，请在手机确认', color: 'text-primary' },
    success: { icon: '🎉', text: '登录成功！', color: 'text-success' },
    expired: { icon: '⚠️', text: '二维码已过期', color: 'text-error' },
  };

  const currentStatus = statusConfig[status];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`扫码登录${platformInfo?.name || ''}`}
      width="sm"
      backButton={
        <button
          onClick={onBack}
          className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-text-secondary" />
        </button>
      }
      footer={
        <div className="w-full flex justify-center">
          <Button variant="secondary" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4" />
            刷新二维码
          </Button>
        </div>
      }
    >
      <div className="flex flex-col items-center space-y-6 py-4">
        {/* 二维码区域 */}
        <div className="w-[200px] h-[200px] p-4 bg-white border-2 border-slate-200 rounded-2xl flex items-center justify-center">
          <div className="w-full h-full rounded-lg bg-slate-50 flex items-center justify-center">
            {status === 'loading' ? (
              <Loader2 className="w-8 h-8 text-slate-400 animate-spin" />
            ) : (
              <span className="text-5xl">📱</span>
            )}
          </div>
        </div>

        {/* 说明文字 */}
        <div className="text-center space-y-2">
          <p className="text-base font-medium text-text-primary">
            请使用{platformInfo?.name}APP扫码
          </p>
          <p className="text-sm text-text-secondary">
            打开{platformInfo?.name}APP → 我 → 设置 → 扫一扫
          </p>
        </div>

        {/* 状态提示 */}
        <div className={`flex items-center gap-2 px-5 py-3 rounded-lg bg-warning-100 ${currentStatus.color}`}>
          <span>{typeof currentStatus.icon === 'string' ? currentStatus.icon : currentStatus.icon}</span>
          <span className="text-sm font-medium">{currentStatus.text}</span>
        </div>

        {/* 温馨提示 */}
        <div className="w-full p-4 bg-slate-50 rounded-lg space-y-2">
          <p className="text-xs font-medium text-text-secondary">💡 温馨提示</p>
          <ul className="space-y-1 text-xs text-slate-400">
            <li>• 二维码有效期为5分钟，超时请点击"刷新"</li>
            <li>• 请确保手机和电脑在同一网络环境</li>
            <li>• 扫码成功后请在手机端确认登录</li>
          </ul>
        </div>
      </div>
    </Modal>
  );
}
