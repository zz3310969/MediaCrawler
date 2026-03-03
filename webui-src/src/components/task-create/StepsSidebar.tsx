import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface Step {
  id: number;
  title: string;
  description: string;
}

interface StepsSidebarProps {
  steps: Step[];
  currentStep: number;
}

export function StepsSidebar({ steps, currentStep }: StepsSidebarProps) {
  return (
    <div className="space-y-0">
      {steps.map((step) => {
        const isCompleted = step.id < currentStep;
        const isActive = step.id === currentStep;
        const isPending = step.id > currentStep;

        return (
          <div
            key={step.id}
            className={cn(
              'flex items-center gap-3 py-4',
              step.id < steps.length && 'relative'
            )}
          >
            {/* 步骤编号 */}
            <div
              className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0',
                isCompleted && 'bg-success text-white',
                isActive && 'bg-primary text-white',
                isPending && 'border-2 border-slate-300 text-slate-400'
              )}
            >
              {isCompleted ? (
                <Check className="w-4 h-4" />
              ) : (
                step.id
              )}
            </div>

            {/* 步骤信息 */}
            <div className="space-y-0.5">
              <p
                className={cn(
                  'text-sm font-medium',
                  isActive ? 'text-primary' : isCompleted ? 'text-text-primary' : 'text-slate-400'
                )}
              >
                {step.title}
              </p>
              <p className="text-xs text-text-secondary">{step.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
