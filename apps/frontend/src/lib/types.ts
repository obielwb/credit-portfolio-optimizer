

export type Algorithm = "simplex" | "simplex_ortools" | "branch_bound";

export type RunStatusFinal = "success" | "error" | "timeout" | "pending";

export type RunState =
  | "waiting_for_processing"
  | "ingestion"
  | "calculating_constraints"
  | "tableau_calculation"
  | "generating_recommendations"
  | "validating_constraints"
  | "completed"
  | "failed";

// ── Erro tipado ───────────────────────────────────────────────────────────────

export class ApiResponseError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
    public readonly httpStatus?: number,
  ) {
    super(message);
    this.name = "ApiResponseError";
  }
}



export interface IngestionUploadResponse {
  run_id: number;
  filename: string;
  algorithm: Algorithm;
  state: "queued" | "csv_ingestion" | "completed" | "failed";
}




export interface RunStatusSchema {
  run_id: number;
  state: RunState;
  current_stage: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}


export interface RunResultSchema {
  run_id: number;
  final_status: "success" | "error" | "timeout";
  algorithm: Algorithm;
  result_id: number | null;
  error: string | null;
  released_at: string | null;
}



export type Multiplier = Record<string, string | number>;

export interface ParametersSchema {
  id: number;
  utilization_rate: number;
  lgd: number;
  min_pd: number;
  max_pd: number;
  filter: boolean;
  max_limit: number;
  baseline_default_rate: number;
  min_limit: number;
  discretize: boolean;
  interchange: number;
  max_rejected_limit: number;
  enabled: boolean;
  n_clusters: number | null;
  max_clients_per_cluster: number;
  min_clusters: number;
  multipliers: Multiplier[];
  created_at: string;
}

export interface ParametersUpdateRequest {
  utilization_rate?: number;
  lgd?: number;
  min_pd?: number;
  max_pd?: number;
  filter?: boolean;
  max_limit?: number;
  baseline_default_rate?: number;
  min_limit?: number;
  discretize?: boolean;
  interchange?: number;
  max_rejected_limit?: number;
  enabled?: boolean;
  n_clusters?: number | null;
  max_clients_per_cluster?: number;
  min_clusters?: number;
  multipliers?: Multiplier[];
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface FileSchema {
  csv_file_id: number;
  file_name: string;
  created_at: string | null;
  run_id: number | null;
}

export interface DashboardClientSchema {
  token: string;
  payment_capacity: number;
  score: number;
  suggested_limit: number | null;
  pd: number;
}

export interface DashboardTotalsSchema {
  total_clients: number;
  total_suggested_limit: number;
  approval_rate: number;
  expected_return: number;
}

export interface StatisticsDashboardSchema {
  file: FileSchema;
  clients: DashboardClientSchema[];
  totais: DashboardTotalsSchema;
  pagina: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  sort_by: string | null;
  sort_order: "asc" | "desc" | null;
}



export interface StatisticsRunSchema {
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  avg_duration_ms: number;
}

export interface StatisticsPortfolioSchema {
  total_limit: number;
  total_income: number;
  total_loss: number;
  total_return: number;
  financial_default_rate: number;
  baseline_default_rate: number;
  total_clients: number;
  approval_rate: number;
}

export interface LimitsBucketSchema {
  range: string;
  count: number;
  percentage: number;
}

export interface ReturnByCohortSchema {
  cohort_reference: string;
  total_clients: number;
  total_return: number;
}

export interface StatisticsPortfolioResponseSchema {
  portfolio: StatisticsPortfolioSchema;
  limit_ranges: LimitsBucketSchema[];
  return_by_cohort: ReturnByCohortSchema[];
}

export interface ClientResultSchema {
  token: string;
  payment_capacity: number;
  propensity_score: number;
  pd: number;
  suggested_limit: number;
  expected_income: number;
  expected_loss: number;
  expected_return: number;
}

export interface StatisticsClientResultsSchema {
  file: FileSchema;
  items: ClientResultSchema[];
  total_items: number;
}



export interface ExecutionHistoryItemSchema {
  run_id: number;
  algorithm: string;
  status: RunStatusFinal;
  csv_file_id: number;
  file_name: string;
  total_clients: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  execution_time_ms: number | null;
  approved: number | null;
  error_reason: string | null;
  total_limit: number | null;
  approval_rate: number | null;
  total_return: number | null;
}

export interface ExecutionHistorySchema {
  items: ExecutionHistoryItemSchema[];
  total_items: number;
}

export interface ExecutionLogEntrySchema {
  t: string;
  tipo: "info" | "ok" | "warn" | "error";
  msg: string;
}

export interface LimitDistributionSchema {
  above: number;
  full: number;
  denied: number;
}

export interface ExecutionDetailSchema {
  run_id: number;
  algorithm: string;
  status: RunStatusFinal;
  csv_file_id: number;
  file_name: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  execution_time_ms: number | null;
  total_clients: number;
  approved: number;
  approval_rate: number | null;
  average_approved_score: number | null;
  total_limit: number | null;
  total_return: number | null;
  error_reason: string | null;
  parameters: ParametersSchema | null;
  distribution: LimitDistributionSchema | null;
  limit_ranges: LimitsBucketSchema[];
  operational_log: ExecutionLogEntrySchema[];
  download_csv_url: string | null;
}



export interface RunComparisonMetricsSchema {
  total_clients: number;
  total_limit: number;
  total_income: number;
  total_loss: number;
  total_return: number;
  financial_default_rate: number;
  approval_rate: number;
}

export interface ComparisonReturnByCohortSchema {
  cohort_reference: string;
  total_return: number;
  percentage: number;
  total_clients: number | null;
}

export interface CohortAnalysisSchema {
  cohort: string;
  client_count: number;
  average_capacity: number;
  average_limit: number;
  approval_rate: number;
}

export type ReturnGrouping = "cohort" | "cluster";

export interface RunComparisonSnapshotSchema {
  run_id: number;
  algorithm: string;
  status: RunStatusFinal;
  created_at: string;
  execution_time_ms: number | null;
  csv_file_id: number;
  file_name: string;
  parameters: ParametersSchema;
  metrics: RunComparisonMetricsSchema;
  limit_ranges: LimitsBucketSchema[];
  return_by_cohort: ComparisonReturnByCohortSchema[];
  cohort_analysis: CohortAnalysisSchema[];
  return_grouping?: ReturnGrouping;
}

export interface ComparisonDeltaItemSchema {
  absoluto: number;
  percentage: number | null;
}

export interface ComparisonDeltaSchema {
  total_limit: ComparisonDeltaItemSchema;
  approval_rate: ComparisonDeltaItemSchema;
  total_return: ComparisonDeltaItemSchema;
  financial_default_rate: ComparisonDeltaItemSchema;
  total_clients: ComparisonDeltaItemSchema;
  total_income: ComparisonDeltaItemSchema | null;
  total_loss: ComparisonDeltaItemSchema | null;
}

export interface ComparisonRunsDataSchema {
  reference: RunComparisonSnapshotSchema;
  compared: RunComparisonSnapshotSchema;
  deltas: ComparisonDeltaSchema;
}
