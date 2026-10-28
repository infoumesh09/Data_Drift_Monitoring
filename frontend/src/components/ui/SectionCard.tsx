import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function SectionCard({
  title,
  subtitle,
  actions,
  icon,
  className,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn('card overflow-hidden', className)}>
      <div className="flex items-center justify-between gap-3 p-5 border-b border-bg-border">
        <div className="flex items-center gap-3 min-w-0">
          {icon && <div className="text-brand-400">{icon}</div>}
          <div className="min-w-0">
            <h3 className="h3 flex items-center gap-2">{title}</h3>
            {subtitle && <p className="text-sm text-text-muted mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="shrink-0 flex items-center gap-2">{actions}</div>}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}
