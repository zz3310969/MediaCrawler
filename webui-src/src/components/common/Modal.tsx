import { ReactNode, useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: 'sm' | 'md' | 'lg' | 'xl';
  showClose?: boolean;
  backButton?: ReactNode;
}

const widthClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
};

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  width = 'md',
  showClose = true,
  backButton,
}: ModalProps) {
  // 阻止背景滚动
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* 弹窗内容 */}
      <div
        className={cn(
          'relative bg-white rounded-2xl shadow-xl w-full mx-4 overflow-hidden',
          widthClasses[width]
        )}
      >
        {/* 头部 */}
        {(title || showClose || backButton) && (
          <div className="flex items-center justify-between px-6 py-5 border-b border-border">
            <div className="flex items-center gap-3">
              {backButton}
              {title && (
                <h2 className="text-lg font-semibold font-display text-text-primary">
                  {title}
                </h2>
              )}
            </div>
            {showClose && (
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                <X className="w-4 h-4 text-text-secondary" />
              </button>
            )}
          </div>
        )}
        
        {/* 内容 */}
        <div className="p-6">
          {children}
        </div>
        
        {/* 底部 */}
        {footer && (
          <div className="flex items-center gap-3 px-6 py-5 border-t border-border">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
