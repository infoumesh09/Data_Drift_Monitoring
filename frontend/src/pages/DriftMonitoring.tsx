import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { driftApi, datasetsApi } from '@/services/api'
import { SectionCard, PageHeader, SeverityBadge, DataTable } from '@/components/ui'
import { cn, driftMetricColor, formatPercent } from '@/lib/utils'
import type { FeatureDriftScore } from '@/types'

function FilterIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 5h18M6 12h12M10 19h4" />
    </svg>
  )
}

// -------------------------------------------------------------------------
// Run Detection modal
// -------------------------------------------------------------------------
function RunDetectionModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess: (result: any) => void
}) {
  const [baselineId, setBaselineId] = useState('')
  const [currentId, setCurrentId] = useState('')
  const [error, setError] = useState('')

  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: datasetsApi.list,
    retry: false,
  })

  const detectMutation = useMutation({
    mutationFn: driftApi.detect,
    onSuccess: (data) => {
      // Persist result in sessionStorage for FeatureDrillDown
      try {
        sessionStorage.setItem('last_drift_result', JSON.stringify(data))
      } catch {
        // ignore storage errors
      }
      onSuccess(data)
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!baselineId || !currentId) {
      setError('Please select both a baseline and a current dataset.')
      return
    }
    if (baselineId === currentId) {
      setError('Baseline and current datasets must be different.')
      return
    }
    detectMutation.mutate({ baseline_dataset_id: baselineId, current_dataset_id: currentId })
  }

  const datasetList = datasets ?? []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
    >
      <div
        className="card w-full max-w-lg p-6 space-y-5"
        role="dialog"
        aria-modal="true"
        aria-labelledby="run-detect-title"
      >
        <div className="flex items-center justify-between">
          <h2 id="run-detect-title" className="text-lg font-semibold text-white">
            Run Drift Detection
          </h2>
          <button className="text-text-muted hover:text-white text-xl leading-none" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-text-muted uppercase tracking-wider font-semibold" htmlFor="baseline-select">
              Baseline Dataset
            </label>
            <select
              id="baseline-select"
              className="select w-full"
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value)}
            >
              <option value="">Select baseline…</option>
              {datasetList.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {d.is_baseline ? '(baseline)' : ''} — {d.row_count.toLocaleString()} rows
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-text-muted uppercase tracking-wider font-semibold" htmlFor="current-select">
              Current Dataset
            </label>
            <select
              id="current-select"
              className="select w-full"
              value={currentId}
              onChange={(e) => setCurrentId(e.target.value)}
            >
              <option value="">Select current…</option>
              {datasetList.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {d.is_baseline ? '(baseline)' : ''} — {d.row_count.toLocaleString()} rows
                </option>
              ))}
            </select>
          </div>

          {datasetList.length === 0 && (
            <p className="text-xs text-severity-medium">
              No datasets found.{' '}
              <a href="/datasets" className="underline">
                Upload datasets
              </a>{' '}
              to run detection.
            </p>
          )}

          {error && <p className="text-xs text-severity-critical">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button type="button" className="btn flex-1" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary flex-1"
              disabled={detectMutation.isPending}
            >
              {detectMutation.isPending ? 'Running…' : 'Run Detection'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// -------------------------------------------------------------------------
// Result summary banner
// -------------------------------------------------------------------------
function DetectionResultBanner({ result, onDismiss }: { result: any; onDismiss: () => void }) {
  return (
    <div className="card p-4 border-severity-healthy/30 bg-severity-healthy/5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-semibold text-white">Detection Complete</div>
        <button className="text-text-muted hover:text-white text-sm" onClick={onDismiss}>✕</button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <div className="text-text-muted text-xs">Run ID</div>
          <div className="font-mono text-white text-xs">{result.run_id}</div>
        </div>
        <div>
          <div className="text-text-muted text-xs">Overall Severity</div>
          <SeverityBadge severity={result.overall_severity} />
        </div>
        <div>
          <div className="text-text-muted text-xs">Features Monitored</div>
          <div className="text-white font-semibold">{result.features_monitored}</div>
        </div>
        <div>
          <div className="text-text-muted text-xs">Features with Drift</div>
          <div className="text-severity-high font-semibold">{result.features_with_drift}</div>
        </div>
      </div>
    </div>
  )
}

// -------------------------------------------------------------------------
// Main page
// -------------------------------------------------------------------------
export default function DriftMonitoring() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [detectionResult, setDetectionResult] = useState<any>(null)
  const [driftTypeFilter, setDriftTypeFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')

  const { data } = useQuery({
    queryKey: ['drift-feature-scores'],
    queryFn: driftApi.featureScores,
    retry: false,
  })

  let rows: FeatureDriftScore[] = data ?? []

  if (driftTypeFilter !== 'all') {
    rows = rows.filter((r) => r.drift_type.toLowerCase().includes(driftTypeFilter.toLowerCase()))
  }

  const handleDetectionSuccess = (result: any) => {
    setDetectionResult(result)
    setShowModal(false)
    qc.invalidateQueries({ queryKey: ['drift-feature-scores'] })
  }

  return (
    <div className="space-y-6">
      {showModal && (
        <RunDetectionModal
          onClose={() => setShowModal(false)}
          onSuccess={handleDetectionSuccess}
        />
      )}

      <PageHeader
        breadcrumb="Drift Monitoring"
        title="Drift Monitoring"
        subtitle="Per-feature statistical drift scores across PSI, KL Divergence and KS Test"
        actions={
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + Run Detection
          </button>
        }
      />

      {detectionResult && (
        <DetectionResultBanner result={detectionResult} onDismiss={() => setDetectionResult(null)} />
      )}

      <div className="card p-4 flex flex-wrap items-center gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted uppercase tracking-wider font-semibold">Current Window</span>
          <select className="select min-w-[160px]">
            <option>24 hours</option>
            <option>7 days</option>
            <option>30 days</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted uppercase tracking-wider font-semibold">Drift Type</span>
          <select
            className="select min-w-[160px]"
            value={driftTypeFilter}
            onChange={(e) => setDriftTypeFilter(e.target.value)}
          >
            <option value="all">All types</option>
            <option value="Distribution">Distribution Drift</option>
            <option value="Null">Null Rate Drift</option>
            <option value="Schema">Schema Drift</option>
            <option value="Cardinality">Cardinality Drift</option>
            <option value="Correlation">Correlation Drift</option>
            <option value="Seasonal">Seasonal Drift</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-text-muted uppercase tracking-wider font-semibold">Severity</span>
          <select
            className="select min-w-[160px]"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="all">All severities</option>
            <option value="HEALTHY">Healthy</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <FilterIcon className="w-4 h-4" />
          {rows.length} features
        </div>
      </div>

      {rows.length === 0 && (
        <div className="card p-8 text-center space-y-3 border-dashed">
          <div className="text-white font-medium text-base">No drift detection runs yet</div>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Run statistical drift detection between a baseline dataset and a current dataset to inspect PSI, KL divergence, KS test, null rates, and drift severities across all monitored features.
          </p>
          <button className="btn btn-primary inline-flex" onClick={() => setShowModal(true)}>
            + Run Detection
          </button>
        </div>
      )}

      <SectionCard
        title="Feature Drift Scores"
        subtitle="Click a feature to view distribution comparison and trend analysis"
      >
        <DataTable
          rowKey={(r) => r.feature}
          onRowClick={(r) => navigate(`/drift-monitoring/${r.feature}`)}
          columns={[
            {
              key: 'feature',
              label: 'Feature',
              render: (r: FeatureDriftScore) => (
                <div className="flex items-center gap-2">
                  <span className="font-mono text-white">{r.feature}</span>
                  <span
                    className={cn(
                      'badge text-[10px]',
                      r.type === 'numeric'
                        ? 'bg-brand-soft/20 border-brand/30 text-brand'
                        : 'bg-purple-500/10 border-purple-500/30 text-purple-300',
                    )}
                  >
                    {r.type}
                  </span>
                </div>
              ),
            },
            {
              key: 'psi',
              label: 'PSI',
              className: 'font-mono text-right',
              render: (r: FeatureDriftScore) => (
                <span className={driftMetricColor(r.psi, { low: 0.1, medium: 0.25, high: 0.4 })}>
                  {r.psi.toFixed(3)}
                </span>
              ),
            },
            {
              key: 'kl',
              label: 'KL Div',
              className: 'font-mono text-right',
              render: (r: FeatureDriftScore) => (
                <span className={driftMetricColor(r.kl, { low: 0.1, medium: 0.4, high: 1 })}>
                  {r.kl.toFixed(3)}
                </span>
              ),
            },
            {
              key: 'ks_stat',
              label: 'KS Stat',
              className: 'font-mono text-right',
              render: (r: FeatureDriftScore) => <span className="text-text">{r.ks_stat.toFixed(3)}</span>,
            },
            {
              key: 'ks_p',
              label: 'KS P-Value',
              className: 'font-mono text-right',
              render: (r: FeatureDriftScore) => (
                <span className={r.ks_p < 0.05 ? 'text-severity-high font-semibold' : 'text-text-muted'}>
                  {r.ks_p.toFixed(4)}
                </span>
              ),
            },
            {
              key: 'null_rate',
              label: 'Null Rate',
              className: 'font-mono text-right',
              render: (r: FeatureDriftScore) => (
                <span
                  className={
                    r.null_rate > 0.2
                      ? 'text-severity-critical font-semibold'
                      : r.null_rate > 0.1
                      ? 'text-severity-high'
                      : 'text-text-muted'
                  }
                >
                  {formatPercent(r.null_rate)}
                </span>
              ),
            },
            {
              key: 'cardinality',
              label: 'Cardinality',
              className: 'font-mono text-right text-text-muted',
              render: (r: FeatureDriftScore) => r.cardinality.toLocaleString(),
            },
            {
              key: 'drift_type',
              label: 'Drift Type',
              render: (r: FeatureDriftScore) => {
                const anyHigh = r.psi >= 0.25 || r.kl >= 0.5 || r.null_rate > 0.15
                return <SeverityBadge severity={anyHigh ? 'HIGH' : 'MEDIUM'} label={r.drift_type} />
              },
            },
          ]}
          rows={rows}
        />
      </SectionCard>
    </div>
  )
}
