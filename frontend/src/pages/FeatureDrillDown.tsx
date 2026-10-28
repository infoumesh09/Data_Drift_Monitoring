import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PageHeader, SectionCard, SeverityBadge } from '@/components/ui'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ResponsiveContainer,
} from 'recharts'
import { driftApi } from '@/services/api'

const TOOLTIP_STYLE = {
  contentStyle: { background: '#111827', border: '1px solid #273449', borderRadius: 8, fontSize: 12 },
}

export default function FeatureDrillDown() {
  const { feature } = useParams<{ feature: string }>()
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['drift-feature-history', feature],
    queryFn: () => (feature ? driftApi.featureHistory(feature) : Promise.resolve(null)),
    enabled: !!feature,
    retry: false,
  })

  const hasData = data?.has_data

  const scores = data?.latest_scores
  const psiVal: number = scores?.psi ?? 0
  const klVal: number = scores?.kl ?? 0
  const ksStatVal: number = scores?.ks_stat ?? 0
  const ksPVal: number = scores?.ks_p ?? 1.0
  const nullRateVal: number = scores?.null_rate ?? 0
  const featureType: string = data?.feature_class ?? 'unknown'
  const severity: string = scores?.severity ?? 'HEALTHY'

  const distChartData = useMemo(() => {
    if (!data?.distribution_chart || data.distribution_chart.length === 0) return []
    return data.distribution_chart.map((d: any) => ({
      bin: d.bin,
      Baseline: d.baseline,
      Current: d.current,
    }))
  }, [data])

  const historyData = useMemo(() => {
    if (!data?.history || data.history.length === 0) return []
    return data.history.map((h: any, i: number) => ({
      run: `Run ${i + 1}`,
      timestamp: h.timestamp ? new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `R${i + 1}`,
      PSI: h.psi,
      KL: h.kl,
      KS: h.ks_stat,
    }))
  }, [data])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={`Drift Monitoring  /  ${feature ?? 'feature'}`}
          title={feature ? `Feature: ${feature}` : 'Feature Drill-Down'}
          subtitle="Loading feature distribution and history…"
        />
        <div className="card p-12 text-center text-text-muted">Loading metrics…</div>
      </div>
    )
  }

  if (!hasData) {
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={`Drift Monitoring  /  ${feature ?? 'feature'}`}
          title={feature ? `Feature: ${feature}` : 'Feature Drill-Down'}
          subtitle="Baseline vs current distributions and statistical drift metrics"
          actions={
            <button className="btn" onClick={() => navigate('/drift-monitoring')}>
              ← Back to Drift Monitoring
            </button>
          }
        />
        <div className="card p-10 text-center space-y-4 border-dashed">
          <div className="text-white font-medium text-lg">No detection data found for "{feature}"</div>
          <p className="text-sm text-text-muted max-w-md mx-auto">
            This feature has not been analyzed in any drift detection run yet. Run drift detection between a baseline dataset and current dataset to generate distribution overlays, statistical tests, and historical trends.
          </p>
          <button className="btn btn-primary inline-flex" onClick={() => navigate('/drift-monitoring')}>
            Go to Drift Detection
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={`Drift Monitoring  /  ${feature ?? 'feature'}`}
        title={`Feature: ${feature}`}
        subtitle="Baseline vs current distributions plus PSI, KL divergence, KS test, and null-rate metrics"
        actions={
          <div className="flex items-center gap-2">
            <button className="btn" onClick={() => navigate('/drift-monitoring')}>← Back</button>
            <button className="btn btn-primary" onClick={() => navigate(`/ai-diagnosis?feature=${encodeURIComponent(feature || '')}`)}>
              Root Cause Analysis
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: 'Feature Class', value: featureType, tone: 'bg-brand-soft/20 text-brand' },
          { label: 'PSI Score', value: psiVal.toFixed(3), tone: psiVal >= 0.25 ? 'text-severity-high' : '' },
          { label: 'KL Divergence', value: klVal.toFixed(3), tone: klVal >= 0.5 ? 'text-severity-critical' : '' },
          { label: 'KS Stat', value: featureType === 'numeric' ? ksStatVal.toFixed(3) : 'N/A', tone: '' },
          { label: 'KS p-value', value: featureType === 'numeric' ? ksPVal.toFixed(4) : 'N/A', tone: ksPVal < 0.05 ? 'text-severity-critical' : '' },
          { label: 'Null Rate (curr)', value: `${(nullRateVal * 100).toFixed(1)}%`, tone: nullRateVal > 0.1 ? 'text-severity-high' : '' },
        ].map((m) => (
          <div key={m.label} className="card p-4">
            <div className="text-xs text-text-muted mb-1">{m.label}</div>
            <div className={`font-mono text-lg font-semibold ${m.tone || 'text-white'}`}>{m.value}</div>
          </div>
        ))}
      </div>

      <SectionCard
        title="Distribution Comparison"
        subtitle="Baseline (blue) vs current (orange) distribution over baseline-derived bins"
      >
        {distChartData.length > 0 ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distChartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                <XAxis dataKey="bin" stroke="#9ca3af" fontSize={10} angle={-25} textAnchor="end" height={50} />
                <YAxis stroke="#9ca3af" fontSize={11} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Baseline" fill="#3b82f6" fillOpacity={0.6} />
                <Bar dataKey="Current" fill="#f97316" fillOpacity={0.6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-center py-8 text-sm text-text-muted">
            No bin distribution data available for this feature.
          </div>
        )}
      </SectionCard>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <SectionCard
          title="Statistical Drift History"
          subtitle={
            historyData.length > 1
              ? `Historical trajectory across ${historyData.length} detection runs`
              : 'Historical trajectory (1 run recorded)'
          }
        >
          {historyData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" stroke="#9ca3af" fontSize={11} />
                  <YAxis stroke="#9ca3af" fontSize={11} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="PSI" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="KL" stroke="#a855f7" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-center py-8 text-sm text-text-muted">
              No historical trajectory available.
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="KS Test History"
          subtitle="Empirical cumulative distribution distance across runs"
        >
          {historyData.length > 0 && featureType === 'numeric' ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" stroke="#9ca3af" fontSize={11} />
                  <YAxis stroke="#9ca3af" fontSize={11} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="KS" stroke="#f97316" strokeWidth={2} dot={{ r: 4 }} name="KS Stat (D)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-center py-8 text-sm text-text-muted">
              {featureType === 'categorical'
                ? 'KS test is continuous-only and not applicable for categorical features.'
                : 'No historical KS data available.'}
            </div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Severity & Diagnostic Summary" subtitle={`Assessment for ${feature}`}>
        <div className="p-4 rounded-xl border border-border bg-surface-2/40 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-white">Evaluated Drift Severity</span>
            <SeverityBadge severity={severity} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-2 border-t border-border/50">
            <div>
              <span className="text-text-muted">PSI Severity Rule: </span>
              <span className="font-mono text-white">
                {psiVal >= 0.25 ? 'High (≥0.25)' : psiVal >= 0.1 ? 'Moderate (0.1–0.25)' : 'Negligible (<0.1)'}
              </span>
            </div>
            <div>
              <span className="text-text-muted">KS Statistical Significance: </span>
              <span className="font-mono text-white">
                {featureType === 'numeric'
                  ? ksPVal < 0.05
                    ? `p=${ksPVal.toFixed(4)} (Significant)`
                    : `p=${ksPVal.toFixed(4)} (Not Significant)`
                  : 'N/A (Categorical)'}
              </span>
            </div>
            <div>
              <span className="text-text-muted">Null Rate Status: </span>
              <span className="font-mono text-white">
                {(nullRateVal * 100).toFixed(1)}% ({nullRateVal > 0.1 ? 'Elevation Detected' : 'Nominal'})
              </span>
            </div>
          </div>
        </div>
      </SectionCard>
    </div>
  )
}
