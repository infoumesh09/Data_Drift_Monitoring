import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { pipelinesApi } from '@/services/api'
import { SectionCard, PageHeader, SeverityBadge, DataTable } from '@/components/ui'
import { formatDate, formatNumber } from '@/lib/utils'
import type { PipelineSummary } from '@/types'

function FilterIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 5h18M6 12h12M10 19h4" />
    </svg>
  )
}

// -------------------------------------------------------------------------
// Register Pipeline inline form (slide-down panel)
// -------------------------------------------------------------------------
function RegisterPipelineForm({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [name, setName] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [destinationType, setDestinationType] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: pipelinesApi.create,
    onSuccess: () => {
      onCreated()
      onClose()
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim()) { setError('Pipeline name is required.'); return }
    if (!sourceType.trim()) { setError('Source type is required.'); return }
    createMutation.mutate({ name: name.trim(), source_type: sourceType.trim(), destination_type: destinationType.trim() || undefined, description: description.trim() || undefined })
  }

  return (
    <div className="card p-5 border-brand/30 bg-brand-soft/5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white">Register New Pipeline</h3>
        <button className="text-text-muted hover:text-white" onClick={onClose} aria-label="Close">✕</button>
      </div>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-xs text-text-muted font-semibold uppercase tracking-wider" htmlFor="pipe-name">
            Pipeline Name *
          </label>
          <input
            id="pipe-name"
            className="input w-full"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Customer Transactions ETL"
            autoFocus
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-muted font-semibold uppercase tracking-wider" htmlFor="pipe-source">
            Source Type *
          </label>
          <input
            id="pipe-source"
            className="input w-full"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            placeholder="PostgreSQL, Kafka, S3…"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-muted font-semibold uppercase tracking-wider" htmlFor="pipe-dest">
            Destination Type
          </label>
          <input
            id="pipe-dest"
            className="input w-full"
            value={destinationType}
            onChange={(e) => setDestinationType(e.target.value)}
            placeholder="Snowflake, BigQuery, Redshift…"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-muted font-semibold uppercase tracking-wider" htmlFor="pipe-desc">
            Description
          </label>
          <input
            id="pipe-desc"
            className="input w-full"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
          />
        </div>

        {error && (
          <div className="sm:col-span-2 text-xs text-severity-critical">{error}</div>
        )}

        <div className="sm:col-span-2 flex gap-3 justify-end">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? 'Registering…' : 'Register Pipeline'}
          </button>
        </div>
      </form>
    </div>
  )
}

// -------------------------------------------------------------------------
// Main page
// -------------------------------------------------------------------------
export default function Pipelines() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [status, setStatus] = useState<string>('all')
  const [showForm, setShowForm] = useState(false)

  // Query real DB pipelines
  const { data: dbPipelines, isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: pipelinesApi.list,
    retry: false,
  })

  const allRows: PipelineSummary[] = dbPipelines ?? []
  const filtered = status === 'all' ? allRows : allRows.filter((r) => r.status === status)

  const handleCreated = () => {
    qc.invalidateQueries({ queryKey: ['pipelines'] })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Pipelines"
        title="Pipelines"
        subtitle={`${allRows.length} monitored data pipelines`}
        actions={
          <button
            className="btn btn-primary"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? '✕ Cancel' : '+ Register Pipeline'}
          </button>
        }
      />

      {showForm && (
        <RegisterPipelineForm onClose={() => setShowForm(false)} onCreated={handleCreated} />
      )}

      {allRows.length === 0 && !isLoading && !showForm && (
        <div className="card p-8 text-center space-y-3 border-dashed">
          <div className="text-white font-medium text-base">No pipelines registered yet</div>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Register your first data pipeline to begin tracking upstream and downstream data health, schema changes, and statistical drift.
          </p>
          <button className="btn btn-primary inline-flex" onClick={() => setShowForm(true)}>
            + Register Pipeline
          </button>
        </div>
      )}

      <SectionCard
        title=""
        actions={
          <div className="flex items-center gap-3 w-full justify-between">
            <div className="flex items-center gap-2">
              <FilterIcon className="w-4 h-4 text-text-muted" />
              <select
                className="select min-w-[180px]"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="all">All statuses</option>
                <option value="Healthy">Healthy</option>
                <option value="Warning">Warning</option>
                <option value="Critical">Critical</option>
                <option value="active">Active</option>
              </select>
            </div>
            <div className="text-xs text-text-muted">{filtered.length} pipelines</div>
          </div>
        }
      >
        <DataTable
          rowKey={(r) => r.id}
          onRowClick={() => navigate('/drift-monitoring')}
          columns={[
            {
              key: 'pipeline',
              label: 'Pipeline',
              render: (r) => (
                <div>
                  <div className="font-medium text-white">{r.name}</div>
                  <div className="text-xs text-text-muted">{(r as any).project ?? r.source_type ?? ''}</div>
                </div>
              ),
            },
            {
              key: 'source',
              label: 'Source',
              className: 'text-text-muted',
              render: (r) => (r as any).source ?? (r as any).source_type ?? '—',
            },
            {
              key: 'destination',
              label: 'Destination',
              className: 'text-text-muted',
              render: (r) => (r as any).destination ?? (r as any).destination_type ?? '—',
            },
            {
              key: 'last_successful_run',
              label: 'Last Successful Run',
              className: 'text-text-muted whitespace-nowrap',
              render: (r) => {
                const ts = (r as any).last_successful_run
                return ts ? formatDate(ts) : '—'
              },
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
              render: (r) => {
                const n = (r as any).mcfe_count
                return n != null ? formatNumber(n, 0) : '—'
              },
            },
          ]}
          rows={filtered}
        />
      </SectionCard>
    </div>
  )
}
