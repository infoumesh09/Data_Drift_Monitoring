export type Severity = 'HEALTHY' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type DriftType =
  | 'distribution'
  | 'schema'
  | 'null_rate'
  | 'cardinality'
  | 'correlation'
  | 'seasonal'

export interface HealthResponse {
  status: string
  app_name: string
  version: string
  environment: string
  timestamp: string
  database?: { status: string; reachable?: boolean; error?: string }
}

export interface OverviewStats {
  data_health_score: number
  active_pipelines: number
  healthy_pipelines: number
  active_incidents: number
  critical_incidents: number
  monitored_features: number
  drift_events_today: number
}

export interface PipelineSummary {
  id: string
  name: string
  source: string
  destination: string
  last_successful_run: string
  status: 'Healthy' | 'Warning' | 'Critical'
  mcfe_count: number
  project: string
}

export interface HeatmapData {
  time_windows: string[]
  rows: { feature: string; cells: Severity[] }[]
}

export interface IncidentSummary {
  id: string
  summary: string
  severity: Severity
  feature: string
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED'
  metric: string
  score: number
  timestamp: string
  drift_type: string
}

export interface FeatureDriftScore {
  feature: string
  type: 'numeric' | 'categorical'
  psi: number
  kl: number
  ks_stat: number
  ks_p: number
  null_rate: number
  cardinality: number
  drift_type: string
}

export interface SchemaData {
  added_columns: number
  removed_columns: number
  type_changes: number
  null_rate_changes: number
  cardinality_changes: number
  before_after: SchemaRow[]
  change_log: SchemaChange[]
}

export interface SchemaRow {
  column: string
  status: string
  before: string
  after: string
  null_rate: number
  cardinality: number
}

export interface SchemaChange {
  change_type: string
  column: string
  before: string
  after: string
  severity: string
  detected_by: string
  detected_at: string
}

export interface DatasetColumnProfile {
  name: string
  dtype: string
  feature_class: string
  null_count: number
  null_rate: number
  cardinality?: number
}

export interface DatasetProfile {
  row_count: number
  column_count: number
  overall_null_rate: number
  columns: DatasetColumnProfile[]
  classification?: Record<string, string>
}

export interface DatasetSummary {
  id: string
  name: string
  description?: string | null
  version: string
  pipeline_id?: string | null
  row_count: number
  column_count: number
  size_bytes: number
  is_baseline: boolean
  profile: DatasetProfile
  created_at: string
  updated_at: string
}

export interface DatasetUploadResponse {
  id: string
  name: string
  row_count: number
  column_count: number
  columns: DatasetColumnProfile[]
  profile: DatasetProfile
}

export interface OverviewResponse {
  stats: OverviewStats
  pipelines: PipelineSummary[]
  drift_heatmap: HeatmapData
  incidents: IncidentSummary[]
  drift_scores: FeatureDriftScore[]
}
