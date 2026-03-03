import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          // 尺寸
          {
            'px-3 h-8 text-xs': size === 'sm',
            'px-5 h-10 text-sm': size === 'md',
            'px-6 h-12 text-base': size === 'lg',
          },
          // 变体
          {
            'bg-primary text-white hover:bg-primary-600 focus:ring-primary': variant === 'primary',
            'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 focus:ring-slate-200': variant === 'secondary',
            'bg-success text-white hover:bg-success-600 focus:ring-success': variant === 'success',
            'bg-warning text-white hover:bg-warning-600 focus:ring-warning': variant === 'warning',
            'bg-error text-white hover:bg-error-600 focus:ring-error': variant === 'error',
            'bg-transparent text-slate-600 hover:bg-slate-100 focus:ring-slate-200': variant === 'ghost',
          },
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
