import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { SectionCard, PageHeader, SeverityBadge } from '@/components/ui'
import { driftApi, aiApi } from '@/services/api'
import type { DiagnosisResult } from '@/services/api'
import type { IncidentSummary } from '@/types'

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" aria-label="Loading" />
      <span className="ml-3 text-sm text-text-muted">Evaluating heuristic evidence and ranking hypotheses…</span>
    </div>
  )
}

export default function AIDiagnosis() {
  const [searchParams] = useSearchParams()
  const incidentIdParam = searchParams.get('incident_id')
  const featureParam = searchParams.get('feature')

  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(incidentIdParam || '')
  const [diagnosis, setDiagnosis] = useState<DiagnosisResult | null>(null)
  const [selectedIncident, setSelectedIncident] = useState<IncidentSummary | null>(null)

  const { data: incidents, isLoading: isIncidentsLoading } = useQuery({
    queryKey: ['drift-incidents'],
    queryFn: () => driftApi.incidents(),
    retry: false,
  })

  const diagnoseMutation = useMutation({
    mutationFn: aiApi.diagnose,
    onSuccess: (data) => {
      setDiagnosis(data)
    },
  })

  const incidentList = incidents ?? []

  // Auto-select incident from query param once loaded
  useEffect(() => {
    if (incidentIdParam && incidentList.length > 0) {
      const found = incidentList.find(
        (i) => i.id === incidentIdParam || (i as any).db_id === incidentIdParam,
      )
      if (found) {
        setSelectedIncident(found)
        setSelectedIncidentId(found.id)
        // Automatically run diagnosis
        diagnoseMutation.mutate({
          feature: found.feature,
          psi_score: found.metric === 'PSI' ? found.score : undefined,
          kl_score: found.metric === 'KL' ? found.score : undefined,
          incident_id: (found as any).db_id || found.id,
        })
      }
    } else if (featureParam && !incidentIdParam) {
      // Find incident matching feature if any
      const found = incidentList.find(
        (i) => i.feature?.toLowerCase() === featureParam.toLowerCase(),
      )
      if (found) {
        setSelectedIncident(found)
        setSelectedIncidentId(found.id)
        diagnoseMutation.mutate({
          feature: found.feature,
          psi_score: found.metric === 'PSI' ? found.score : undefined,
          kl_score: found.metric === 'KL' ? found.score : undefined,
          incident_id: (found as any).db_id || found.id,
        })
      } else {
        // Run diagnosis on feature name directly
        diagnoseMutation.mutate({
          feature: featureParam,
        })
      }
    }
  }, [incidentIdParam, featureParam, incidentList])

  const handleIncidentChange = (id: string) => {
    setSelectedIncidentId(id)
    const found = incidentList.find((i) => i.id === id || (i as any).db_id === id) ?? null
    setSelectedIncident(found)
    setDiagnosis(null)
  }

  const handleRunDiagnosis = () => {
    if (!selectedIncident && !featureParam) return
    const inc = selectedIncident as any
    diagnoseMutation.mutate({
      feature: inc?.feature || featureParam || undefined,
      psi_score: inc?.metric === 'PSI' ? inc.score : undefined,
      kl_score: inc?.metric === 'KL' ? inc.score : undefined,
      incident_id: inc?.db_id || inc?.id || undefined,
    })
  }

  const displayedDiagnosis = diagnosis
  const incident = selectedIncident

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Root Cause Analysis"
        title="Root Cause Analysis (AI-Assisted)"
        subtitle="Deterministic evidence-grounded diagnosis ranking root cause hypotheses and remediation steps"
        actions={
          <div className="flex items-center gap-2">
            <select
              className="select min-w-[280px]"
              value={selectedIncidentId}
              onChange={(e) => handleIncidentChange(e.target.value)}
              aria-label="Select incident"
            >
              <option value="">Select an incident to diagnose…</option>
              {incidentList.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.id} — {i.feature} ({i.severity})
                </option>
              ))}
            </select>
            <button
              className="btn btn-primary"
              disabled={(!selectedIncidentId && !featureParam) || diagnoseMutation.isPending}
              onClick={handleRunDiagnosis}
            >
              {diagnoseMutation.isPending ? 'Diagnosing…' : 'Run Diagnostic Analysis'}
            </button>
          </div>
        }
      />

      {diagnoseMutation.isPending && <LoadingSpinner />}

      {diagnoseMutation.isError && (
        <div className="rounded-xl border border-severity-critical/30 bg-severity-critical/10 px-4 py-3 text-sm text-severity-critical">
          Diagnosis failed: {(diagnoseMutation.error as Error).message}
        </div>
      )}

      {!diagnoseMutation.isPending && !displayedDiagnosis && (
        <div className="card p-10 text-center space-y-3 border-dashed">
          <div className="text-white font-medium text-lg">No incident selected for root cause analysis</div>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            Select an active incident from the dropdown above (or navigate here directly from an Incident or Feature Drill-Down) and click "Run Diagnostic Analysis" to evaluate observed evidence, rank causal hypotheses, and generate concrete remediation actions.
          </p>
        </div>
      )}

      {!diagnoseMutation.isPending && displayedDiagnosis && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <SectionCard
              title="Observed Evidence"
              subtitle="Empirical facts evaluated by the diagnostic engine"
            >
              <ul className="space-y-3">
                {displayedDiagnosis.observed_evidence.map((e, i) => (
                  <li key={i} className="flex items-start gap-3 p-3 rounded-lg bg-surface-2/40 border border-border">
                    <SeverityBadge severity={e.severity} showDot={false} />
                    <div className="text-sm text-white flex-1">{e.text}</div>
                    <span className="badge text-[11px] text-text-muted">{e.metric}</span>
                  </li>
                ))}
              </ul>
            </SectionCard>

            <SectionCard
              title="Hypotheses (Ranked)"
              subtitle="Causal hypotheses scored using deterministic heuristic evaluation"
            >
              <ol className="space-y-4">
                {displayedDiagnosis.hypotheses.map((h) => (
                  <li key={h.rank} className="p-4 rounded-xl border border-border">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div>
                        <div className="text-xs text-text-muted mb-1">Hypothesis #{h.rank}</div>
                        <div className="font-semibold text-white">{h.title}</div>
                      </div>
                      <div className="text-right">
                        <SeverityBadge
                          severity={h.severity}
                          label={`Heuristic Score: ${Math.round(h.confidence * 100)}%`}
                        />
                      </div>
                    </div>
                    <p className="text-sm text-text-muted leading-relaxed">{h.reasoning}</p>
                  </li>
                ))}
              </ol>
            </SectionCard>

            <SectionCard
              title="Targeted Recommendations"
              subtitle="Actionable engineering and operational steps ordered by priority"
            >
              <ul className="space-y-3">
                {displayedDiagnosis.recommendations.map((r, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-3 p-3 rounded-lg border border-border hover:bg-surface-2/40 transition-colors"
                  >
                    <div className="w-7 h-7 rounded-md bg-brand-soft/30 border border-brand/30 text-brand font-semibold text-xs flex items-center justify-center shrink-0">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-3 mb-1">
                        <div className="font-medium text-white">{r.title}</div>
                        <SeverityBadge severity={r.priority} showDot={false} />
                      </div>
                      <p className="text-sm text-text-muted">{r.body}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>

          <div className="space-y-6">
            <SectionCard title="Incident Diagnostic Report" subtitle="Structured synthesis for postmortem">
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-text-muted">Incident</dt>
                  <dd className="font-mono">{incident?.id ?? (featureParam ? `FEAT-${featureParam}` : 'Manual Query')}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-text-muted">Severity</dt>
                  <dd>
                    <SeverityBadge severity={incident?.severity ?? 'HIGH'} />
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-text-muted">Affected feature</dt>
                  <dd className="font-mono text-white">{incident?.feature ?? featureParam ?? 'N/A'}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-text-muted">Most probable cause</dt>
                  <dd className="text-severity-high font-medium text-right max-w-[180px]">
                    {displayedDiagnosis.most_probable_cause}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-text-muted">Heuristic Confidence</dt>
                  <dd className="text-white font-semibold">
                    {Math.round(displayedDiagnosis.confidence * 100)}%
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-text-muted">Diagnostic Engine</dt>
                  <dd className="text-text-muted text-xs">{displayedDiagnosis.provider}</dd>
                </div>
              </dl>
              {displayedDiagnosis.evidence_summary && (
                <p className="mt-3 text-xs text-text-muted border-t border-border pt-3">
                  {displayedDiagnosis.evidence_summary}
                </p>
              )}
              <div className="flex gap-2 mt-4">
                <button
                  className="btn flex-1 text-xs"
                  onClick={() => {
                    const json = JSON.stringify(displayedDiagnosis, null, 2)
                    navigator.clipboard.writeText(json).catch(() => null)
                  }}
                >
                  Copy JSON
                </button>
              </div>
            </SectionCard>

            <SectionCard title="Evidence Sources Evaluated" subtitle="Integrated observational signals">
              <ul className="space-y-2 text-sm">
                {[
                  'Population Stability Index (PSI)',
                  'Kullback-Leibler Divergence (KL)',
                  'Kolmogorov-Smirnov Test (KS D & p-val)',
                  'Null-Rate Shift & Relative Multiplier',
                  'Schema Drift & Type Changes',
                  'Historical Incident Recurrence',
                ].map((t) => (
                  <li key={t} className="flex items-center gap-2 p-2 rounded-md bg-surface-2/40 text-text-muted">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand" /> {t}
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>
        </div>
      )}
    </div>
  )
}
