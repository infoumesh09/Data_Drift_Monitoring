import { SectionCard, PageHeader } from '@/components/ui'

export default function Settings() {
  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb="Settings"
        title="Settings"
        subtitle="Statistical thresholds, severity rules, database persistence and diagnostic engine"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="card p-5">
            <h3 className="text-[15px] font-semibold text-white mb-1">DriftSense</h3>
            <p className="text-xs text-text-muted mb-4">Data Observability & Drift Monitoring Platform · v1.0.0</p>
            <dl className="text-sm space-y-2">
              <div className="flex justify-between"><dt className="text-text-muted">Environment</dt><dd>production-ready</dd></div>
              <div className="flex justify-between"><dt className="text-text-muted">API Base URL</dt><dd className="font-mono text-xs">/api/v1</dd></div>
              <div className="flex justify-between"><dt className="text-text-muted">Database</dt><dd className="font-mono text-xs">PostgreSQL (port 5432)</dd></div>
              <div className="flex justify-between"><dt className="text-text-muted">Diagnostic Engine</dt><dd className="text-xs">Deterministic Expert Rules</dd></div>
            </dl>
          </div>
          <nav className="card p-2 text-sm">
            {['Thresholds & Rules', 'Database & Storage', 'Statistical Methods', 'About'].map((s, i) => (
              <button
                key={s}
                className={
                  'w-full text-left px-3 py-2 rounded-md transition-colors ' +
                  (i === 0 ? 'bg-brand-soft/40 text-white font-medium' : 'hover:bg-surface-2 text-text-muted')
                }
              >
                {s}
              </button>
            ))}
          </nav>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <SectionCard title="Population Stability Index (PSI) Thresholds" subtitle="Standard baseline bins with [-inf, +inf] expansion and epsilon smoothing">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              {[
                { label: 'Healthy (≤)', value: 0.1, hint: 'Negligible population shift' },
                { label: 'Low (≤)', value: 0.2, hint: 'Slight shift detected' },
                { label: 'Medium (≤)', value: 0.25, hint: 'Moderate distribution shift' },
                { label: 'Critical (>)', value: 0.4, hint: 'Severe population drift' },
              ].map((t) => (
                <label key={t.label} className="block">
                  <div className="text-xs text-text-muted mb-1">{t.label}</div>
                  <input className="input w-full font-mono" defaultValue={t.value} type="number" step="0.01" readOnly />
                  <div className="text-[11px] text-text-subtle mt-1">{t.hint}</div>
                </label>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Kolmogorov-Smirnov (KS) Significance Thresholds" subtitle="Continuous two-sample test with Benjamini-Hochberg FDR correction">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: 'Alpha (Significance)', value: 0.05, hint: 'p < α rejects null hypothesis' },
                { label: 'Negligible Distance D (≤)', value: 0.1, hint: 'Statistical noise / negligible effect' },
                { label: 'Severe Distance D (>)', value: 0.3, hint: 'Substantial cumulative divergence' },
              ].map((t) => (
                <label key={t.label} className="block">
                  <div className="text-xs text-text-muted mb-1">{t.label}</div>
                  <input className="input w-full font-mono" defaultValue={t.value} type="number" step="0.01" readOnly />
                  <div className="text-[11px] text-text-subtle mt-1">{t.hint}</div>
                </label>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Null-Rate Shift Thresholds" subtitle="Signed delta and absolute change between baseline and current missing rates">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              {[
                { label: 'Healthy (≤)', value: '1.0 %', hint: 'Nominal fluctuation' },
                { label: 'Warning (≤)', value: '5.0 %', hint: 'Noticeable drop in completeness' },
                { label: 'High (≤)', value: '15.0 %', hint: 'Pipeline ingestion issue' },
                { label: 'Critical (>)', value: '30.0 %', hint: 'Major upstream failure' },
              ].map((t) => (
                <label key={t.label} className="block">
                  <div className="text-xs text-text-muted mb-1">{t.label}</div>
                  <input className="input w-full font-mono" defaultValue={t.value} readOnly />
                  <div className="text-[11px] text-text-subtle mt-1">{t.hint}</div>
                </label>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Diagnostic Engine Architecture" subtitle="Grounded, evidence-based causal analysis">
            <div className="space-y-3 text-sm text-text-muted leading-relaxed">
              <p>
                The DriftSense Root Cause Analysis engine operates as a deterministic, rules-based expert system grounded directly in verified database records (<span className="font-mono text-white text-xs">DetectionRun</span>, <span className="font-mono text-white text-xs">DriftEvent</span>, <span className="font-mono text-white text-xs">SchemaChange</span>, and <span className="font-mono text-white text-xs">Incident</span>).
              </p>
              <div className="p-3 rounded-lg border border-border bg-surface-2/40 text-xs text-text-subtle">
                No third-party cloud LLM API key is required. All hypothesis ranking and remediation advice are evaluated locally using rule priority engines with explicit rule identifiers (<span className="font-mono text-text">RULE-CRIT-SCHEMA</span>, <span className="font-mono text-text">RULE-CRIT-NULL</span>, <span className="font-mono text-text">RULE-CRIT-PSI</span>, <span className="font-mono text-text">RULE-HIGH-CONSENSUS</span>).
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
