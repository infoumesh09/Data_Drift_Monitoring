import { useQuery } from '@tanstack/react-query'
import { driftApi } from '@/services/api'
import { StatCard, SectionCard, PageHeader, SeverityBadge } from '@/components/ui'
import { cn, formatNumber, formatPercent } from '@/lib/utils'
import type { SchemaRow, SchemaChange } from '@/types'

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}
function MinusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14" />
    </svg>
  )
}
function TypeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 7V4h16v3" />
      <path d="M9 20h6" />
      <path d="M12 4v16" />
    </svg>
  )
}
function PctIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 5 5 19" />
      <circle cx="6.5" cy="6.5" r="2.5" />
      <circle cx="17.5" cy="17.5" r="2.5" />
    </svg>
  )
}
function HashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 9h16M4 15h16M10 3 8 21M16 3l-2 18" />
    </svg>
  )
}

function beforeAfterBadge(status: string) {
  if (status === 'Unchanged')
    return (
      <span className="badge text-severity-healthy border-severity-healthy/30 bg-severity-healthy/10">
        <span className="w-1.5 h-1.5 rounded-full bg-severity-healthy" /> Unchanged
      </span>
    )
  if (status.startsWith('+'))
    return (
      <span className="badge text-severity-healthy border-severity-healthy/30 bg-severity-healthy/10">
        <PlusIcon className="w-3 h-3" /> Column
      </span>
    )
  if (status.startsWith('-'))
    return (
      <span className="badge text-severity-critical border-severity-critical/30 bg-severity-critical/10">
        <MinusIcon className="w-3 h-3" /> Column
      </span>
    )
  if (status.includes('Type'))
    return (
      <span className="badge text-severity-critical border-severity-critical/30 bg-severity-critical/10">
        <TypeIcon className="w-3 h-3" /> Changed
      </span>
    )
  return <span className="badge">{status}</span>
}

export default function SchemaMonitoring() {
  const { data, isLoading } = useQuery({
    queryKey: ['drift-schema'],
    queryFn: driftApi.schema,
    retry: false,
  })

  const hasData = data?.has_data

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Schema Monitoring"
        title="Schema Monitoring"
        subtitle="Detect and track schema changes between baseline and current datasets"
      />

      {!hasData && !isLoading && (
        <div className="card p-10 text-center space-y-3 border-dashed">
          <div className="text-white font-medium text-lg">No schema comparison data found</div>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Run a drift detection run between a baseline dataset and current dataset to analyze schema stability, column additions, deletions, type alterations, and cardinality shifts.
          </p>
          <a href="/drift-monitoring" className="btn btn-primary inline-flex">
            Go to Drift Detection
          </a>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <StatCard
          accent="health"
          title="Added Columns"
          value={data?.added_columns ?? 0}
          icon={<PlusIcon className="w-4 h-4" />}
        />
        <StatCard
          accent="critical"
          title="Removed Columns"
          value={data?.removed_columns ?? 0}
          icon={<MinusIcon className="w-4 h-4" />}
        />
        <StatCard
          accent="critical"
          title="Type Changes"
          value={data?.type_changes ?? 0}
          icon={<TypeIcon className="w-4 h-4" />}
        />
        <StatCard
          accent="warning"
          title="Null-Rate Changes"
          value={data?.null_rate_changes ?? 0}
          icon={<PctIcon className="w-4 h-4" />}
        />
        <StatCard
          accent="warning"
          title="Cardinality Changes"
          value={data?.cardinality_changes ?? 0}
          icon={<HashIcon className="w-4 h-4" />}
        />
      </div>

      <SectionCard
        title="Before / After Schema Comparison"
        subtitle={hasData ? "Baseline schema vs Current schema from latest detection run" : "No active detection run"}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Column</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Status</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Before (Baseline)</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">After (Current)</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted text-right">Null Rate</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted text-right">Cardinality</th>
              </tr>
            </thead>
            <tbody>
              {(data?.before_after ?? []).map((row: SchemaRow) => (
                <tr key={row.column} className="border-b border-border/50 last:border-0 hover:bg-surface-2/50">
                  <td className="px-4 py-3 font-mono text-white">{row.column}</td>
                  <td className="px-4 py-3">{beforeAfterBadge(row.status)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text-muted">{row.before}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text">{row.after}</td>
                  <td className={cn('px-4 py-3 font-mono text-xs text-right', row.null_rate > 0.1 ? 'text-severity-high' : 'text-text-muted')}>
                    {formatPercent(row.null_rate)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-right text-text-muted">
                    {formatNumber(row.cardinality, 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard
        title="Schema Change Log"
        subtitle="All detected schema changes with timestamps"
        actions={
          <select className="select">
            <option>All changes</option>
            <option>Type changes</option>
            <option>Added / removed</option>
            <option>Null-rate changes</option>
          </select>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Change Type</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Column</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Before</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">After</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Severity</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Detected By</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted text-right">Detected At</th>
              </tr>
            </thead>
            <tbody>
              {(data?.change_log ?? []).map((c: SchemaChange, i: number) => (
                <tr key={i} className="border-b border-border/50 last:border-0 hover:bg-surface-2/50">
                  <td className="px-4 py-3">
                    <SeverityBadge
                      severity={c.severity === 'Warning' ? 'MEDIUM' : c.severity}
                      label={c.change_type}
                    />
                  </td>
                  <td className="px-4 py-3 font-mono text-white">{c.column}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text-muted">{c.before}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text">{c.after}</td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={c.severity} label={c.severity} />
                  </td>
                  <td className="px-4 py-3 text-xs text-text-muted">{c.detected_by}</td>
                  <td className="px-4 py-3 text-xs text-right text-text-muted whitespace-nowrap">{c.detected_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}
