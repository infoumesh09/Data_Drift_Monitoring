import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { SectionCard, PageHeader, StatCard } from '@/components/ui'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from 'recharts'
import { experimentsApi } from '@/services/api'
import type { AlgorithmComparisonData } from '@/services/api'

const TOOLTIP_STYLE = {
  contentStyle: { background: '#111827', border: '1px solid #273449', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#fff' },
}

export default function AlgorithmComparison() {
  const navigate = useNavigate()
  const { data: rawData, isLoading } = useQuery({
    queryKey: ['algorithm-comparison'],
    queryFn: experimentsApi.algorithmComparison,
    retry: false,
  })

  const d = rawData
  const hasRealData = !!d?.has_data && (d?.total_experiments ?? 0) > 0

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Algorithm Comparison"
        title="Algorithm Comparison"
        subtitle={
          hasRealData
            ? `PSI vs KL Divergence vs KS Test — aggregated across ${d.total_experiments.toLocaleString()} empirical experiment runs`
            : 'PSI vs KL Divergence vs KS Test — empirical benchmark comparison'
        }
        actions={
          <button className="btn btn-primary" onClick={() => navigate('/experiments')}>
            + Run Experiments
          </button>
        }
      />

      {isLoading && (
        <div className="card p-12 text-center text-text-muted text-sm">Loading comparison benchmarks…</div>
      )}

      {!hasRealData && !isLoading && (
        <div className="card p-10 text-center space-y-4 border-dashed">
          <div className="text-white font-medium text-lg">No experiment benchmarks recorded yet</div>
          <p className="text-sm text-text-muted max-w-xl mx-auto">
            Algorithm comparison charts are calculated dynamically from real experiment runs with ground-truth drift labels. Run experiments across varying sample sizes, drift magnitudes, and drift types to generate empirical sensitivity curves, false positive/negative rates, latency benchmarks, and detector agreement matrices.
          </p>
          <button className="btn btn-primary inline-flex" onClick={() => navigate('/experiments')}>
            Go to Experiments Suite
          </button>
        </div>
      )}

      {hasRealData && d && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard title="Experiments Run" value={d.summary.experiments_run.toLocaleString()} />
            <StatCard
              title="Agreement (all 3)"
              value={`${d.agreement.all_agree_pct}%`}
              accent="health"
            />
            <StatCard title="Avg Detection Latency" value={`${d.summary.avg_execution_ms} ms`} />
            <StatCard
              title="Total Samples Analyzed"
              value={
                d.summary.total_samples >= 1_000_000
                  ? `${(d.summary.total_samples / 1_000_000).toFixed(1)}M`
                  : d.summary.total_samples.toLocaleString()
              }
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <SectionCard
              title="Drift Magnitude vs Score"
              subtitle="Mean detector scores grouped by drift magnitude"
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={d.mag_data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                    <XAxis dataKey="drift" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip {...TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="monotone" dataKey="PSI" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="KL" stroke="#a855f7" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="KS" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard title="Detection Sensitivity Radar" subtitle="Relative sensitivity across drift modalities">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={d.radar_data}>
                    <PolarGrid stroke="#1f2937" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <PolarRadiusAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
                    <Radar name="PSI" dataKey="PSI" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
                    <Radar name="KL" dataKey="KL" stroke="#a855f7" fill="#a855f7" fillOpacity={0.2} />
                    <Radar name="KS" dataKey="KS" stroke="#f97316" fill="#f97316" fillOpacity={0.15} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE.contentStyle} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard
              title="Computational Cost"
              subtitle="Measured execution latency (ms) across sample sizes"
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={d.latency_data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip {...TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="PSI" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="KL" fill="#a855f7" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="KS" fill="#f97316" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>

            <SectionCard
              title="False Positive / False Negative Rates"
              subtitle="Empirical error rates evaluated against ground truth labels (%)"
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={d.error_data}
                    margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                    layout="vertical"
                  >
                    <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                    <XAxis type="number" stroke="#9ca3af" fontSize={12} unit="%" />
                    <YAxis dataKey="method" type="category" stroke="#9ca3af" fontSize={12} width={48} />
                    <Tooltip {...TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="fp" name="False Positive %" fill="#fbbf24" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="fn" name="False Negative %" fill="#ef4444" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </SectionCard>
          </div>

          <SectionCard
            title="Algorithm Agreement"
            subtitle="Observed consensus between PSI, KL and KS detector verdicts"
          >
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
              {[
                { label: 'All three agree', pct: d.agreement.all_agree_pct, color: 'bg-severity-healthy' },
                { label: 'PSI + KL agree', pct: d.agreement.psi_kl_pct, color: 'bg-brand' },
                { label: 'PSI + KS agree', pct: d.agreement.psi_ks_pct, color: 'bg-purple-500' },
                { label: 'Detectors disagree', pct: d.agreement.disagree_pct, color: 'bg-severity-medium' },
              ].map((b) => (
                <div key={b.label} className="p-4 rounded-xl border border-border bg-surface-2/40">
                  <div className="flex items-end justify-between mb-3">
                    <div className="text-2xl font-semibold text-white">{b.pct}%</div>
                    <div className={`w-2 h-8 rounded-full ${b.color}`} />
                  </div>
                  <div className="h-1.5 rounded-full bg-border overflow-hidden">
                    <div className={`h-full ${b.color}`} style={{ width: `${b.pct}%` }} />
                  </div>
                  <div className="mt-2 text-xs text-text-muted">{b.label}</div>
                </div>
              ))}
            </div>
          </SectionCard>
        </>
      )}
    </div>
  )
}
