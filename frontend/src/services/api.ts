import axios from 'axios'
import type {
  HealthResponse,
  OverviewResponse,
  PipelineSummary,
  FeatureDriftScore,
  HeatmapData,
  SchemaData,
  IncidentSummary,
  DatasetSummary,
  DatasetUploadResponse,
} from '@/types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
})

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export const healthApi = {
  check: () => api.get<HealthResponse>('/health').then((r) => r.data),
}

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------
export const overviewApi = {
  get: () => api.get<OverviewResponse>('/overview').then((r) => r.data),
}

// ---------------------------------------------------------------------------
// Pipelines
// ---------------------------------------------------------------------------
export const pipelinesApi = {
  /** Fetch real pipelines from DB */
  list: () =>
    api
      .get<PipelineSummary[]>('/pipelines')
      .then((r) => r.data)
      .catch(() => [] as PipelineSummary[]),

  /** Alias for backward compatibility */
  listFromDB: () =>
    api
      .get<PipelineSummary[]>('/pipelines')
      .then((r) => r.data)
      .catch(() => [] as PipelineSummary[]),

  /** Create a new pipeline */
  create: (data: {
    name: string
    source_type: string
    destination_type?: string
    description?: string
    status?: string
  }) => api.post<PipelineSummary>('/pipelines', data).then((r) => r.data),

  get: (id: string) => api.get<PipelineSummary>(`/pipelines/${id}`).then((r) => r.data),

  update: (id: string, data: Partial<{ name: string; status: string; description: string }>) =>
    api.patch<PipelineSummary>(`/pipelines/${id}`, data).then((r) => r.data),
}

// ---------------------------------------------------------------------------
// Drift Detection & Incidents
// ---------------------------------------------------------------------------
export const driftApi = {
  featureScores: () =>
    api.get<{ features: FeatureDriftScore[] }>('/drift/feature-scores').then((r) => r.data.features),

  latest: () => api.get<any>('/drift/latest').then((r) => r.data),

  featureHistory: (featureName: string) =>
    api.get<any>(`/drift/feature/${encodeURIComponent(featureName)}/history`).then((r) => r.data),

  heatmap: () => api.get<HeatmapData>('/drift/heatmap').then((r) => r.data),

  incidents: (status?: string) =>
    api
      .get<{ items: IncidentSummary[] }>('/drift/incidents', {
        params: status && status !== 'all' ? { status } : undefined,
      })
      .then((r) => r.data.items ?? []),

  incidentById: (id: string) => api.get<IncidentSummary>(`/drift/incidents/${id}`).then((r) => r.data),

  createIncident: (data: {
    incident_id: string
    title: string
    summary?: string
    severity: string
    affected_features?: string[]
    triggering_metric?: string
    triggering_score?: number
  }) => api.post('/drift/incidents', data).then((r) => r.data),

  updateIncident: (id: string, data: { status?: string; severity?: string; resolution_notes?: string }) =>
    api.patch(`/drift/incidents/${id}`, data).then((r) => r.data),

  schema: () => api.get<any>('/drift/schema').then((r) => r.data),

  /** Run drift detection between two datasets and return full result */
  detect: (payload: {
    baseline_dataset_id: string
    current_dataset_id: string
    features?: string[]
    run_psi?: boolean
    run_kl?: boolean
    run_ks?: boolean
    run_schema?: boolean
    run_null_rate?: boolean
    thresholds?: Record<string, unknown>
  }) => api.post('/drift/detect', payload).then((r) => r.data),

  events: (params?: {
    dataset_id?: string
    pipeline_id?: string
    feature?: string
    severity?: string
    limit?: number
  }) => api.get('/drift/events', { params }).then((r) => r.data),
}

// ---------------------------------------------------------------------------
// Datasets
// ---------------------------------------------------------------------------
export const datasetsApi = {
  list: () => api.get<DatasetSummary[]>('/datasets').then((r) => r.data),

  upload: (file: File, options?: { name?: string; version?: string; is_baseline?: boolean }) => {
    const form = new FormData()
    form.append('file', file)
    if (options?.name) form.append('name', options.name)
    if (options?.version) form.append('version', options.version)
    if (options?.is_baseline !== undefined) form.append('is_baseline', String(options.is_baseline))
    return api
      .post<DatasetUploadResponse>('/datasets/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  remove: (id: string) => api.delete(`/datasets/${id}`),
}

// ---------------------------------------------------------------------------
// Experiments
// ---------------------------------------------------------------------------
export const experimentsApi = {
  list: () =>
    api
      .get<{ items: ExperimentRecord[]; available_drift_types: string[] }>('/experiments')
      .then((r) => r.data),

  create: (data: { name: string; experiment_type: string; config?: Record<string, unknown> }) =>
    api.post<ExperimentRecord>('/experiments', data).then((r) => r.data),

  run: (req: {
    drift_types?: string[]
    dataset_id?: string
    sample_sizes?: number[]
    magnitudes?: number[]
    random_seed?: number
  }) => api.post<ExperimentRunResult>('/experiments/run', req).then((r) => r.data),

  results: (experimentId?: string) =>
    api
      .get<{ items: ExperimentResultRecord[]; total: number }>('/experiments/results', {
        params: experimentId ? { experiment_id: experimentId } : undefined,
      })
      .then((r) => r.data),

  algorithmComparison: () =>
    api.get<AlgorithmComparisonData>('/experiments/algorithm-comparison').then((r) => r.data),
}

// ---------------------------------------------------------------------------
// AI Diagnosis
// ---------------------------------------------------------------------------
export const aiApi = {
  status: () => api.get('/ai/status').then((r) => r.data),

  diagnose: (payload: {
    feature?: string
    psi_score?: number
    kl_score?: number
    ks_statistic?: number
    ks_p_value?: number
    null_rate_change?: number
    baseline_null_rate?: number
    current_null_rate?: number
    schema_change_severity?: string
    schema_change_type?: string
    historical_incident_count?: number
    incident_id?: string
  }) => api.post<DiagnosisResult>('/ai/diagnose', payload).then((r) => r.data),

  listDiagnoses: () => api.get('/ai/diagnoses').then((r) => r.data),

  getDiagnosis: (id: string) => api.get(`/ai/diagnoses/${id}`).then((r) => r.data),
}

// ---------------------------------------------------------------------------
// Supporting TypeScript types for API responses
// ---------------------------------------------------------------------------

export interface ExperimentRecord {
  id: string
  name: string
  experiment_type: string
  status: string
  random_seed: number
  created_at: string
}

export interface ExperimentRunResult {
  experiment_id: string
  status: string
  total_runs: number
  drift_types_tested: string[]
  results_summary: ExperimentSingleResult[]
}

export interface ExperimentSingleResult {
  drift_type: string
  magnitude: number
  sample_size: number
  psi_score: number
  kl_score: number
  ks_statistic: number
  ks_p_value: number
  psi_detected: number
  kl_detected: number
  ks_detected: number
  overall_severity: string
  execution_time_ms: number
  error: string | null
}

export interface ExperimentResultRecord {
  id: string
  experiment_id: string
  drift_type: string
  drift_magnitude: number
  sample_size: number
  psi_score: number
  kl_score: number
  ks_statistic: number
  ks_p_value: number
  psi_detected: boolean
  kl_detected: boolean
  ks_detected: boolean
  execution_time_ms: number
  created_at: string
  metrics: Record<string, unknown>
}

export interface AlgorithmComparisonData {
  has_data: boolean
  total_experiments: number
  mag_data: { drift: string; PSI: number; KL: number; KS: number }[]
  latency_data: { name: string; PSI: number; KL: number; KS: number }[]
  error_data: { method: string; fp: number; fn: number }[]
  radar_data: { subject: string; PSI: number; KL: number; KS: number }[]
  agreement: {
    all_agree_pct: number
    psi_kl_pct: number
    psi_ks_pct: number
    disagree_pct: number
  }
  summary: {
    experiments_run: number
    avg_execution_ms: number
    total_samples: number
  }
}

export interface DiagnosisResult {
  provider: string
  model: string
  most_probable_cause: string
  confidence: number
  observed_evidence: { text: string; severity: string; metric: string }[]
  hypotheses: {
    rank: number
    title: string
    confidence: number
    severity: string
    reasoning: string
  }[]
  recommendations: { priority: string; title: string; body: string }[]
  evidence_summary: string
  db_id?: string
}
