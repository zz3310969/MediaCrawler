import { useState } from 'react';
import { Check, QrCode, Cookie, Smartphone } from 'lucide-react';
import { Modal, Button, PlatformIcon } from '../common';
import { cn } from '../../lib/utils';
import { Platform, LoginMethod } from '../../types';
import { PLATFORMS } from '../../lib/constants';

interface AddAccountModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (platform: Platform, method: LoginMethod) => void;
}

export function AddAccountModal({ open, onClose, onSubmit }: AddAccountModalProps) {
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<LoginMethod | null>('qrcode');

  const handleNext = () => {
    if (selectedPlatform && selectedMethod) {
      onSubmit(selectedPlatform, selectedMethod);
    }
  };

  const handleClose = () => {
    setSelectedPlatform(null);
    setSelectedMethod('qrcode');
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="添加新账号"
      width="lg"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            取消
          </Button>
          <Button onClick={handleNext} disabled={!selectedPlatform || !selectedMethod}>
            下一步
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {/* 步骤1: 选择平台 */}
        <div className="space-y-3">
          <p className="text-sm text-text-secondary">步骤 1：选择平台</p>
          <div className="grid grid-cols-4 gap-3">
            {PLATFORMS.slice(0, 4).map((platform) => (
              <button
                key={platform.id}
                onClick={() => setSelectedPlatform(platform.id)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-xl border transition-colors',
                  selectedPlatform === platform.id
                    ? 'bg-primary-50 border-primary'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                )}
              >
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center overflow-hidden"
                  style={{ backgroundColor: platform.color + '20' }}
                >
                  <PlatformIcon platformId={platform.id} size={22} />
                </div>
                <span className="text-sm font-medium text-text-primary">
                  {platform.name}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* 步骤2: 选择登录方式 */}
        <div className="space-y-3">
          <p className="text-sm text-text-secondary">步骤 2：选择登录方式</p>
          <div className="space-y-3">
            <MethodOption
              icon={<QrCode className="w-5 h-5 text-primary" />}
              iconBg="bg-primary-100"
              title="扫码登录"
              description="使用APP扫描二维码登录，安全便捷"
              badge="推荐"
              isSelected={selectedMethod === 'qrcode'}
              onSelect={() => setSelectedMethod('qrcode')}
            />
            <MethodOption
              icon={<Cookie className="w-5 h-5 text-purple-500" />}
              iconBg="bg-purple-100"
              title="Cookie导入"
              description="手动导入浏览器Cookie登录"
              isSelected={selectedMethod === 'cookie'}
              onSelect={() => setSelectedMethod('cookie')}
            />
            <MethodOption
              icon={<Smartphone className="w-5 h-5 text-warning" />}
              iconBg="bg-warning-100"
              title="手机验证"
              description="通过手机号和验证码登录"
              isSelected={selectedMethod === 'phone'}
              onSelect={() => setSelectedMethod('phone')}
            />
          </div>
        </div>
      </div>
    </Modal>
  );
}

interface MethodOptionProps {
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  description: string;
  badge?: string;
  isSelected: boolean;
  onSelect: () => void;
}

function MethodOption({ icon, iconBg, title, description, badge, isSelected, onSelect }: MethodOptionProps) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        'flex items-center gap-4 w-full p-4 rounded-xl border transition-colors text-left',
        isSelected
          ? 'bg-primary-50 border-primary'
          : 'bg-white border-slate-200 hover:border-slate-300'
      )}
    >
      <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', iconBg)}>
        {icon}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary">{title}</span>
          {badge && (
            <span className="px-2 py-0.5 rounded text-xs bg-success-100 text-success font-medium">
              {badge}
            </span>
          )}
        </div>
        <p className="text-xs text-text-secondary mt-1">{description}</p>
      </div>
      {isSelected && (
        <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
          <Check className="w-3 h-3 text-white" />
        </div>
      )}
    </button>
  );
}
