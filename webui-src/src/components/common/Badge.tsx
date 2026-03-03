import { cn } from '../../lib/utils';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'error' | 'gray';
  size?: 'sm' | 'md';
}

export function Badge({ children, variant = 'gray', size = 'sm' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        {
          'px-2 py-0.5 text-xs': size === 'sm',
          'px-2.5 py-1 text-xs': size === 'md',
        },
        {
          'bg-primary-100 text-primary': variant === 'primary',
          'bg-success-100 text-success': variant === 'success',
          'bg-warning-100 text-warning': variant === 'warning',
          'bg-error-100 text-error': variant === 'error',
          'bg-slate-100 text-slate-500': variant === 'gray',
        }
      )}
    >
      {children}
    </span>
  );
}
