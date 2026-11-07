export const RISK_TIERS = ["Low", "Elevated", "High", "Critical"] as const;
export type RiskTier = (typeof RISK_TIERS)[number];

export const FEATURE_COLUMNS = [
  "Time",
  ...Array.from({ length: 28 }, (_, index) => `V${index + 1}`),
  "Amount",
] as const;
export type FeatureName = (typeof FEATURE_COLUMNS)[number];
export type FeatureVector = Record<FeatureName, number>;

export interface ApiErrorPayload {
  error?: string;
  message?: string;
  request_id?: string;
  timestamp?: string;
  details?: Array<{ type?: string; location?: string }>;
}

export interface HealthResponse {
  status: string;
  service: string;
  api_version: string;
  components: Record<string, string>;
}

export interface ReadyResponse {
  status: string;
  model_version: string;
}

export interface AnomalyOutput {
  score?: number;
  percentile?: number;
  category?: string;
  score_direction?: string;
  score_is_probability?: false;
}

export interface Prediction {
  contract_version?: string;
  record_id: string;
  model_version: string;
  schema_version: string;
  transaction_id?: string | number | null;
  fraud_probability: number;
  risk_score: number;
  risk_tier: RiskTier;
  predicted_class: 0 | 1;
  decision_threshold: number;
  decision_status: string;
  probability_calibration_status: string;
  risk_policy_version: string;
  anomaly: AnomalyOutput | null;
  explanation?: Record<string, unknown> | null;
  narrative?: string[];
  timestamp?: string;
  created_at?: string;
  source?: string;
  analysis_id?: string | null;
  row_number?: number | null;
}

export interface PageResponse<T> {
  total?: number;
  count: number;
  limit: number;
  offset: number;
  results?: T[];
  analyses?: Analysis[];
  investigations?: Investigation[];
}

export interface PredictionResponse {
  count: number;
  results: Prediction[];
}

export interface AnalysisSummary {
  rows?: number;
  flagged_for_review?: number;
  flagged_percentage?: number;
  mean_fraud_probability?: number;
  minimum_fraud_probability?: number;
  maximum_fraud_probability?: number;
  risk_tier_counts?: Record<string, number>;
  anomaly_category_counts?: Record<string, number>;
  created_at?: string;
  model_version?: string;
  labels_present?: boolean;
  precision_recall_computed?: boolean;
}

export interface Analysis {
  analysis_id: string;
  upload_id: string;
  status: "pending" | "running" | "completed" | "failed";
  requested_rows: number;
  processed_rows: number;
  model_version: string | null;
  failure_code: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  summary: AnalysisSummary | null;
}

export interface UploadResponse {
  upload_id: string;
  sha256: string;
  size_bytes: number;
  row_count: number;
  schema_version: string;
}

export interface AnalysisResultsResponse {
  analysis_id: string;
  count: number;
  limit: number;
  offset: number;
  results: Prediction[];
}

export interface InvestigationNote {
  note_id: string;
  body: string;
  created_at: string;
}

export interface InvestigationEvent {
  event_id: string;
  event_type: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export type InvestigationStatus = "Open" | "In Review" | "Escalated" | "Closed";
export type InvestigationOutcome = "Unconfirmed" | "Legitimate" | "Confirmed Fraud" | "Inconclusive";

export interface Investigation {
  investigation_id: string;
  prediction_id: string | null;
  title: string;
  reason: string;
  status: InvestigationStatus;
  outcome: InvestigationOutcome | null;
  outcome_is_analyst_recorded: boolean;
  outcome_is_ground_truth: false;
  created_at: string;
  updated_at: string;
  notes?: InvestigationNote[];
  events?: InvestigationEvent[];
}

export interface LocalExplanation {
  method?: string;
  output_space?: string;
  raw_decision_score?: number;
  fraud_probability?: number;
  decision_threshold?: number;
  risk_score?: number;
  explanation?: {
    method?: string;
    output_space?: string;
    base_value?: number;
    baseline_semantics?: string;
    feature_contributions?: Array<Record<string, unknown>>;
    all_contributions_returned?: boolean;
    reconstruction_error?: number;
    [key: string]: unknown;
  };
  contributions?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}
