import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { SectionCard, PageHeader, SeverityBadge, DataTable, StatCard } from '@/components/ui'
import { datasetsApi } from '@/services/api'
import { formatDate, formatNumber } from '@/lib/utils'
import type { DatasetSummary } from '@/types'

function avgNullRate(profile: DatasetSummary['profile']): string {
  if (!profile?.columns?.length) return '—'
  const avg =
    profile.columns.reduce((sum, c) => sum + (c.null_rate ?? 0), 0) / profile.columns.length
  return `${(avg * 100).toFixed(1)}%`
}

function monitoredFeatures(profile: DatasetSummary['profile']): number {
  if (!profile?.columns?.length) return 0
  return profile.columns.filter(
    (c) => c.feature_class === 'numerical' || c.feature_class === 'categorical',
  ).length
}

export default function Datasets() {
  const fileRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isBaseline, setIsBaseline] = useState(false)

  const { data: datasets = [], isLoading, error } = useQuery({
    queryKey: ['datasets'],
    queryFn: datasetsApi.list,
    retry: false,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => datasetsApi.upload(file, { is_baseline: isBaseline }),
    onSuccess: () => {
      setUploadError(null)
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : 'Upload failed')
      setUploadError(String(msg))
    },
  })

  const dbUnavailable =
    error &&
    String((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? error).includes(
      'connect',
    )

  const totalRows = datasets.reduce((sum, d) => sum + (d.row_count ?? 0), 0)

  const handleFile = (file: File | undefined) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Only CSV uploads are supported in Phase 2.')
      return
    }
    uploadMutation.mutate(file)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Datasets"
        title="Datasets"
        subtitle="Upload CSV data and run pandas profiling / drift detection against stored baselines"
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMutation.isPending}
          >
            {uploadMutation.isPending ? 'Uploading…' : '+ Upload CSV'}
          </button>
        }
      />

      {dbUnavailable && (
        <div className="rounded-lg border border-severity-medium/40 bg-severity-medium/10 px-4 py-3 text-sm text-severity-medium">
          PostgreSQL is not connected. Start the database with{' '}
          <code className="font-mono text-xs">docker compose up -d postgres</code> before uploading
          datasets.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 card p-5">
          <h3 className="text-[15px] font-semibold text-white mb-1">Upload a Dataset</h3>
          <p className="text-xs text-text-muted mb-4">
            CSV files are profiled with Pandas and stored via the storage abstraction (local →
            S3-ready).
          </p>

          <label
            className="block border-2 border-dashed border-border-2 rounded-xl p-8 text-center hover:border-brand/50 transition-colors cursor-pointer"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              handleFile(e.dataTransfer.files[0])
            }}
          >
            <div className="mx-auto w-12 h-12 rounded-xl bg-brand-soft/30 border border-brand/30 flex items-center justify-center mb-3">
              <svg
                className="w-6 h-6 text-brand"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className="text-sm font-medium text-white mb-1">Drop CSV here or click to browse</div>
            <div className="text-xs text-text-muted">Max 250 MB · Pandas profiling is automatic</div>
            <input
              ref={fileRef}
              className="hidden"
              type="file"
              accept=".csv"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </label>

          <label className="mt-4 flex items-center gap-2 text-sm text-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={isBaseline}
              onChange={(e) => setIsBaseline(e.target.checked)}
              className="rounded border-border"
            />
            Mark as baseline window dataset
          </label>

          {uploadError && (
            <p className="mt-3 text-xs text-severity-critical">{uploadError}</p>
          )}
          {uploadMutation.isSuccess && (
            <p className="mt-3 text-xs text-severity-healthy">Dataset uploaded and profiled successfully.</p>
          )}

          <div className="mt-5 grid grid-cols-3 gap-3 text-center">
            <StatCard title="Total" value={datasets.length} />
            <StatCard title="Baselines" value={datasets.filter((d) => d.is_baseline).length} />
            <StatCard title="Rows (total)" value={formatNumber(totalRows, 0)} />
          </div>
        </div>

        <div className="lg:col-span-2">
          <SectionCard
            title="Dataset Library"
            subtitle={
              isLoading
                ? 'Loading…'
                : datasets.length
                  ? `${datasets.length} uploaded dataset${datasets.length === 1 ? '' : 's'}`
                  : 'No datasets yet — upload a CSV to begin profiling'
            }
          >
            <DataTable
              rowKey={(r) => r.id}
              columns={[
                {
                  key: 'name',
                  label: 'Dataset',
                  render: (r) => (
                    <div>
                      <div className="font-mono text-white">{r.name}</div>
                      <div className="text-xs text-text-muted">
                        v{r.version}
                        {r.is_baseline ? ' · baseline' : ''}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'rows',
                  label: 'Rows',
                  className: 'font-mono text-right text-text-muted',
                  render: (r) => formatNumber(r.row_count, 0),
                },
                {
                  key: 'cols',
                  label: 'Cols',
                  className: 'font-mono text-right text-text-muted',
                  render: (r) => r.column_count,
                },
                {
                  key: 'features',
                  label: 'Features',
                  className: 'font-mono text-right text-text-muted',
                  render: (r) => monitoredFeatures(r.profile),
                },
                {
                  key: 'nulls',
                  label: 'Avg Null %',
                  className: 'text-right text-text-muted',
                  render: (r) => avgNullRate(r.profile),
                },
                {
                  key: 'health',
                  label: 'Baseline',
                  render: (r) => (
                    <SeverityBadge severity={r.is_baseline ? 'Healthy' : 'LOW'} />
                  ),
                },
                {
                  key: 'updated',
                  label: 'Updated',
                  className: 'text-xs text-text-muted whitespace-nowrap',
                  render: (r) => formatDate(r.updated_at),
                },
              ]}
              rows={datasets}
              empty="Upload a CSV file to populate the dataset library."
            />
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
