import { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft, RefreshCw, Loader2 } from 'lucide-react';
import { Modal, Button } from '../common';
import { Platform } from '../../types';
import { PLATFORMS } from '../../lib/constants';
import { crawlerApi, CrawlerStatus } from '../../api/crawler';

interface QRLoginModalProps {
  open: boolean;
  onClose: () => void;
  platform: Platform | null;
  onBack: () => void;
  onSuccess?: () => void;
}

type QRStatus = 'loading' | 'waiting' | 'scanned' | 'success' | 'expired' | 'error';

export function QRLoginModal({ open, onClose, platform, onBack, onSuccess }: QRLoginModalProps) {
  const [status, setStatus] = useState<QRStatus>('loading');
  const [qrcodeImg, setQrcodeImg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedRef = useRef(false);
  const platformInfo = PLATFORMS.find((p) => p.id === platform);

  const cleanup = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const startLogin = useCallback(async () => {
    if (!platform || startedRef.current) return;
    startedRef.current = true;

    setStatus('loading');
    setQrcodeImg(null);
    setErrorMsg('');

    try {
      await crawlerApi.start({
        platform: platform,
        login_type: 'qrcode',
        crawler_type: 'search',
        keywords: 'test',
        headless: true,
        login_only: true,
      });

      pollTimerRef.current = setInterval(async () => {
        try {
          const resp = await crawlerApi.getStatus();
          const data: CrawlerStatus = resp.data;

          if (data.qrcode_img && data.qrcode_img !== qrcodeImg) {
            const img = data.qrcode_img;
            const src = img.startsWith('data:') ? img : `data:image/png;base64,${img}`;
            setQrcodeImg(src);
            setStatus('waiting');
          }

          if (data.new_cookies) {
            cleanup();
            setStatus('success');
            setTimeout(() => {
              onSuccess?.();
            }, 1500);
            return;
          }

          if (data.status === 'idle' && !data.qrcode_img && !data.new_cookies) {
            if (status !== 'loading') {
              cleanup();
              setStatus('expired');
            }
          }
        } catch {
          // 轮询失败忽略
        }
      }, 1000);
    } catch (err: any) {
      setStatus('error');
      setErrorMsg(err?.response?.data?.detail || err?.message || '启动登录失败');
      startedRef.current = false;
    }
  }, [platform, cleanup, onSuccess, qrcodeImg, status]);

  useEffect(() => {
    if (open && platform) {
      startedRef.current = false;
      startLogin();
    }
    return () => {
      cleanup();
      startedRef.current = false;
    };
  }, [open, platform]);

  const handleRefresh = async () => {
    cleanup();
    startedRef.current = false;

    try {
      await crawlerApi.stop();
    } catch {
      // 可能没在运行
    }

    setTimeout(() => startLogin(), 500);
  };

  const handleClose = async () => {
    cleanup();
    startedRef.current = false;
    try {
      await crawlerApi.stop();
    } catch {
      // ignore
    }
    onClose();
  };

  const statusConfig = {
    loading: { icon: <Loader2 className="w-6 h-6 animate-spin" />, text: '正在初始化...', color: 'text-slate-500' },
    waiting: { icon: '⏳', text: '等待扫码...', color: 'text-warning' },
    scanned: { icon: '✅', text: '已扫码，请在手机确认', color: 'text-primary' },
    success: { icon: '🎉', text: '登录成功！', color: 'text-success' },
    expired: { icon: '⚠️', text: '二维码已过期，请刷新', color: 'text-error' },
    error: { icon: '❌', text: errorMsg || '出错了', color: 'text-error' },
  };

  const currentStatus = statusConfig[status];

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={`扫码登录${platformInfo?.name || ''}`}
      width="sm"
      backButton={
        <button
          onClick={() => {
            handleClose();
            onBack();
          }}
          className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-text-secondary" />
        </button>
      }
      footer={
        <div className="w-full flex justify-center">
          <Button variant="secondary" onClick={handleRefresh} disabled={status === 'loading'}>
            <RefreshCw className="w-4 h-4" />
            刷新二维码
          </Button>
        </div>
      }
    >
      <div className="flex flex-col items-center space-y-6 py-4">
        {/* 二维码区域 */}
        <div className="w-[200px] h-[200px] p-4 bg-white border-2 border-slate-200 rounded-2xl flex items-center justify-center">
          {status === 'loading' ? (
            <Loader2 className="w-8 h-8 text-slate-400 animate-spin" />
          ) : qrcodeImg ? (
            <img
              src={qrcodeImg}
              alt="扫码登录二维码"
              className="w-full h-full object-contain rounded-lg"
            />
          ) : (
            <div className="w-full h-full rounded-lg bg-slate-50 flex items-center justify-center">
              <span className="text-sm text-slate-400">等待二维码...</span>
            </div>
          )}
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
