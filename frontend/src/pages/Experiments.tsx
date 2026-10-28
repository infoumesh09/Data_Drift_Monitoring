import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { SectionCard, PageHeader, SeverityBadge, DataTable } from '@/components/ui'
import { experimentsApi, datasetsApi } from '@/services/api'
import type { ExperimentResultRecord } from '@/services/api'
import { formatNumber } from '@/lib/utils'

const ALL_DRIFT_TYPES = [
  { id: 'no_drift', name: 'No drift (control)', description: 'Baseline distribution preserved — pure control run.', severity: 'HEALTHY' },
  { id: 'small_mean_shift', name: 'Small mean shift (0.5σ)', description: 'Subtle location shift, tests sensitivity.', severity: 'LOW' },
  { id: 'medium_mean_shift', name: 'Medium mean shift (1.0σ)', description: 'Noticeable shift, most methods should detect.', severity: 'MEDIUM' },
  { id: 'large_mean_shift', name: 'Large mean shift (2.0σ)', description: 'Clear shift — all detectors expected to fire.', severity: 'HIGH' },
  { id: 'variance_shift', name: 'Variance shift', description: 'Scale change while mean stays fixed.', severity: 'MEDIUM' },
  { id: 'distribution_shift', name: 'Distribution family shift', description: 'Gaussian → exponential — family change.', severity: 'HIGH' },
  { id: 'categorical_shift', name: 'Categorical proportion shift', description: 'Class rebalancing on categorical features.', severity: 'MEDIUM' },
  { id: 'gradual_drift', name: 'Gradual drift (linear ramp)', description: 'Slow linear transition over the window.', severity: 'MEDIUM' },
  { id: 'sudden_drift', name: 'Sudden drift (split-point)', description: 'Hard change-point at the window midpoint.', severity: 'HIGH' },
  { id: 'null_rate_spike', name: 'Null-rate spike', description: 'Abrupt increase in missing-value ratio.', severity: 'CRITICAL' },
  { id: 'schema_change', name: 'Schema change (type/column)', description: 'Datatype coercion, added or removed columns.', severity: 'CRITICAL' },
]

function RunStatusBanner({
  status,
  summary,
  onDismiss,
}: {
  status: 'running' | 'done' | 'error'
  summary?: string
  onDismiss: () => void
}) {
  const cls =
    status === 'done'
      ? 'bg-severity-healthy/10 border-severity-healthy/30 text-severity-healthy'
      : status === 'error'
      ? 'bg-severity-critical/10 border-severity-critical/30 text-severity-critical'
      : 'bg-brand-soft/10 border-brand/30 text-brand'

  return (
    <div className={`rounded-xl border px-4 py-3 flex items-center justify-between gap-4 text-sm ${cls}`}>
      <span>
        {status === 'running' && '⏳ Running experiments…'}
        {status === 'done' && `✓ ${summary}`}
        {status === 'error' && `✗ ${summary}`}
      </span>
      <button onClick={onDismiss} className="opacity-60 hover:opacity-100 text-xs">✕</button>
    </div>
  )
}

export default function Experiments() {
  const qc = useQueryClient()
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('')
  const [seed, setSeed] = useState('42')
  const [runStatus, setRunStatus] = useState<{ status: 'running' | 'done' | 'error'; msg: string } | null>(null)

  const { data: datasetsData } = useQuery({
    queryKey: ['datasets'],
    queryFn: datasetsApi.list,
    retry: false,
  })

  const { data: resultsData, isLoading: resultsLoading } = useQuery({
    queryKey: ['experiment-results'],
    queryFn: () => experimentsApi.results(),
    retry: false,
  })

  const runMutation = useMutation({
    mutationFn: experimentsApi.run,
    onMutate: () => setRunStatus({ status: 'running', msg: '' }),
    onSuccess: (data) => {
      setRunStatus({
        status: 'done',
        msg: `Completed ${data.total_runs} runs across ${data.drift_types_tested.length} drift type(s).`,
      })
      qc.invalidateQueries({ queryKey: ['experiment-results'] })
      qc.invalidateQueries({ queryKey: ['algorithm-comparison'] })
    },
    onError: (err: Error) => setRunStatus({ status: 'error', msg: err.message }),
  })

  const handleRunSingle = (driftTypeId: string) => {
    runMutation.mutate({
      drift_types: [driftTypeId],
      dataset_id: selectedDatasetId || undefined,
      sample_sizes: [1000, 5000],
      magnitudes: [0.5, 1.0, 2.0],
      random_seed: parseInt(seed, 10) || 42,
    })
  }

  const handleRunAll = () => {
    runMutation.mutate({
      drift_types: ALL_DRIFT_TYPES.map((d) => d.id),
      dataset_id: selectedDatasetId || undefined,
      sample_sizes: [1000, 5000],
      magnitudes: [0.5, 1.0, 2.0],
      random_seed: parseInt(seed, 10) || 42,
    })
  }

  const recentResults: ExperimentResultRecord[] = resultsData?.items ?? []
  const datasets = datasetsData ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Experiments"
        title="Experiments"
        subtitle="Controlled drift-injection framework — 11 deterministic, reproducible injectors (seed=42)"
        actions={
          <>
            <select
              className="select min-w-[200px]"
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
            >
              <option value="">Synthetic data (auto-generated)</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {d.is_baseline ? '(baseline)' : ''}
                </option>
              ))}
            </select>
            <input
              className="input max-w-[120px]"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="Seed"
              aria-label="Random seed"
            />
            <button
              className="btn btn-primary"
              disabled={runMutation.isPending}
              onClick={handleRunAll}
            >
              {runMutation.isPending ? 'Running…' : 'Run Full Suite'}
            </button>
          </>
        }
      />

      {runStatus && (
        <RunStatusBanner
          status={runStatus.status}
          summary={runStatus.msg}
          onDismiss={() => setRunStatus(null)}
        />
      )}

      <SectionCard title="Drift Injectors" subtitle="Select an injector to run, inspect parameters and results">
        <DataTable
          rowKey={(r) => r.id}
          columns={[
            { key: 'id', label: 'Injector ID', className: 'font-mono text-xs text-text-muted' },
            {
              key: 'name',
              label: 'Name',
              render: (r) => <div className="font-medium text-white">{r.name}</div>,
            },
            { key: 'description', label: 'Description', className: 'text-text-muted' },
            {
              key: 'severity',
              label: 'Expected Severity',
              render: (r) => <SeverityBadge severity={r.severity} />,
            },
            {
              key: 'actions',
              label: '',
              className: 'text-right',
              render: (r) => (
                <div className="flex justify-end gap-2">
                  <button
                    className="btn btn-primary !py-1 !px-2 text-xs"
                    disabled={runMutation.isPending}
                    onClick={() => handleRunSingle(r.id)}
                  >
                    {runMutation.isPending ? '…' : 'Run'}
                  </button>
                </div>
              ),
            },
          ]}
          rows={ALL_DRIFT_TYPES}
        />
      </SectionCard>

      <SectionCard
        title="Recent Experiment Runs"
        subtitle={
          resultsLoading
            ? 'Loading…'
            : `${recentResults.length} result(s) — all with captured seed, params and timestamps`
        }
      >
        {recentResults.length === 0 && !resultsLoading ? (
          <div className="text-center text-text-muted py-10 text-sm">
            No experiment runs yet — click "Run" on an injector above to get started.
          </div>
        ) : (
          <DataTable
            rowKey={(r) => r.id}
            columns={[
              {
                key: 'id',
                label: 'Run ID',
                className: 'font-mono text-xs text-text-muted',
                render: (r) => r.id.slice(0, 8),
              },
              {
                key: 'drift_type',
                label: 'Drift Type',
                render: (r) => <span className="badge bg-surface-2">{r.drift_type}</span>,
              },
              {
                key: 'drift_magnitude',
                label: 'Magnitude',
                className: 'font-mono text-text-muted',
                render: (r) => formatNumber(r.drift_magnitude),
              },
              {
                key: 'sample_size',
                label: 'Sample Size',
                className: 'font-mono text-right text-text-muted',
                render: (r) => r.sample_size?.toLocaleString() ?? '—',
              },
              {
                key: 'psi_score',
                label: 'PSI',
                className: 'font-mono text-right',
                render: (r) => <span>{r.psi_score != null ? formatNumber(r.psi_score, 3) : '—'}</span>,
              },
              {
                key: 'kl_score',
                label: 'KL',
                className: 'font-mono text-right',
                render: (r) => <span>{r.kl_score != null ? formatNumber(r.kl_score, 3) : '—'}</span>,
              },
              {
                key: 'ks_statistic',
                label: 'KS',
                className: 'font-mono text-right',
                render: (r) => <span>{r.ks_statistic != null ? formatNumber(r.ks_statistic, 3) : '—'}</span>,
              },
              {
                key: 'execution_time_ms',
                label: 'Exec Time',
                className: 'text-text-muted text-right',
                render: (r) => r.execution_time_ms != null ? `${formatNumber(r.execution_time_ms, 1)} ms` : '—',
              },
              {
                key: 'created_at',
                label: 'Run At',
                className: 'text-text-muted whitespace-nowrap',
                render: (r) => r.created_at ? new Date(r.created_at).toLocaleString() : '—',
              },
            ]}
            rows={recentResults}
          />
        )}
      </SectionCard>
    </div>
  )
}
