import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Variant = 'default' | 'outline' | 'subtle';
type Size = 'sm' | 'md' | 'lg';

export function StatCard({
  title,
  icon,
  value,
  delta,
  deltaLabel = 'this week',
  variant = 'default',
  accent = 'blue',
  size = 'md',
  children,
}: {
  title: string;
  icon?: ReactNode;
  value: ReactNode;
  delta?: string;
  deltaType?: 'positive' | 'negative' | 'neutral';
  deltaLabel?: string;
  variant?: Variant;
  accent?: 'yellow' | 'green' | 'red' | 'blue' | 'indigo' | 'purple' | 'orange';
  size?: Size;
  children?: ReactNode;
}) {
  return (
    <div
      className={cn(
        'stat-card',
        size === 'lg' ? 'p-6' : 'p-5',
        accent === 'yellow' && 'accent-left-yellow',
        accent === 'green' && 'accent-left-green',
        accent === 'red' && 'accent-left-red',
        accent === 'blue' && 'accent-left-blue',
        accent === 'indigo' && 'accent-left-indigo',
        accent === 'purple' && 'accent-left-purple',
        accent === 'orange' && 'accent-left-orange',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[13px] font-medium text-text-secondary">
            {title}
            {children}
          </div>
          <div className={cn('mt-2 font-bold tracking-tight', size === 'lg' ? 'text-4xl' : 'text-3xl')}>
            {value}
          </div>
          {delta && (
            <div className="mt-2 text-[12px] text-text-muted flex items-center gap-1.5">
              <span className={cn(
                'font-semibold',
                delta.startsWith('+') || delta.startsWith('↓') || delta.includes('vs')
                  ? 'text-severity-critical'
                  : delta.startsWith('-') || delta.startsWith('↑')
                    ? 'text-severity-healthy'
                    : 'text-text-muted',
              )}>
                {delta}
              </span>
              <span className="text-text-dim">vs {deltaLabel}</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="p-2 rounded-lg bg-white/[0.04] text-text-muted border border-white/5">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
