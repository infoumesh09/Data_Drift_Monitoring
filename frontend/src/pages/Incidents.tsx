import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { driftApi } from '@/services/api'
import { SectionCard, PageHeader, SeverityBadge, DataTable } from '@/components/ui'
import { formatDate, formatNumber } from '@/lib/utils'

const STATUS_OPTIONS = ['all', 'OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']
const SEVERITY_OPTIONS = ['all', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

// -------------------------------------------------------------------------
// Update Status modal
// -------------------------------------------------------------------------
function UpdateStatusModal({
  incident,
  onClose,
  onUpdated,
}: {
  incident: any
  onClose: () => void
  onUpdated: () => void
}) {
  const [status, setStatus] = useState<string>(incident.status)
  const [notes, setNotes] = useState<string>(incident.resolution_notes ?? '')
  const [error, setError] = useState('')

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => driftApi.updateIncident(id, data),
    onSuccess: () => { onUpdated(); onClose() },
    onError: (err: Error) => setError(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const id = incident.db_id ?? incident.id
    if (!id) { setError('Cannot update — incident has no DB id.'); return }
    updateMutation.mutate({ id, data: { status, resolution_notes: notes || undefined } })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
    >
      <div
        className="card w-full max-w-md p-6 space-y-5"
        role="dialog"
        aria-modal="true"
        aria-labelledby="update-status-title"
      >
        <div className="flex items-center justify-between">
          <h2 id="update-status-title" className="text-lg font-semibold text-white">
            Update Incident
          </h2>
          <button className="text-text-muted hover:text-white text-xl" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <p className="text-sm text-text-muted font-mono">{incident.id}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs text-text-muted uppercase tracking-wider font-semibold" htmlFor="inc-status">
              New Status
            </label>
            <select
              id="inc-status"
              className="select w-full"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-text-muted uppercase tracking-wider font-semibold" htmlFor="inc-notes">
              Resolution Notes
            </label>
            <textarea
              id="inc-notes"
              className="input w-full h-20 resize-none"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes about resolution…"
            />
          </div>

          {error && <p className="text-xs text-severity-critical">{error}</p>}

          <div className="flex gap-3 justify-end">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// -------------------------------------------------------------------------
// Main page
// -------------------------------------------------------------------------
export default function Incidents() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [editingIncident, setEditingIncident] = useState<any>(null)
  const [showNewIncident, setShowNewIncident] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['drift-incidents', statusFilter],
    queryFn: () => driftApi.incidents(statusFilter !== 'all' ? statusFilter : undefined),
    retry: false,
  })

  let rows = data ?? []

  if (severityFilter !== 'all') {
    rows = rows.filter((r) => r.severity?.toUpperCase() === severityFilter)
  }

  const handleUpdated = () => {
    qc.invalidateQueries({ queryKey: ['drift-incidents'] })
  }

  return (
    <div className="space-y-6">
      {editingIncident && (
        <UpdateStatusModal
          incident={editingIncident}
          onClose={() => setEditingIncident(null)}
          onUpdated={handleUpdated}
        />
      )}

      <PageHeader
        breadcrumb="Incidents"
        title="Incidents"
        subtitle="Track and triage active drift incidents across monitored pipelines"
        actions={
          <>
            <select
              className="select min-w-[160px]"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by status"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? 'All statuses' : s.replace('_', ' ')}
                </option>
              ))}
            </select>
            <select
              className="select min-w-[140px]"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              aria-label="Filter by severity"
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? 'All severities' : s}
                </option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={() => navigate('/drift-monitoring')}>
              + Run Detection
            </button>
          </>
        }
      />

      {rows.length === 0 && !isLoading && (
        <div className="card p-10 text-center space-y-3 border-dashed">
          <div className="text-white font-medium text-lg">No drift incidents recorded</div>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Incidents are automatically triggered when drift detection calculates HIGH or CRITICAL severity anomalies across monitored features.
          </p>
          <button className="btn btn-primary inline-flex" onClick={() => navigate('/drift-monitoring')}>
            Go to Drift Detection
          </button>
        </div>
      )}

      <SectionCard
        title={statusFilter === 'all' ? 'All Incidents' : `${statusFilter.replace('_', ' ')} Incidents`}
        subtitle={
          isLoading
            ? 'Loading…'
            : `${rows.length} incident${rows.length !== 1 ? 's' : ''}`
        }
      >
        <DataTable
          rowKey={(r) => r.id}
          onRowClick={(r) => navigate(`/ai-diagnosis?incident_id=${r.id}`)}
          columns={[
            {
              key: 'id',
              label: 'Incident ID',
              render: (r) => <span className="font-mono text-white">{r.id}</span>,
            },
            {
              key: 'summary',
              label: 'Summary',
              render: (r) => <div className="max-w-xl text-sm">{r.summary}</div>,
            },
            {
              key: 'severity',
              label: 'Severity',
              render: (r) => <SeverityBadge severity={r.severity} />,
            },
            {
              key: 'feature',
              label: 'Affected Feature',
              render: (r) => <span className="font-mono text-text">{r.feature}</span>,
            },
            {
              key: 'metric',
              label: 'Metric',
              render: (r) => (
                <span className="font-mono">
                  {r.metric} {formatNumber(r.score)}
                </span>
              ),
            },
            {
              key: 'timestamp',
              label: 'Detected',
              className: 'whitespace-nowrap text-text-muted',
              render: (r) => formatDate(r.timestamp),
            },
            {
              key: 'status',
              label: 'Status',
              render: (r) => (
                <span
                  className={
                    'badge ' +
                    (r.status === 'OPEN'
                      ? 'text-severity-critical border-severity-critical/30 bg-severity-critical/10'
                      : r.status === 'IN_PROGRESS'
                      ? 'text-severity-medium border-severity-medium/30 bg-severity-medium/10'
                      : 'text-severity-healthy border-severity-healthy/30 bg-severity-healthy/10')
                  }
                >
                  {r.status.replace('_', ' ')}
                </span>
              ),
            },
            {
              key: 'actions',
              label: '',
              className: 'text-right',
              render: (r) => (
                <button
                  className="btn !py-1 !px-2 text-xs"
                  onClick={(e) => {
                    e.stopPropagation()
                    setEditingIncident(r)
                  }}
                  aria-label="Update status"
                >
                  Update
                </button>
              ),
            },
          ]}
          rows={rows}
        />
      </SectionCard>
    </div>
  )
}
