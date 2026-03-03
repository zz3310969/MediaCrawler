import { cn } from '../../lib/utils';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  description?: string;
}

export function Switch({ checked, onChange, disabled, label, description }: SwitchProps) {
  return (
    <label className={cn(
      'flex items-center justify-between cursor-pointer',
      disabled && 'cursor-not-allowed opacity-50'
    )}>
      {(label || description) && (
        <div className="space-y-1">
          {label && (
            <span className="text-base font-medium text-text-primary">{label}</span>
          )}
          {description && (
            <p className="text-sm text-text-secondary">{description}</p>
          )}
        </div>
      )}
      
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex h-7 w-[52px] items-center rounded-full transition-colors',
          checked ? 'bg-primary' : 'bg-slate-200',
          disabled && 'cursor-not-allowed'
        )}
      >
        <span
          className={cn(
            'inline-block h-[22px] w-[22px] transform rounded-full bg-white shadow-sm transition-transform',
            checked ? 'translate-x-[27px]' : 'translate-x-[3px]'
          )}
        />
      </button>
    </label>
  );
}
