import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function StatCard({
  title,
  value,
  icon,
  trend,
  accent,
  footer,
}: {
  title: string
  value: ReactNode
  icon?: ReactNode
  trend?: { label: string; positive?: boolean; warning?: boolean; critical?: boolean }
  accent?: 'default' | 'health' | 'warning' | 'critical'
  footer?: ReactNode
}) {
  const accentBar = {
    default: 'bg-border-2',
    health: 'bg-severity-healthy',
    warning: 'bg-severity-medium',
    critical: 'bg-severity-critical',
  }[accent ?? 'default']

  const trendColor = trend?.critical
    ? 'text-severity-critical'
    : trend?.warning
    ? 'text-severity-medium'
    : trend?.positive
    ? 'text-severity-healthy'
    : 'text-text-muted'

  return (
    <div className="card relative overflow-hidden">
      <div className={cn('absolute left-0 top-0 bottom-0 w-1 rounded-l-xl', accentBar)} />
      <div className="p-5 pl-6">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="text-sm text-text-muted flex items-center gap-2">
            {title}
            <span className="text-text-subtle cursor-help" title={title}>
              ⓘ
            </span>
          </div>
          {icon && <div className="text-text-muted">{icon}</div>}
        </div>
        <div className="flex items-end justify-between gap-3">
          <div className="text-3xl font-semibold text-white tracking-tight">{value}</div>
          {trend && (
            <div className={cn('text-xs flex items-center gap-1 pb-1', trendColor)}>
              {trend.positive || (!trend.warning && !trend.critical) ? '⌄' : '⌃'} {trend.label}
            </div>
          )}
        </div>
        {footer && <div className="mt-3 pt-3 border-t border-border/70 text-xs text-text-muted">{footer}</div>}
      </div>
    </div>
  )
}

export function SectionCard({
  title,
  subtitle,
  actions,
  children,
  icon,
  className,
}: {
  title: string
  subtitle?: string
  icon?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('card overflow-hidden', className)}>
      <header className="flex items-start justify-between gap-4 px-5 py-4 border-b border-border/70">
        <div className="flex items-start gap-3">
          {icon && <div className="mt-0.5 text-text-muted">{icon}</div>}
          <div>
            <h3 className="text-[15px] font-semibold text-white leading-tight">{title}</h3>
            {subtitle && <p className="text-xs text-text-muted mt-1">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </header>
      <div className="p-5">{children}</div>
    </section>
  )
}

export function SeverityBadge({
  severity,
  label,
  showDot = true,
}: {
  severity: string
  label?: string
  showDot?: boolean
}) {
  const cls = {
    Healthy: 'text-severity-healthy border-severity-healthy/30 bg-severity-healthy/10',
    HEALTHY: 'text-severity-healthy border-severity-healthy/30 bg-severity-healthy/10',
    LOW: 'text-severity-low border-severity-low/30 bg-severity-low/10',
    Warning: 'text-severity-medium border-severity-medium/30 bg-severity-medium/10',
    MEDIUM: 'text-severity-medium border-severity-medium/30 bg-severity-medium/10',
    High: 'text-severity-high border-severity-high/30 bg-severity-high/10',
    HIGH: 'text-severity-high border-severity-high/30 bg-severity-high/10',
    Critical: 'text-severity-critical border-severity-critical/30 bg-severity-critical/10',
    CRITICAL: 'text-severity-critical border-severity-critical/30 bg-severity-critical/10',
  }[severity] ?? 'text-text-muted border-border bg-surface'

  const dot = {
    Healthy: 'bg-severity-healthy',
    HEALTHY: 'bg-severity-healthy',
    LOW: 'bg-severity-low',
    Warning: 'bg-severity-medium',
    MEDIUM: 'bg-severity-medium',
    High: 'bg-severity-high',
    HIGH: 'bg-severity-high',
    Critical: 'bg-severity-critical',
    CRITICAL: 'bg-severity-critical',
  }[severity] ?? 'bg-text-subtle'

  return (
    <span className={cn('badge', cls)}>
      {showDot && <span className={cn('w-1.5 h-1.5 rounded-full', dot)} />}
      {label ?? severity}
    </span>
  )
}

export function PageHeader({
  breadcrumb,
  title,
  subtitle,
  actions,
}: {
  breadcrumb?: string
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
      <div>
        {breadcrumb && <div className="text-xs text-text-muted mb-1.5">{breadcrumb}</div>}
        <h1 className="text-2xl font-semibold text-white tracking-tight leading-tight">{title}</h1>
        {subtitle && <p className="text-sm text-text-muted mt-1.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

export function DataTable({
  columns,
  rows,
  rowKey,
  onRowClick,
  empty = 'No data',
}: {
  columns: { key: string; label: string; className?: string; render?: (r: any) => ReactNode }[]
  rows: any[]
  rowKey: (r: any) => string
  onRowClick?: (r: any) => void
  empty?: string
}) {
  return (
    <div className="overflow-x-auto -mx-1 px-1">
      <table className="w-full text-sm border-separate border-spacing-0">
        <thead>
          <tr className="text-left">
            {columns.map((c) => (
              <th
                key={c.key}
                className={cn(
                  'px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted border-b border-border whitespace-nowrap',
                  c.className,
                )}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-text-muted text-sm">
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr
                key={rowKey(r)}
                onClick={() => onRowClick?.(r)}
                className={cn(
                  'border-b border-border/50 last:border-0',
                  onRowClick && 'cursor-pointer hover:bg-surface-2/60 transition-colors',
                )}
              >
                {columns.map((c) => (
                  <td key={c.key} className={cn('px-4 py-3 align-middle', c.className)}>
                    {c.render ? c.render(r) : r[c.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
