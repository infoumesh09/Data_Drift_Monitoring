import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { overviewApi, driftApi } from '@/services/api'
import { StatCard, SectionCard, PageHeader, SeverityBadge, DataTable } from '@/components/ui'
import { formatDate, heatmapColor, cn, formatNumber } from '@/lib/utils'
import type { Severity } from '@/types'

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
    </svg>
  )
}
function PipeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7h3a2 2 0 0 1 2 2v6a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" />
      <circle cx="4" cy="7" r="1.4" />
      <circle cx="20" cy="11" r="1.4" />
    </svg>
  )
}
function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.3 3.72 2.52 16.83a2 2 0 0 0 1.72 3h15.52a2 2 0 0 0 1.72-3L13.71 3.72a2 2 0 0 0-3.41 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  )
}
function LayersIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 2 10 6-10 6L2 8l10-6Z" />
      <path d="m2 16 10 6 10-6" />
    </svg>
  )
}
function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}
function HeatmapIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M14 7h7v7" />
    </svg>
  )
}

export default function Overview() {
  const navigate = useNavigate()
  const { data: overview } = useQuery({
    queryKey: ['overview'],
    queryFn: overviewApi.get,
    retry: false,
  })
  const { data: heatmap } = useQuery({
    queryKey: ['drift-heatmap'],
    queryFn: driftApi.heatmap,
    retry: false,
    enabled: !overview?.drift_heatmap,
  })
  const hm = overview?.drift_heatmap ?? heatmap

  const stats = overview?.stats ?? {
    data_health_score: 100,
    active_pipelines: 0,
    healthy_pipelines: 0,
    active_incidents: 0,
    critical_incidents: 0,
    monitored_features: 0,
    drift_events_today: 0,
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Overview"
        title="Overview"
        subtitle="Real-time data observability across all monitored pipelines"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard
          accent="health"
          title="Data Health Score"
          value={stats.data_health_score}
          icon={<ShieldIcon className="w-[18px] h-[18px]" />}
        />
        <StatCard
          title="Active Pipelines"
          value={stats.active_pipelines}
          icon={<PipeIcon className="w-[18px] h-[18px]" />}
        />
        <StatCard
          title="Healthy Pipelines"
          value={stats.healthy_pipelines}
          icon={<ShieldIcon className="w-[18px] h-[18px]" />}
        />
        <StatCard
          accent="warning"
          title="Active Incidents"
          value={stats.active_incidents}
          icon={<AlertIcon className="w-[18px] h-[18px]" />}
        />
        <StatCard
          accent="critical"
          title="Critical Incidents"
          value={stats.critical_incidents}
          icon={<AlertIcon className="w-[18px] h-[18px]" />}
        />
        <StatCard
          title="Monitored Features"
          value={stats.monitored_features}
          icon={<LayersIcon className="w-[18px] h-[18px]" />}
        />
        <StatCard
          title="Drift Events Today"
          value={stats.drift_events_today}
          icon={<ClockIcon className="w-[18px] h-[18px]" />}
        />
      </div>

      <SectionCard
        title="Drift Severity Heatmap"
        subtitle="Feature × time window — darker cells indicate higher drift severity"
        icon={<HeatmapIcon className="w-[18px] h-[18px]" />}
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Last 24h</span>
          </div>
        }
      >
        {!hm?.rows || hm.rows.length === 0 ? (
          <div className="text-center py-8 text-sm text-text-muted">
            No drift events recorded in the last 24 hours. Run drift detection between datasets to populate the activity heatmap.
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-3">
              <div className="flex-1 grid grid-cols-12 gap-1.5 pl-36">
                {hm?.time_windows?.map((t) => (
                  <div key={t} className="text-[11px] text-text-muted text-center truncate">
                    {t}
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              {hm?.rows?.map((row) => (
                <div key={row.feature} className="flex items-center gap-3">
                  <div className="w-36 text-xs text-text-muted truncate shrink-0 font-mono">
                    {row.feature}
                  </div>
                  <div className="flex-1 grid grid-cols-12 gap-1.5">
                    {row.cells.map((sev: Severity, i: number) => (
                      <div
                        key={i}
                        title={`${row.feature} @ ${hm.time_windows[i]}: ${sev}`}
                        className={cn('heatmap-cell h-6', heatmapColor(sev))}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-end gap-4 mt-4 pt-4 border-t border-border/60">
              <div className="flex items-center gap-4 text-[11px] text-text-muted">
                {(['HEALTHY', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as Severity[]).map((s) => (
                  <div key={s} className="flex items-center gap-1.5">
                    <div className={cn('w-3.5 h-3.5 rounded-sm', heatmapColor(s))} />
                    <span>{s.charAt(0) + s.slice(1).toLowerCase()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <SectionCard
            title="Pipelines"
            subtitle={`${overview?.pipelines?.length ?? 0} monitored data pipelines`}
            actions={
              <button onClick={() => navigate('/pipelines')} className="btn">
                View all →
              </button>
            }
          >
            <DataTable
              rowKey={(r) => r.id}
              onRowClick={(r) => navigate('/pipelines')}
              columns={[
                {
                  key: 'pipeline',
                  label: 'Pipeline',
                  render: (r) => (
                    <div>
                      <div className="font-medium text-white">{r.name}</div>
                      <div className="text-xs text-text-muted">{r.project}</div>
                    </div>
                  ),
                },
                {
                  key: 'source',
                  label: 'Source',
                  className: 'text-text-muted',
                },
                {
                  key: 'destination',
                  label: 'Destination',
                  className: 'text-text-muted',
                },
                {
                  key: 'last_successful_run',
                  label: 'Last Successful Run',
                  className: 'text-text-muted whitespace-nowrap',
                  render: (r) => formatDate(r.last_successful_run),
                },
                {
                  key: 'status',
                  label: 'Status',
                  render: (r) => <SeverityBadge severity={r.status} />,
                },
                {
                  key: 'mcfe_count',
                  label: 'MCFE',
                  className: 'text-right font-mono text-text-muted',
                  render: (r) => formatNumber(r.mcfe_count, 0),
                },
              ]}
              rows={overview?.pipelines ?? []}
            />
          </SectionCard>
        </div>
        <div>
          <SectionCard
            title="Recent Incidents"
            subtitle="Active and in-progress drift incidents"
            actions={
              <button onClick={() => navigate('/incidents')} className="btn">
                All →
              </button>
            }
          >
            {overview?.incidents && overview.incidents.length > 0 ? (
              <ul className="space-y-3">
                {overview.incidents.map((inc) => (
                  <li
                    key={inc.id}
                    onClick={() => navigate(`/ai-diagnosis?incident_id=${inc.id}`)}
                    className="p-3 rounded-lg border border-border hover:border-border-2 hover:bg-surface-2/60 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="font-mono text-[11px] text-text-subtle">{inc.id}</div>
                      <SeverityBadge severity={inc.severity} showDot={false} />
                    </div>
                    <div className="text-sm text-white leading-snug mb-2 line-clamp-2">
                      {inc.summary}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-text-muted">
                      <span className="font-mono">
                        {inc.metric} {formatNumber(inc.score)} · {inc.feature}
                      </span>
                      <span>{formatDate(inc.timestamp)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center py-8 text-sm text-text-muted">
                No active incidents. Monitored pipelines are operating within nominal thresholds.
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
