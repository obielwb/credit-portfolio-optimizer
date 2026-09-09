"use client";

import {
  type ChangeEvent,
  type DragEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useRunPolling } from "@/hooks/use-run-polling";
import {
  getClientResult,
  getDashboard,
  uploadFile,
} from "@/lib/api";
import {
  ETAPAS_FLUXO,
  ETAPA_LABEL,
  LIMIT_BADGE_CLASS,
  LIMIT_BADGE_LABEL,
  type LimitCategory,
  avatarColorFor,
  classifyLimit,
  classifyScore,
  etapaProgress,
  formatBRL,
  formatBRLFull,
  formatPct,
  tokenInitials,
} from "@/lib/format";
import {
  ApiResponseError,
  type Algorithm,
  type DashboardClientSchema,
  type ClientResultSchema,
  type StatisticsDashboardSchema,
} from "@/lib/types";

type Phase = "idle" | "uploading" | "processing" | "done" | "error";
type ScoreFilter = "all" | "muito-baixo" | "baixo" | "medio" | "bom" | "excelente";
type ValueFilter = "all" | "ate5k" | "5k10k" | "10k20k" | "above20k";


const REQUIRED_COL_GROUPS: Array<{ label: string; aliases: string[] }> = [
  { label: "token", aliases: ["token"] },
  { label: "payment_capacity", aliases: ["payment_capacity"] },
  { label: "product_pd", aliases: ["default_probability", "product_pd"] },
  {
    label: "contract_propensity_score",
    aliases: ["contract_propensity", "contract_propensity_score"],
  },
  { label: "filter_flag", aliases: ["filter_flag"] },
];
const PAGE_SIZE = 10;
const ACCEPTED_EXTS = ["csv", "parquet", "pq"];

const ALGORITHM_LABELS: Record<Algorithm, string> = {
  branch_bound: "Branch and Bound",
  simplex: "Simplex",
  simplex_ortools: "Simplex OR-Tools",
};

const SCORE_OPTIONS: Array<{ value: ScoreFilter; label: string; sub?: string; color?: string }> = [
  { value: "all", label: "All" },
  { value: "muito-baixo", label: "Very low score", sub: "Below 300", color: "#ef4444" },
  { value: "baixo", label: "Score baixo", sub: "300 – 499", color: "#f97316" },
  { value: "medio", label: "Average score", sub: "500 – 699", color: "#eab308" },
  { value: "bom", label: "Score bom", sub: "700 – 849", color: "#22c55e" },
  { value: "excelente", label: "Score excelente", sub: "850 or mais", color: "#16a34a" },
];

const VALUE_OPTIONS: Array<{ value: ValueFilter; label: string }> = [
  { value: "all", label: "Qualquer value" },
  { value: "ate5k", label: "Up to R$ 5,000" },
  { value: "5k10k", label: "R$ 5.001 – R$ 10.000" },
  { value: "10k20k", label: "R$ 10.001 – R$ 20.000" },
  { value: "above20k", label: "Above R$ 20,000" },
];

const SCORE_RANGES: Record<Exclude<ScoreFilter, "all">, [number, number]> = {
  "muito-baixo": [0, 299],
  baixo: [300, 499],
  medio: [500, 699],
  bom: [700, 849],
  excelente: [850, 9999],
};

const VALUE_RANGES: Record<Exclude<ValueFilter, "all">, [number, number]> = {
  ate5k: [0, 5000],
  "5k10k": [5001, 10000],
  "10k20k": [10001, 20000],
  above20k: [20001, Number.POSITIVE_INFINITY],
};

interface UploadInfo {
  file: File;
  cols: string[];
  missing: string[];
  sizeMB: string;
  ext: string;
  rowCount: number | null;
  canPreviewColumns: boolean;
}

interface PersistedApplicationsState {
  phase: Phase;
  error: string | null;
  algorithm: Algorithm;
  runId: number | null;
  dashboard: StatisticsDashboardSchema | null;
  searchDraft: string;
  search: string;
  scoreFilter: ScoreFilter;
  valueFilter: ValueFilter;
  sortDesc: boolean;
  page: number;
}

const APPLICATIONS_STORAGE_KEY = "credit-portfolio-optimizer.applications.state";

function loadPersistedApplications(): PersistedApplicationsState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(APPLICATIONS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PersistedApplicationsState) : null;
  } catch {
    return null;
  }
}

function persistApplications(state: PersistedApplicationsState): void {
  try {
    window.sessionStorage.setItem(APPLICATIONS_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignora failures de quota/permissao; a navegacao continua funcionando.
  }
}

export default function HomePage() {
  const persisted = useMemo(loadPersistedApplications, []);

  // ── Estado principal ──
  const [phase, setPhase] = useState<Phase>(persisted?.phase ?? "idle");
  const [error, setError] = useState<string | null>(persisted?.error ?? null);
  const [pickedFile, setPickedFile] = useState<File | null>(null);
  const [algorithm, setAlgorithm] = useState<Algorithm>(
    persisted?.algorithm ?? "branch_bound",
  );
  const [runId, setRunId] = useState<number | null>(persisted?.runId ?? null);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);
  const [dashboard, setDashboard] = useState<StatisticsDashboardSchema | null>(
    persisted?.dashboard ?? null,
  );

  // Polling
  const { status: runStatus, error: pollError } = useRunPolling(runId);

  // Modais
  const [showUpload, setShowUpload] = useState(false);
  const [showAlgo, setShowAlgo] = useState(false);
  const [detailToken, setDetailToken] = useState<string | null>(null);
  const [detailResult, setDetailResult] = useState<ClientResultSchema | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Filtros / busca / sort
  const [searchDraft, setSearchDraft] = useState(persisted?.searchDraft ?? "");
  const [search, setSearch] = useState(persisted?.search ?? "");
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>(
    persisted?.scoreFilter ?? "all",
  );
  const [valueFilter, setValueFilter] = useState<ValueFilter>(
    persisted?.valueFilter ?? "all",
  );
  const [openDropdown, setOpenDropdown] = useState<"score" | "value" | null>(null);
  const [sortDesc, setSortDesc] = useState(persisted?.sortDesc ?? true);


  const [page, setPage] = useState(persisted?.page ?? 1);

  useEffect(() => {
    persistApplications({
      phase,
      error,
      algorithm,
      runId,
      dashboard,
      searchDraft,
      search,
      scoreFilter,
      valueFilter,
      sortDesc,
      page,
    });
  }, [
    phase,
    error,
    algorithm,
    runId,
    dashboard,
    searchDraft,
    search,
    scoreFilter,
    valueFilter,
    sortDesc,
    page,
  ]);


  useEffect(() => {
    if (!runStatus) return;
    if (runStatus.state === "completed" && runId !== null) {
      let cancelled = false;
      getDashboard({ run_id: runId, page, page_size: PAGE_SIZE })
        .then((data) => {
          if (cancelled) return;
          setDashboard(data);
          setPhase("done");
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setError(
            err instanceof ApiResponseError
              ? err.message
              : "Failed to load the results dashboard.",
          );
          setPhase("error");
        });
      return () => {
        cancelled = true;
      };
    }
    if (runStatus.state === "failed") {
      setError(runStatus.error ?? "The algorithm run failed.");
      setPhase("error");
    }
  }, [runStatus, runId, page]);

  useEffect(() => {
    if (pollError) {
      setError(pollError);
      setPhase("error");
    }
  }, [pollError]);

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    function onClick(event: MouseEvent) {
      const target = event.target as HTMLElement | null;
      if (!target?.closest(".dropdown-wrap")) setOpenDropdown(null);
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  // Esc fecha modais
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (detailToken) setDetailToken(null);
      else if (showAlgo) setShowAlgo(false);
      else if (showUpload && phase !== "uploading") setShowUpload(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [detailToken, showAlgo, showUpload, phase]);

  // ── Handlers ──
  const handleConfirmUpload = useCallback((file: File) => {
    setPickedFile(file);
    setShowUpload(false);
  }, []);

  const startAlgorithm = useCallback(() => {
    if (!pickedFile) {
      setShowUpload(true);
      return;
    }
    setShowAlgo(true);
  }, [pickedFile]);

  const confirmAlgorithm = useCallback(async () => {
    if (!pickedFile) return;
    setShowAlgo(false);
    setError(null);
    setPhase("uploading");
    setRunStartedAt(Date.now());
    try {
      const response = await uploadFile(pickedFile, algorithm);
      setRunId(response.run_id);
      setPhase("processing");
    } catch (err) {
      setError(
        err instanceof ApiResponseError ? err.message : "Failed to upload the file.",
      );
      setPhase("error");
      setRunStartedAt(null);
    }
  }, [pickedFile, algorithm]);

  const cancelRunning = useCallback(() => {
    setRunId(null);
    setRunStartedAt(null);
    setPhase(pickedFile ? "idle" : "idle");
  }, [pickedFile]);

  const openDetalhes = useCallback(
    async (token: string) => {
      if (runId === null) return;
      setDetailToken(token);
      setDetailResult(null);
      setDetailError(null);
      setDetailLoading(true);
      try {
        const data = await getClientResult({ run_id: runId, token });
        const match = data.items.find((i) => i.token === token) ?? data.items[0] ?? null;
        setDetailResult(match);
      } catch (err) {
        setDetailError(
          err instanceof ApiResponseError
            ? err.message
            : "Failed to load client details.",
        );
      } finally {
        setDetailLoading(false);
      }
    },
    [runId],
  );


  useEffect(() => {
    if (phase !== "done" || runId === null) return;
    let cancelled = false;
    getDashboard({ run_id: runId, page, page_size: PAGE_SIZE })
      .then((data) => {
        if (!cancelled) setDashboard(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // phase intentionally excluded — refetch only on page changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, runId]);

  // ── Filtros client-side sobre clients retornados ──
  const visibleClients = useMemo(() => {
    if (!dashboard) return [];
    let data = [...dashboard.clients];
    if (search) {
      const q = search.toLowerCase();
      data = data.filter((c) => c.token.toLowerCase().includes(q));
    }
    if (scoreFilter !== "all") {
      const [min, max] = SCORE_RANGES[scoreFilter];
      data = data.filter((c) => c.score >= min && c.score <= max);
    }
    if (valueFilter !== "all") {
      const [min, max] = VALUE_RANGES[valueFilter];
      data = data.filter((c) => c.payment_capacity >= min && c.payment_capacity <= max);
    }
    data.sort((a, b) => {
      const av = a.suggested_limit ?? -1;
      const bv = b.suggested_limit ?? -1;
      if (av === bv) return sortDesc ? b.score - a.score : a.score - b.score;
      return sortDesc ? bv - av : av - bv;
    });
    return data;
  }, [dashboard, search, scoreFilter, valueFilter, sortDesc]);

  const showResults = phase === "done" && dashboard !== null;
  const hasFile = pickedFile !== null;
  const totalPages = dashboard ? Math.max(1, dashboard.total_pages) : 1;
  const isRunning = phase === "uploading" || phase === "processing";

  const detailClientRow: DashboardClientSchema | null =
    detailToken && dashboard
      ? dashboard.clients.find((c) => c.token === detailToken) ?? null
      : null;

  return (
    <div className="screen active" style={{ position: "relative" }}>
      {showResults && (
        <div className="state-badge">
          <span className="dot"></span> AFTER ALGORITHM
        </div>
      )}

      <div className="breadcrumb">
        Applicants › <span>Credit applications</span>
      </div>

      <div className="top-bar">
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          Credit Applications
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            className={`btn-update${hasFile ? " has-file" : ""}`}
            onClick={() => setShowUpload(true)}
            disabled={isRunning}
            title={hasFile ? pickedFile?.name : "Importar file CSV or Parquet"}
          >
            <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              {hasFile ? (
                <>
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </>
              ) : (
                <>
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </>
              )}
            </svg>
            {hasFile ? pickedFile!.name : "Update data"}
          </button>
          <button
            className={showResults ? "btn-reanalisar" : "btn-rodar"}
            onClick={startAlgorithm}
            disabled={!hasFile || isRunning}
          >
            <svg width="13" height="13" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
            {showResults ? "Reanalisar" : "Rodar Algorithm"}
          </button>
        </div>
      </div>

      {phase === "error" && error && <div className="inline-error">{error}</div>}

      {showResults && dashboard && (
        <KpiStrip
          totalClients={dashboard.totais.total_clients}
          totalLimit={dashboard.totais.total_suggested_limit}
          approvalRate={dashboard.totais.approval_rate}
          expectedReturn={dashboard.totais.expected_return}
        />
      )}

      {showResults && (
        <>
          <FilterBar
            searchDraft={searchDraft}
            onSearchChange={setSearchDraft}
            onApply={() => setSearch(searchDraft)}
            scoreFilter={scoreFilter}
            valueFilter={valueFilter}
            openDropdown={openDropdown}
            onToggleDropdown={(d) => setOpenDropdown(openDropdown === d ? null : d)}
            onSelectScore={(v) => {
              setScoreFilter(v);
              setOpenDropdown(null);
            }}
            onSelectValue={(v) => {
              setValueFilter(v);
              setOpenDropdown(null);
            }}
          />
          <div className="list-controls">
            <span className="list-count">
              {dashboard.total_items === 0
                ? "No application"
                : `${visibleClients.length} de ${dashboard.total_items} ${
                    dashboard.total_items === 1
                      ? "application found"
                      : "applications found"
                  }`}
            </span>
            <span className="sort-control">
              Ordenar por:{" "}
              <strong onClick={() => setSortDesc((v) => !v)}>
                {sortDesc ? "Limit sugerido (greater) ↓" : "Limit sugerido (lower) ↑"}
              </strong>
            </span>
          </div>
        </>
      )}

      {!showResults && !isRunning && (
        <div className="home-empty-state">
          <div className="home-empty-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div className="home-empty-title">
            {hasFile ? "File ready for analysis" : "No file imported"}
          </div>
          <div className="home-empty-sub">
            {hasFile
              ? "Click \"Run algorithm\" to send the file to the backend and generate recommendations."
              : "Import a CSV or Parquet file with the required columns to view applications."}
          </div>
          {!hasFile && (
            <button className="btn-update" onClick={() => setShowUpload(true)}>
              Importar file
            </button>
          )}
        </div>
      )}

      {showResults && (
        <div className="requests-list">
          {visibleClients.length === 0 ? (
            <div className="home-empty-state" style={{ minHeight: 200 }}>
              <div className="empty-title">No client matches the filters</div>
              <div className="empty-sub">Ajuste a busca or os filters e tente newmente.</div>
            </div>
          ) : (
            visibleClients.map((c) => (
              <RequestCard key={c.token} client={c} onDetails={() => openDetalhes(c.token)} />
            ))
          )}
        </div>
      )}

      {showResults && totalPages > 1 && (
        <div className="home-pagination">
          <button
            className="page-btn"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            ← Anterior
          </button>
          <span className="page-info">
            Page {page} de {totalPages}
          </span>
          <button
            className="page-btn"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next →
          </button>
        </div>
      )}

      {/* Modais */}
      {showUpload && (
        <UploadModal
          existing={pickedFile}
          onClose={() => setShowUpload(false)}
          onConfirm={handleConfirmUpload}
        />
      )}
      {showAlgo && (
        <AlgorithmModal
          algorithm={algorithm}
          onSelect={setAlgorithm}
          onClose={() => setShowAlgo(false)}
          onConfirm={confirmAlgorithm}
        />
      )}
      {isRunning && (
        <LoadingModal
          algorithmLabel={ALGORITHM_LABELS[algorithm]}
          uploading={phase === "uploading"}
          state={runStatus?.state ?? null}
          currentStage={runStatus?.current_stage ?? null}
          startedAt={runStartedAt}
          onCancel={cancelRunning}
        />
      )}
      {detailToken && (
        <DetalhesModal
          token={detailToken}
          clientRow={detailClientRow}
          detail={detailResult}
          loading={detailLoading}
          error={detailError}
          onClose={() => setDetailToken(null)}
        />
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Sub-components

function KpiStrip({
  totalClients,
  totalLimit,
  approvalRate,
  expectedReturn,
}: {
  totalClients: number;
  totalLimit: number;
  approvalRate: number;
  expectedReturn: number;
}) {
  return (
    <div className="kpi-strip">
      <div className="kpi-card">
        <div className="kpi-icon">
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 00-3-3.87" />
            <path d="M16 3.13a4 4 0 010 7.75" />
          </svg>
        </div>
        <div>
          <div className="kpi-label">Clients analisados</div>
          <div className="kpi-val">{totalClients.toLocaleString("en-US")}</div>
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-icon">
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
            <line x1="12" y1="1" x2="12" y2="23" />
            <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
          </svg>
        </div>
        <div>
          <div className="kpi-label">Limit total sugerido</div>
          <div className="kpi-val">{formatBRL(totalLimit)}</div>
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-icon">
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <div>
          <div className="kpi-label">Approval rate</div>
          <div className="kpi-val">{formatPct(approvalRate, 0)}</div>
        </div>
      </div>
      <div className="kpi-card">
        <div className="kpi-icon">
          <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
            <line x1="12" y1="1" x2="12" y2="23" />
            <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
          </svg>
        </div>
        <div>
          <div className="kpi-label">Return expected</div>
          <div className="kpi-val">{formatBRL(expectedReturn)}</div>
        </div>
      </div>
    </div>
  );
}

interface FilterBarProps {
  searchDraft: string;
  onSearchChange: (v: string) => void;
  onApply: () => void;
  scoreFilter: ScoreFilter;
  valueFilter: ValueFilter;
  openDropdown: "score" | "value" | null;
  onToggleDropdown: (d: "score" | "value") => void;
  onSelectScore: (v: ScoreFilter) => void;
  onSelectValue: (v: ValueFilter) => void;
}

function FilterBar({
  searchDraft,
  onSearchChange,
  onApply,
  scoreFilter,
  valueFilter,
  openDropdown,
  onToggleDropdown,
  onSelectScore,
  onSelectValue,
}: FilterBarProps) {
  const scoreOption = SCORE_OPTIONS.find((o) => o.value === scoreFilter) ?? SCORE_OPTIONS[0];
  const valueOption = VALUE_OPTIONS.find((o) => o.value === valueFilter) ?? VALUE_OPTIONS[0];
  return (
    <div className="filter-bar">
      <div className="filter-group grow">
        <div className="filter-label">Buscar</div>
        <div className="filter-search">
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            placeholder="Client token (for example, DEMO-003)"
            value={searchDraft}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onApply();
            }}
          />
        </div>
      </div>

      <div className="filter-group dropdown-wrap">
        <div className="filter-label">Faixa de score</div>
        <div className="filter-select-btn" onClick={() => onToggleDropdown("score")}>
          <span>{scoreOption.label}</span>
          <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
        <div className={`dropdown-menu${openDropdown === "score" ? " open" : ""}`}>
          <div className="dropdown-header">Faixa de score</div>
          {SCORE_OPTIONS.map((opt) => (
            <div
              key={opt.value}
              className={`dropdown-item${opt.value === scoreFilter ? " selected" : ""}`}
              onClick={() => onSelectScore(opt.value)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {opt.color && (
                  <span
                    style={{
                      display: "inline-block",
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: opt.color,
                    }}
                  />
                )}
                <div>
                  <div>{opt.label}</div>
                  {opt.sub && (
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{opt.sub}</div>
                  )}
                </div>
              </div>
              {opt.value === scoreFilter && (
                <div className="check-icon">
                  <svg width="10" height="10" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="filter-group dropdown-wrap">
        <div className="filter-label">Value range</div>
        <div className="filter-select-btn" onClick={() => onToggleDropdown("value")}>
          <span>{valueOption.label}</span>
          <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
        <div className={`dropdown-menu${openDropdown === "value" ? " open" : ""}`}>
          <div className="dropdown-header">Value range</div>
          {VALUE_OPTIONS.map((opt) => (
            <div
              key={opt.value}
              className={`dropdown-item${opt.value === valueFilter ? " selected" : ""}`}
              onClick={() => onSelectValue(opt.value)}
            >
              <span>{opt.label}</span>
              {opt.value === valueFilter && (
                <div className="check-icon">
                  <svg width="10" height="10" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <button className="btn-apply" onClick={onApply}>
        Aplicar
      </button>
    </div>
  );
}

function RequestCard({
  client,
  onDetails,
}: {
  client: DashboardClientSchema;
  onDetails: () => void;
}) {
  const score = classifyScore(client.score);
  const categoria: LimitCategory = classifyLimit(
    client.suggested_limit,
    client.payment_capacity,
  );
  const hasLimit = client.suggested_limit !== null && client.suggested_limit !== undefined;
  return (
    <div className="req-card">
      <div className="req-avatar" style={{ background: avatarColorFor(client.token) }}>
        {tokenInitials(client.token)}
      </div>
      <div className="req-info">
        <div className="req-name">{client.token}</div>
        <div className="req-sub">PD {(client.pd * 100).toFixed(1)}%</div>
      </div>
      <div className="req-field">
        <span className="req-field-label">Capacity de payment</span>
        <span className="req-field-val">{formatBRL(client.payment_capacity)}</span>
      </div>
      <div className="req-field">
        <span className="req-field-label">Score</span>
        <div className="score-wrap">
          <span className="score-num">{client.score.toFixed(0)}</span>
          <span className={`score-badge ${score.className}`}>{score.label}</span>
        </div>
      </div>
      <div className="req-field" style={{ minWidth: 150 }}>
        <span className="req-field-label">Limit sugerido</span>
        {hasLimit ? (
          <div className="limit-sugerido">
            <span className="limit-val">{formatBRL(client.suggested_limit)}</span>
            <span className={`limit-badge ${LIMIT_BADGE_CLASS[categoria]}`}>
              {LIMIT_BADGE_LABEL[categoria]}
            </span>
          </div>
        ) : (
          <div className="limit-waiting">
            <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <rect x="3" y="11" width="18" height="11" rx="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            Waiting for analysis
          </div>
        )}
      </div>
      <button className="btn-details" onClick={onDetails}>
        Ver details
        <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}

// ── Upload modal (TASK-04) ──
interface UploadModalProps {
  existing: File | null;
  onClose: () => void;
  onConfirm: (file: File) => void;
}

function UploadModal({ existing, onClose, onConfirm }: UploadModalProps) {
  const [info, setInfo] = useState<UploadInfo | null>(null);
  const [invalid, setInvalid] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);


  useEffect(() => {
    if (existing) {
      void parseFile(existing).then((parsed) => {
        if (parsed.invalid) setInvalid(parsed.invalid);
        else setInfo(parsed.info);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFile = useCallback(async (file: File) => {
    setInvalid(null);
    setInfo(null);
    const parsed = await parseFile(file);
    if (parsed.invalid) {
      setInvalid(parsed.invalid);
    } else {
      setInfo(parsed.info);
    }
  }, []);

  const onInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void handleFile(file);
    },
    [handleFile],
  );

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) void handleFile(file);
    },
    [handleFile],
  );

  const canConfirm = info !== null && info.missing.length === 0;
  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-box" style={{ width: 520 }}>
        <div className="modal-header">
          <div className="modal-header-left">
            <div className="modal-avatar" style={{ background: "#07B2FD" }}>
              <svg width="18" height="18" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div>
              <div className="modal-name">Update data</div>
              <div className="modal-cpf">Upload a client CSV or Parquet file for analysis</div>
            </div>
          </div>
          <button className="btn-close-x" onClick={onClose}>
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="modal-body" style={{ gap: 16 }}>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.parquet,.pq"
            style={{ display: "none" }}
            onChange={onInputChange}
          />

          {invalid ? (
            <div className="upload-area has-error">
              <div className="upload-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <div className="upload-file-info">
                <div className="upload-file-name">Invalid file</div>
                <div className="upload-error-msg" style={{ marginTop: 4 }}>
                  <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {invalid}
                </div>
              </div>
              <div className="upload-actions">
                <button
                  className="btn-upload-remove"
                  onClick={() => {
                    setInvalid(null);
                    if (inputRef.current) inputRef.current.value = "";
                  }}
                >
                  Remover
                </button>
              </div>
            </div>
          ) : info ? (
            <div className="upload-area has-file">
              <div className="upload-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <div className="upload-file-info">
                <div className="upload-file-name">{info.file.name}</div>
                <div className="upload-file-meta">
                  {info.cols.length} columns ·{" "}
                  {info.rowCount === null
                    ? "row count unavailable"
                    : `${info.rowCount.toLocaleString("en-US")} ${
                        info.rowCount === 1 ? "row" : "rows"
                      }`}{" "}
                  · {info.sizeMB} MB
                </div>
                <div className="upload-badges">
                  <span className={`upload-badge ${info.missing.length === 0 ? "badge-ok" : "badge-err"}`}>
                    {info.canPreviewColumns
                      ? info.missing.length === 0
                        ? "✓ Valid columns"
                        : "× Columns missing"
                      : "✓ Validado no envio"}
                  </span>
                  <span className="upload-badge badge-ok">.{info.ext.toUpperCase()}</span>
                </div>
              </div>
              <div className="upload-actions">
                <button
                  className="btn-upload-remove"
                  onClick={() => {
                    setInfo(null);
                    setInvalid(null);
                    if (inputRef.current) inputRef.current.value = "";
                  }}
                >
                  Remover
                </button>
              </div>
            </div>
          ) : (
            <div
              className={`upload-area${dragOver ? " drag-over" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
            >
              <div className="upload-icon">
                <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div>
                <div className="upload-text-main">
                  Drag a file or{" "}
                  <span className="upload-link">click to select</span>
                </div>
                <div className="upload-text-sub">
                  Formatos aceitos: <strong>.csv</strong>, <strong>.parquet</strong> e <strong>.pq</strong>
                </div>
              </div>
            </div>
          )}

          {info && info.canPreviewColumns && (
            <div className="cols-preview">
              <div className="cols-preview-title">Columns detected in the file</div>
              <div className="cols-list">
                {REQUIRED_COL_GROUPS.map((g) => {
                  const present = g.aliases.find((a) => info.cols.includes(a));
                  return (
                    <span
                      key={g.label}
                      className={`col-tag ${present ? "col-required" : "col-missing"}`}
                      title={
                        present
                          ? `Required · present as "${present}"`
                          : `Required · MISSING (accepted: ${g.aliases.join(" or ")})`
                      }
                    >
                      {present ?? `⚠ ${g.label}`}
                    </span>
                  );
                })}
                {info.cols
                  .filter(
                    (c) =>
                      !REQUIRED_COL_GROUPS.some((g) => g.aliases.includes(c)),
                  )
                  .map((c) => (
                    <span key={c} className="col-tag col-optional" title="Column adicional">
                      {c}
                    </span>
                  ))}
              </div>
              {info.missing.length > 0 && (
                <div className="upload-error-msg" style={{ marginTop: 6 }}>
                  <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  Missing required columns: {info.missing.join(", ")}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer" style={{ justifyContent: "space-between" }}>
          <button className="btn-close secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            className="btn-close"
            disabled={!canConfirm}
            onClick={() => info && onConfirm(info.file)}
          >
            Confirmar file
          </button>
        </div>
      </div>
    </div>
  );
}

async function parseFile(
  file: File,
): Promise<{ info: UploadInfo; invalid: null } | { info: null; invalid: string }> {
  const ext = (file.name.split(".").pop() ?? "").toLowerCase();
  if (!ACCEPTED_EXTS.includes(ext)) {
    return { info: null, invalid: "Invalid format. Use .csv, .parquet, or .pq." };
  }
  const sizeMB = (file.size / 1024 / 1024).toFixed(2);
  let cols: string[] = [];
  let rowCount: number | null = null;
  let canPreviewColumns = false;
  if (ext === "csv") {
    try {
      const preview = await readCsvPreview(file);
      const firstLine = preview.firstLine;
      cols = firstLine
        .split(",")
        .map((c) => c.trim().toLowerCase().replace(/"/g, ""))
        .filter(Boolean);
      rowCount = preview.rowCount;
      canPreviewColumns = true;
    } catch {
      cols = [];
      rowCount = null;
    }
  } else {
    // Parquet is not parsed in the browser; the backend performs authoritative validation.
    cols = [];
  }
  const missing = canPreviewColumns
    ? REQUIRED_COL_GROUPS.filter(
        (g) => !g.aliases.some((alias) => cols.includes(alias)),
      ).map((g) => g.label)
    : [];
  return {
    info: { file, cols, missing, sizeMB, ext, rowCount, canPreviewColumns },
    invalid: null,
  };
}

async function readCsvPreview(file: File): Promise<{ firstLine: string; rowCount: number }> {
  const chunkSize = 1024 * 1024;
  const decoder = new TextDecoder();
  let pending = "";
  let firstLine = "";
  let hasHeader = false;
  let rowCount = 0;

  for (let offset = 0; offset < file.size; offset += chunkSize) {
    const isLast = offset + chunkSize >= file.size;
    pending += decoder.decode(await file.slice(offset, offset + chunkSize).arrayBuffer(), {
      stream: !isLast,
    });

    const lines = pending.split(/\r\n|\n|\r/);
    pending = lines.pop() ?? "";

    for (const line of lines) {
      if (!hasHeader) {
        firstLine = line;
        hasHeader = true;
      } else if (line.trim().length > 0) {
        rowCount += 1;
      }
    }

    await new Promise((resolve) => window.setTimeout(resolve, 0));
  }

  if (pending.length > 0) {
    if (!hasHeader) {
      firstLine = pending;
    } else if (pending.trim().length > 0) {
      rowCount += 1;
    }
  }

  return { firstLine, rowCount };
}

// ── Algorithm picker modal (TASK-04) ──
function AlgorithmModal({
  algorithm,
  onSelect,
  onClose,
  onConfirm,
}: {
  algorithm: Algorithm;
  onSelect: (a: Algorithm) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-box" style={{ width: 560 }}>
        <div className="modal-header">
          <div className="modal-header-left">
            <div className="modal-avatar" style={{ background: "#07B2FD" }}>
              <svg width="18" height="18" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M18 20V10M12 20V4M6 20v-6" />
              </svg>
            </div>
            <div>
              <div className="modal-name">Escolher algorithm</div>
              <div className="modal-cpf">Select the method used to optimize limits</div>
            </div>
          </div>
          <button className="btn-close-x" onClick={onClose}>
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="modal-body" style={{ gap: 16 }}>
          <div className="algorithm-options">
            <button
              className={`algorithm-option${algorithm === "branch_bound" ? " selected" : ""}`}
              onClick={() => onSelect("branch_bound")}
            >
              <div className="algorithm-option-title">Branch and Bound</div>
              <div className="algorithm-option-sub">
                Integer search for scenarios with discrete decision constraints.
              </div>
            </button>
            <button
              className={`algorithm-option${algorithm === "simplex" ? " selected" : ""}`}
              onClick={() => onSelect("simplex")}
            >
              <div className="algorithm-option-title">Simplex</div>
              <div className="algorithm-option-sub">
                Linear optimization for fast runs with continuous variables.
              </div>
            </button>
            <button
              className={`algorithm-option${algorithm === "simplex_ortools" ? " selected" : ""}`}
              onClick={() => onSelect("simplex_ortools")}
            >
              <div className="algorithm-option-title">Simplex OR-Tools</div>
              <div className="algorithm-option-sub">
                Solve the same linear model with the Google OR-Tools GLOP solver.
              </div>
            </button>
          </div>
        </div>
        <div className="modal-footer" style={{ justifyContent: "space-between" }}>
          <button className="btn-close secondary" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn-close" onClick={onConfirm}>
            Continuar
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Loading modal (TASK-05 view) ──
function LoadingModal({
  algorithmLabel,
  uploading,
  state,
  currentStage,
  startedAt,
  onCancel,
}: {
  algorithmLabel: string;
  uploading: boolean;
  state: string | null;
  currentStage: string | null;
  startedAt: number | null;
  onCancel: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const elapsedMs = startedAt ? Math.max(0, now - startedAt) : 0;
  const progress = uploading
    ? {
        index: -1,
        pct: Math.min(25, 6 + Math.floor(elapsedMs / 5000)),
      }
    : etapaProgress(state);

  return (
    <div className="main-overlay">
      <div className="modal-loading">
        <div className="pulso-wrap">
          <div className="pulso-circle pulso-c1"></div>
          <div className="pulso-circle pulso-c2"></div>
          <div className="pulso-circle pulso-c3">
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
            </svg>
          </div>
        </div>
        <div className="loading-title">Optimizing credit limits</div>
        <div className="loading-sub">
          {uploading
            ? "Uploading and importing data in the backend..."
            : `Analyzing applications with ${algorithmLabel}`}
        </div>
        <div className="runtime-panel">
          <span>Time in this run</span>
          <strong>{formatElapsed(elapsedMs)}</strong>
        </div>
        <div className="progress-wrap">
          <div className="progress-labels">
            <span>Progresso</span>
            <span className="progress-pct">{progress.pct}%</span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress.pct}%` }} />
          </div>
        </div>
        <div className="stages-list">
          {ETAPAS_FLUXO.map((key, idx) => {
            const isDone = progress.index > idx || state === "completed";
            const isCurrent = !isDone && progress.index === idx && !uploading;
            return (
              <div className="stage" key={key}>
                <div className="stage-left">
                  <div
                    className={`stage-icon ${
                      isDone ? "stage-completed" : isCurrent ? "stage-in-progress" : "stage-pending"
                    }`}
                  >
                    {isDone ? (
                      <svg width="10" height="10" fill="none" stroke="white" strokeWidth="3" viewBox="0 0 24 24">
                        <path d="M20 6L9 17l-5-5" />
                      </svg>
                    ) : isCurrent ? (
                      <span className="stage-in-progress-dot" />
                    ) : null}
                  </div>
                  <span>{ETAPA_LABEL[key]}</span>
                </div>
                <span
                  className={`stage-label-status ${
                    isDone
                      ? "stage-label-completed"
                      : isCurrent
                        ? "stage-label-in-progress"
                        : ""
                  }`}
                >
                  {isDone ? "Completed" : isCurrent ? "In progress..." : ""}
                </span>
              </div>
            );
          })}
        </div>
        <div className="loading-info">
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {currentStage ?? "Waiting for the backend to start the run..."}
        </div>
        <div className="loading-info secondary">
          History records backend time; this timer measures elapsed time in the current view.
        </div>
        <button className="btn-cancelar" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

// ── Detalhes modal (TASK-07) ──
function DetalhesModal({
  token,
  clientRow,
  detail,
  loading,
  error,
  onClose,
}: {
  token: string;
  clientRow: DashboardClientSchema | null;
  detail: ClientResultSchema | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  const pd = detail?.pd ?? clientRow?.pd ?? null;
  const capacity = detail?.payment_capacity ?? clientRow?.payment_capacity ?? null;
  const scoreNorm = detail?.propensity_score ?? clientRow?.score ?? null;
  const limit = detail?.suggested_limit ?? clientRow?.suggested_limit ?? null;
  const categoria: LimitCategory = classifyLimit(limit, capacity);
  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-box">
        <div className="modal-header">
          <div className="modal-header-left">
            <div className="modal-avatar" style={{ background: avatarColorFor(token) }}>
              {tokenInitials(token)}
            </div>
            <div>
              <div className="modal-name">{token}</div>
              <div className="modal-cpf">Client anonimizado</div>
            </div>
          </div>
          <button className="btn-close-x" onClick={onClose}>
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="modal-body">
          {}
          <div>
            <div className="modal-section-title">
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
              </svg>
              Model variables
            </div>
            <div className="variable-pills">
              <div className="variable-pill">
                <div className="variable-pill-label">PD (DEFAULT)</div>
                <div className="variable-pill-val">{formatPct(pd, 1)}</div>
              </div>
              <div className="variable-pill">
                <div className="variable-pill-label">SCORE NORMALIZADO</div>
                <div className="variable-pill-val">
                  {scoreNorm !== null ? scoreNorm.toFixed(0) : "—"}
                </div>
              </div>
              <div className="variable-pill">
                <div className="variable-pill-label">CAPACITY</div>
                <div className="variable-pill-val">{formatBRL(capacity)}</div>
              </div>
            </div>
          </div>

          {}
          <div>
            <div className="modal-section-title">
              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <rect x="3" y="11" width="18" height="11" rx="2" />
                <path d="M7 11V7a5 5 0 0110 0v4" />
              </svg>
              Algorithm decision
            </div>
            {loading ? (
              <div className="detail-status">Carregando details...</div>
            ) : error ? (
              <div className="detail-status">{error}</div>
            ) : limit === null || limit === 0 ? (
              <div className="decisao-vazia">
                <div className="decisao-vazia-icon">
                  <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0110 0v4" />
                  </svg>
                </div>
                <h3>No recommendation</h3>
                <p>The algorithm did not assign a limit to this client.</p>
              </div>
            ) : (
              <div className="decisao-card">
                <div className="decisao-top">
                  <div>
                    <div className="decision-label">LIMIT SUGERIDO</div>
                    <div className="decisao-val">{formatBRLFull(limit)}</div>
                  </div>
                  <div className={`decisao-badge db-${categoria === "denied" ? "parcial" : categoria}`}>
                    ✓ {LIMIT_BADGE_LABEL[categoria]}
                  </div>
                </div>
                {detail && (
                  <>
                    <div className="calculation-title">Componentes calculados</div>
                    <div className="calculation-row">
                      <span>Income expected</span>
                      <span>{formatBRLFull(detail.expected_income)}</span>
                    </div>
                    <div className="calculation-row">
                      <span>− Loss expected (PD × LGD)</span>
                      <span>− {formatBRLFull(detail.expected_loss)}</span>
                    </div>
                    <div className="calculation-row" style={{ fontWeight: 700 }}>
                      <span>= Return expected</span>
                      <span>{formatBRLFull(detail.expected_return)}</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-close" onClick={onClose}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
