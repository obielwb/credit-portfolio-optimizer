









import type {
  Algorithm,
  ComparisonRunsDataSchema,
  ExecutionDetailSchema,
  ExecutionHistorySchema,
  IngestionUploadResponse,
  LimitsBucketSchema,
  ParametersSchema,
  ParametersUpdateRequest,
  ReturnByCohortSchema,
  RunComparisonSnapshotSchema,
  RunResultSchema,
  RunStatusSchema,
  StatisticsPortfolioResponseSchema,
  StatisticsDashboardSchema,
  StatisticsClientResultsSchema,
  StatisticsRunSchema,
} from "./types";
import { ApiResponseError } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Helpers ───────────────────────────────────────────────────────────────────

function extractError(body: Record<string, unknown>, status: number): ApiResponseError {
  // Support { status:'error', code, message, details } and the FastAPI format { detail: { code, message } }
  const detail = body?.detail as Record<string, unknown> | undefined;
  const code = (body?.code ?? detail?.code ?? "UNKNOWN_ERROR") as string;
  const message = (body?.message ?? detail?.message ?? `HTTP ${status}`) as string;
  const details = (body?.details ?? detail?.details ?? {}) as Record<string, unknown>;
  return new ApiResponseError(code, message, details, status);
}


async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (init.headers) {
    Object.assign(headers, init.headers);
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  const body = (await res.json()) as Record<string, unknown>;

  if (!res.ok || body?.status === "error") {
    throw extractError(body, res.status);
  }


  if (body?.status === "ok" && "data" in body) {
    return body.data as T;
  }


  return body as unknown as T;
}


async function requestBlob(path: string): Promise<{ blob: Blob; disposition: string }> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    throw extractError(body, res.status);
  }
  return {
    blob: await res.blob(),
    disposition: res.headers.get("Content-Disposition") ?? "",
  };
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}



export async function uploadFile(
  file: File,
  algorithm: Algorithm = "simplex",
): Promise<IngestionUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("algorithm", algorithm);


  const res = await fetch(`${BASE_URL}/ingestion/upload`, { method: "POST", body: form });
  const body = (await res.json()) as Record<string, unknown>;

  if (!res.ok || body?.status === "error") {
    throw extractError(body, res.status);
  }

  return ((body?.status === "ok" ? body.data : body) as IngestionUploadResponse);
}




export async function getRunStatus(runId: number): Promise<RunStatusSchema> {
  const res = await fetch(`${BASE_URL}/optimization/runs/${runId}`);
  const body = (await res.json()) as Record<string, unknown>;
  if (!res.ok) throw extractError(body, res.status);
  return body as unknown as RunStatusSchema;
}


export async function getRunResult(runId: number): Promise<RunResultSchema> {
  const res = await fetch(`${BASE_URL}/optimization/runs/${runId}/result`);
  const body = (await res.json()) as Record<string, unknown>;
  if (!res.ok) throw extractError(body, res.status);
  return body as unknown as RunResultSchema;
}



export function getActiveParameters(): Promise<ParametersSchema> {
  return request<ParametersSchema>("/parameters/active");
}

export function updateParameters(params: ParametersUpdateRequest): Promise<ParametersSchema> {
  return request<ParametersSchema>("/parameters/active", {
    method: "PUT",
    body: JSON.stringify(params),
  });
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardParams {
  run_id?: number;
  csv_file_id?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export function getDashboard(params: DashboardParams = {}): Promise<StatisticsDashboardSchema> {
  const qs = new URLSearchParams();
  if (params.run_id != null) qs.set("run_id", String(params.run_id));
  if (params.csv_file_id != null) qs.set("csv_file_id", String(params.csv_file_id));
  if (params.page != null) qs.set("page", String(params.page));
  if (params.page_size != null) qs.set("page_size", String(params.page_size));
  if (params.sort_by) qs.set("sort_by", params.sort_by);
  if (params.sort_order) qs.set("sort_order", params.sort_order);
  return request<StatisticsDashboardSchema>(`/results/dashboard?${qs}`);
}



export function getRunsSummary(): Promise<StatisticsRunSchema> {
  return request<StatisticsRunSchema>("/results/runs");
}

export function getPortfolio(csv_file_id?: number): Promise<StatisticsPortfolioResponseSchema> {
  const qs = csv_file_id != null ? `?csv_file_id=${csv_file_id}` : "";
  return request<StatisticsPortfolioResponseSchema>(`/results/portfolio${qs}`);
}

export interface ClientResultParams {
  run_id?: number;
  csv_file_id?: number;
  token?: string;
}

export function getClientResult(
  params: ClientResultParams,
): Promise<StatisticsClientResultsSchema> {
  const qs = new URLSearchParams();
  if (params.run_id != null) qs.set("run_id", String(params.run_id));
  if (params.csv_file_id != null) qs.set("csv_file_id", String(params.csv_file_id));
  if (params.token) qs.set("token", params.token);
  return request<StatisticsClientResultsSchema>(`/results/client?${qs}`);
}

export function getLimitBuckets(csv_file_id?: number): Promise<LimitsBucketSchema[]> {
  const qs = csv_file_id != null ? `?csv_file_id=${csv_file_id}` : "";
  return request<{ items: LimitsBucketSchema[] }>(
    `/results/portfolio/limits-buckets${qs}`,
  ).then((data) => data.items);
}

export interface CohortReturnParams {
  csv_file_id?: number;
  run_id?: number;
}

export function getReturnByCohort(
  params: CohortReturnParams = {},
): Promise<ReturnByCohortSchema[]> {
  const qs = new URLSearchParams();
  if (params.csv_file_id != null) qs.set("csv_file_id", String(params.csv_file_id));
  if (params.run_id != null) qs.set("run_id", String(params.run_id));
  const suffix = qs.toString() ? `?${qs}` : "";
  return request<{ items: ReturnByCohortSchema[] }>(
    `/results/portfolio/return-cohort${suffix}`,
  ).then((data) => data.items);
}



export interface HistoryParams {
  page?: number;
  page_size?: number;
  status?: string;
}

export function getExecutionHistory(params: HistoryParams = {}): Promise<ExecutionHistorySchema> {
  const qs = new URLSearchParams();
  if (params.page != null) qs.set("page", String(params.page));
  if (params.page_size != null) qs.set("page_size", String(params.page_size));
  if (params.status) qs.set("status", params.status);
  return request<ExecutionHistorySchema>(`/results/executions/history?${qs}`);
}

export function getExecutionDetail(runId: number): Promise<ExecutionDetailSchema> {
  return request<ExecutionDetailSchema>(`/results/executions/${runId}`);
}

export function deleteExecution(runId: number): Promise<{ run_id: number }> {
  return request<{ run_id: number }>(`/results/executions/${runId}`, {
    method: "DELETE",
  });
}

export async function downloadExecutionCsv(runId: number): Promise<void> {
  const { blob, disposition } = await requestBlob(`/results/executions/${runId}/download`);
  const match = disposition.match(/filename="?([^"]+)"?/);
  triggerDownload(blob, match?.[1] ?? `result_run_${runId}.csv`);
}

export async function downloadReportPdf(params: {
  run_id?: number;
  csv_file_id?: number;
}): Promise<void> {
  const qs = new URLSearchParams();
  if (params.run_id != null) qs.set("run_id", String(params.run_id));
  if (params.csv_file_id != null) qs.set("csv_file_id", String(params.csv_file_id));
  const { blob } = await requestBlob(`/results/report/pdf?${qs}`);
  triggerDownload(blob, `run_report_${params.run_id ?? "portfolio"}.pdf`);
}



export function compareRuns(
  referenciaRunId: number,
  comparedRunId: number,
): Promise<ComparisonRunsDataSchema> {
  return request<ComparisonRunsDataSchema>(
    `/comparison/runs?reference_run_id=${referenciaRunId}&compared_run_id=${comparedRunId}`,
  );
}

export async function downloadComparisonPdf(
  referenciaRunId: number,
  comparedRunId: number,
): Promise<void> {
  const qs = new URLSearchParams({
    reference_run_id: String(referenciaRunId),
    compared_run_id: String(comparedRunId),
  });
  const { blob, disposition } = await requestBlob(`/comparison/runs/pdf?${qs}`);
  const match = disposition.match(/filename="?([^"]+)"?/);
  triggerDownload(blob, match?.[1] ?? `comparison_runs_${referenciaRunId}_${comparedRunId}.pdf`);
}

export function getRunSnapshot(runId: number): Promise<RunComparisonSnapshotSchema> {
  return request<RunComparisonSnapshotSchema>(`/comparison/runs/${runId}`);
}
