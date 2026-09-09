"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  compareRuns,
  deleteExecution,
  downloadComparisonPdf,
  downloadExecutionCsv,
  downloadReportPdf,
  getExecutionDetail,
  getExecutionHistory,
} from "@/lib/api";
import { ApiResponseError } from "@/lib/types";
import {
  STATUS_BADGE_CLASS,
  STATUS_LABEL,
  daysFromNow,
  formatAlgorithm,
  formatBRL,
  formatBRLFull,
  formatDateTime,
  formatDuracao,
  formatPct,
  formatRunId,
} from "@/lib/format";
import type {
  ComparisonDeltaItemSchema,
  ComparisonRunsDataSchema,
  ExecutionDetailSchema,
  ExecutionHistoryItemSchema,
  RunStatusFinal,
} from "@/lib/types";

type PeriodoFilter = "all" | "hoje" | "7d" | "30d" | "90d";
type StatusFilter = "all" | RunStatusFinal;

const PERIODO_OPTIONS: { value: PeriodoFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "hoje", label: "Hoje" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
];

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "success", label: "Completed" },
  { value: "error", label: "With error" },
  { value: "pending", label: "Pending" },
  { value: "timeout", label: "Timeout" },
];

const PERIODO_MAX_DAYS: Record<PeriodoFilter, number | null> = {
  all: null,
  hoje: 0,
  "7d": 7,
  "30d": 30,
  "90d": 90,
};

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [periodo, setPeriodo] = useState<PeriodoFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [openDropdown, setOpenDropdown] = useState<"periodo" | "status" | null>(null);
  const [sortDesc, setSortDesc] = useState(true);

  const [page, setPage] = useState(1);
  const [items, setItems] = useState<ExecutionHistoryItemSchema[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [openCards, setOpenCards] = useState<Set<number>>(new Set());
  const [detailCache, setDetailCache] = useState<Map<number, ExecutionDetailSchema>>(new Map());
  const [detailLoading, setDetailLoading] = useState<Set<number>>(new Set());
  const [detailErrors, setDetailErrors] = useState<Map<number, string>>(new Map());
  const [pdfLoading, setPdfLoading] = useState<Set<number>>(new Set());
  const [csvLoading, setCsvLoading] = useState<Set<number>>(new Set());
  const [deleteLoading, setDeleteLoading] = useState<Set<number>>(new Set());

  const [compareMode, setCompareMode] = useState(false);
  const [compareSelection, setCompareSelection] = useState<number[]>([]);
  const [comparison, setComparison] = useState<ComparisonRunsDataSchema | null>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonPdfLoading, setComparisonPdfLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);


  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getExecutionHistory({
      page,
      page_size: PAGE_SIZE,
      status: statusFilter === "all" ? undefined : statusFilter,
    })
      .then((data) => {
        if (!active) return;
        setItems(data.items);
        setTotalItems(data.total_items);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setItems([]);
        setTotalItems(0);
        setError(err instanceof ApiResponseError ? err.message : "Failed to load run history.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [page, statusFilter]);


  const visibleItems = useMemo(() => {
    let data = [...items];
    if (search) {
      const needle = search.toLowerCase();
      data = data.filter(
        (r) =>
          formatRunId(r.run_id).toLowerCase().includes(needle) ||
          r.file_name.toLowerCase().includes(needle),
      );
    }
    const maxDays = PERIODO_MAX_DAYS[periodo];
    if (maxDays !== null) {
      data = data.filter((r) => daysFromNow(r.created_at) <= maxDays);
    }
    data.sort((a, b) => {
      const ta = new Date(a.created_at).getTime();
      const tb = new Date(b.created_at).getTime();
      return sortDesc ? tb - ta : ta - tb;
    });
    return data;
  }, [items, search, periodo, sortDesc]);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      const target = event.target as HTMLElement | null;
      if (!target?.closest(".dropdown-wrap")) setOpenDropdown(null);
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const applyFilters = useCallback(() => setSearch(searchDraft), [searchDraft]);

  const toggleCard = useCallback(
    (runId: number) => {
      setOpenCards((prev) => {
        const next = new Set(prev);
        if (next.has(runId)) next.delete(runId);
        else next.add(runId);
        return next;
      });
      if (!detailCache.has(runId) && !detailLoading.has(runId)) {
        setDetailLoading((prev) => new Set(prev).add(runId));
        getExecutionDetail(runId)
          .then((detail) => {
            setDetailCache((prev) => new Map(prev).set(runId, detail));
            setDetailErrors((prev) => {
              const next = new Map(prev);
              next.delete(runId);
              return next;
            });
          })
          .catch((err: unknown) => {
            const msg =
              err instanceof ApiResponseError ? err.message : "Failed to load details.";
            setDetailErrors((prev) => new Map(prev).set(runId, msg));
          })
          .finally(() => {
            setDetailLoading((prev) => {
              const next = new Set(prev);
              next.delete(runId);
              return next;
            });
          });
      }
    },
    [detailCache, detailLoading],
  );

  const exportCsv = useCallback(async (runId: number) => {
    setCsvLoading((prev) => new Set(prev).add(runId));
    try {
      await downloadExecutionCsv(runId);
    } catch (err) {
      alert(err instanceof ApiResponseError ? err.message : "Failed to download the CSV.");
    } finally {
      setCsvLoading((prev) => {
        const next = new Set(prev);
        next.delete(runId);
        return next;
      });
    }
  }, []);

  const exportPdf = useCallback(async (runId: number) => {
    setPdfLoading((prev) => new Set(prev).add(runId));
    try {
      await downloadReportPdf({ run_id: runId });
    } catch (err) {
      alert(err instanceof ApiResponseError ? err.message : "Failed to generate the PDF.");
    } finally {
      setPdfLoading((prev) => {
        const next = new Set(prev);
        next.delete(runId);
        return next;
      });
    }
  }, []);

  const deleteRun = useCallback((runId: number) => {
    if (
      !window.confirm(
        `Delete run ${formatRunId(runId)}? Its associated results and data will be permanently removed.`,
      )
    ) {
      return;
    }
    setDeleteLoading((prev) => new Set(prev).add(runId));
    deleteExecution(runId)
      .then(() => {
        setItems((prev) => prev.filter((r) => r.run_id !== runId));
        setTotalItems((prev) => Math.max(0, prev - 1));
        setOpenCards((prev) => {
          const next = new Set(prev);
          next.delete(runId);
          return next;
        });
        setDetailCache((prev) => {
          const next = new Map(prev);
          next.delete(runId);
          return next;
        });
        setCompareSelection((prev) => prev.filter((id) => id !== runId));
      })
      .catch((err: unknown) => {
        alert(err instanceof ApiResponseError ? err.message : "Failed to delete the run.");
      })
      .finally(() => {
        setDeleteLoading((prev) => {
          const next = new Set(prev);
          next.delete(runId);
          return next;
        });
      });
  }, []);

  const toggleCompareSelection = useCallback((runId: number) => {
    setCompareSelection((prev) => {
      if (prev.includes(runId)) return prev.filter((id) => id !== runId);
      if (prev.length >= 2) return [prev[1], runId];
      return [...prev, runId];
    });
  }, []);

  const runComparison = useCallback(async () => {
    if (compareSelection.length !== 2) return;
    setComparisonLoading(true);
    setComparisonError(null);
    setComparison(null);
    try {
      const data = await compareRuns(compareSelection[0], compareSelection[1]);
      setComparison(data);
    } catch (err) {
      setComparisonError(
        err instanceof ApiResponseError ? err.message : "Failed to compare runs.",
      );
    } finally {
      setComparisonLoading(false);
    }
  }, [compareSelection]);

  const exportComparisonPdf = useCallback(async () => {
    if (!comparison) return;
    setComparisonPdfLoading(true);
    try {
      await downloadComparisonPdf(comparison.reference.run_id, comparison.compared.run_id);
    } catch (err) {
      alert(err instanceof ApiResponseError ? err.message : "Failed to generate the comparison PDF.");
    } finally {
      setComparisonPdfLoading(false);
    }
  }, [comparison]);

  const exitCompareMode = useCallback(() => {
    setCompareMode(false);
    setCompareSelection([]);
    setComparison(null);
    setComparisonError(null);
  }, []);

  const latestId = sortDesc ? visibleItems[0]?.run_id : undefined;

  return (
    <div className="screen active">
      <div className="breadcrumb">
        Algorithm › <span>Run history</span>
      </div>
      <h1 className="page-title">History</h1>

      {/* Filtros */}
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
              placeholder="Run ID or file..."
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") applyFilters();
              }}
            />
          </div>
        </div>

        <FilterDropdown
          label="Period"
          open={openDropdown === "periodo"}
          onToggle={() => setOpenDropdown(openDropdown === "periodo" ? null : "periodo")}
          options={PERIODO_OPTIONS}
          value={periodo}
          onSelect={(v) => {
            setPeriodo(v);
            setOpenDropdown(null);
          }}
        />

        <FilterDropdown
          label="Status"
          open={openDropdown === "status"}
          onToggle={() => setOpenDropdown(openDropdown === "status" ? null : "status")}
          options={STATUS_OPTIONS}
          value={statusFilter}
          onSelect={(v) => {
            setStatusFilter(v);
            setPage(1);
            setOpenDropdown(null);
          }}
        />

        <button className="btn-apply" onClick={applyFilters}>
          Aplicar
        </button>
      </div>

      {}
      {compareMode && (
        <div className="compare-banner">
          <div className="compare-banner-text">
            <strong>Comparison mode</strong> — select two completed runs (
            {compareSelection.length}/2 escolhidas).
          </div>
          <div className="compare-banner-actions">
            <button
              className="btn-apply"
              disabled={compareSelection.length !== 2 || comparisonLoading}
              onClick={runComparison}
            >
              {comparisonLoading ? "Comparing..." : "Compare agora"}
            </button>
            <button
              className="btn-modo-compare"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
              onClick={exitCompareMode}
            >
              Sair
            </button>
          </div>
        </div>
      )}

      {comparisonError && (
        <div className="compare-banner" style={{ background: "#fef2f2", borderColor: "#fecaca" }}>
          <div className="compare-banner-text" style={{ color: "#991b1b" }}>
            {comparisonError}
          </div>
        </div>
      )}

      {comparison && (
        <ComparisonResult
          data={comparison}
          onClose={() => setComparison(null)}
          onExportPdf={exportComparisonPdf}
          pdfLoading={comparisonPdfLoading}
        />
      )}

      {/* List controls */}
      <div className="list-controls">
        <span className="list-count">
          {loading
            ? "Loading runs..."
            : `${visibleItems.length} de ${totalItems} ${
                totalItems === 1 ? "run found" : "runs found"
              }`}
        </span>
        <div className="list-controls-right">
          {!compareMode && (
            <button
              className="btn-modo-compare"
              onClick={() => setCompareMode(true)}
              title="Compare two completed runs"
            >
              <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
                <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                <line x1="12" y1="22.08" x2="12" y2="12" />
              </svg>
              Comparison mode
            </button>
          )}
          <span className="sort-control">
            Sort by:{" "}
            <strong onClick={() => setSortDesc((v) => !v)}>
              {sortDesc ? "Mais recente ↓" : "Mais antigo ↑"}
            </strong>
          </span>
        </div>
      </div>

      {error && (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="empty-title">Run history could not be loaded</div>
          <div className="empty-sub">{error}</div>
        </div>
      )}

      {!error && !loading && visibleItems.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div className="empty-title">No run was found</div>
          <div className="empty-sub">
            Adjust the filters or run the algorithm from the home page.
          </div>
        </div>
      )}

      {!error && visibleItems.length > 0 && (
        <div className="runs-list">
          {visibleItems.map((run) => (
            <RunCard
              key={run.run_id}
              run={run}
              isLatest={run.run_id === latestId}
              open={openCards.has(run.run_id)}
              detail={detailCache.get(run.run_id) ?? null}
              detailLoading={detailLoading.has(run.run_id)}
              detailError={detailErrors.get(run.run_id) ?? null}
              onToggle={() => toggleCard(run.run_id)}
              csvLoading={csvLoading.has(run.run_id)}
              pdfLoading={pdfLoading.has(run.run_id)}
              deleteLoading={deleteLoading.has(run.run_id)}
              onDownloadCsv={() => exportCsv(run.run_id)}
              onDownloadPdf={() => exportPdf(run.run_id)}
              onDelete={() => deleteRun(run.run_id)}
              compareMode={compareMode}
              compareSelected={compareSelection.includes(run.run_id)}
              onToggleCompare={() => toggleCompareSelection(run.run_id)}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="history-pagination">
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
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────

interface FilterDropdownProps<T extends string> {
  label: string;
  open: boolean;
  onToggle: () => void;
  options: { value: T; label: string }[];
  value: T;
  onSelect: (value: T) => void;
}

function FilterDropdown<T extends string>({
  label,
  open,
  onToggle,
  options,
  value,
  onSelect,
}: FilterDropdownProps<T>) {
  const current = options.find((o) => o.value === value) ?? options[0];
  return (
    <div className="filter-group dropdown-wrap">
      <div className="filter-label">{label}</div>
      <div className="filter-select-btn" onClick={onToggle}>
        <span>{current.label}</span>
        <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>
      <div className={`dropdown-menu${open ? " open" : ""}`}>
        <div className="dropdown-header">{label}</div>
        {options.map((opt) => (
          <div
            key={opt.value}
            className={`dropdown-item${opt.value === value ? " selected" : ""}`}
            onClick={() => onSelect(opt.value)}
          >
            <span>{opt.label}</span>
            {opt.value === value && (
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
  );
}

interface RunCardProps {
  run: ExecutionHistoryItemSchema;
  isLatest: boolean;
  open: boolean;
  detail: ExecutionDetailSchema | null;
  detailLoading: boolean;
  detailError: string | null;
  onToggle: () => void;
  csvLoading: boolean;
  pdfLoading: boolean;
  deleteLoading: boolean;
  onDownloadCsv: () => void;
  onDownloadPdf: () => void;
  onDelete: () => void;
  compareMode: boolean;
  compareSelected: boolean;
  onToggleCompare: () => void;
}

function RunCard({
  run,
  isLatest,
  open,
  detail,
  detailLoading,
  detailError,
  onToggle,
  csvLoading,
  pdfLoading,
  deleteLoading,
  onDownloadCsv,
  onDownloadPdf,
  onDelete,
  compareMode,
  compareSelected,
  onToggleCompare,
}: RunCardProps) {
  const isError = run.status === "error" || run.status === "timeout";
  const algorithm = formatAlgorithm(run.algorithm);
  const ext = (run.file_name.split(".").pop() ?? "csv").toUpperCase();
  const compareEligible = run.status === "success";

  const onHeaderClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest("[data-stop]")) return;
    onToggle();
  };

  return (
    <div className={`run-card${open ? " open" : ""}${compareSelected ? " compare-selected" : ""}`}>
      <div className="run-card-header" onClick={onHeaderClick}>
        <div className={`run-index${isLatest ? " run-latest" : ""}`}>#{run.run_id}</div>
        <div className="run-header-info">
          <div className="run-title">
            {formatRunId(run.run_id)}
            <span className={`run-badge ${STATUS_BADGE_CLASS[run.status]}`}>
              {STATUS_LABEL[run.status]}
            </span>
            {isLatest && <span className="run-badge run-badge-latest">Mais recente</span>}
            {compareMode && (
              <button
                type="button"
                className={`compare-select-button${compareSelected ? " selected" : ""}${
                  !compareEligible ? " disabled" : ""
                }`}
                data-stop
                onClick={(e) => {
                  e.stopPropagation();
                  if (!compareEligible) return;
                  onToggleCompare();
                }}
                title={compareEligible ? "Select for comparison" : "Completed runs only"}
                disabled={!compareEligible}
              >
                <span className="compare-select-icon">{compareSelected ? "✓" : "+"}</span>
                {compareSelected ? "In comparison" : "Adicionar"}
              </button>
            )}
          </div>
          <div className="run-meta">
            <span>{formatDateTime(run.created_at)}</span>
            <span className="run-meta-dot"></span>
            <span>{run.file_name}</span>
            <span className="run-meta-dot"></span>
            <span>{algorithm}</span>
            <span className="run-meta-dot"></span>
            <span>⏱ {formatDuracao(run.execution_time_ms)}</span>
          </div>
        </div>
        {!isError && (
          <div className="run-kpis">
            <div className="run-kpi">
              <div className="run-kpi-label">Clients</div>
              <div className="run-kpi-val">{run.total_clients}</div>
            </div>
            <div className="run-kpi">
              <div className="run-kpi-label">Approval</div>
              <div className="run-kpi-val blue">{formatPct(run.approval_rate, 0)}</div>
            </div>
            <div className="run-kpi">
              <div className="run-kpi-label">Return</div>
              <div className="run-kpi-val green">{formatBRL(run.total_return)}</div>
            </div>
          </div>
        )}
        <button
          type="button"
          className={`run-download${isError || csvLoading ? " disabled" : ""}`}
          data-stop
          onClick={(e) => {
            e.stopPropagation();
            if (isError || csvLoading) return;
            onDownloadCsv();
          }}
          title={
            isError
              ? "File not processed — download unavailable"
              : "Download input file"
          }
          disabled={isError || csvLoading}
        >
          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          {csvLoading ? "..." : ext}
        </button>
        <svg
          className="run-chevron"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>

      {open && (
        <div className="run-body">
          <RunDetail
            run={run}
            detail={detail}
            loading={detailLoading}
            error={detailError}
            csvLoading={csvLoading}
            pdfLoading={pdfLoading}
            deleteLoading={deleteLoading}
            onDownloadCsv={onDownloadCsv}
            onDownloadPdf={onDownloadPdf}
            onDelete={onDelete}
          />
        </div>
      )}
    </div>
  );
}

interface RunDetailProps {
  run: ExecutionHistoryItemSchema;
  detail: ExecutionDetailSchema | null;
  loading: boolean;
  error: string | null;
  csvLoading: boolean;
  pdfLoading: boolean;
  deleteLoading: boolean;
  onDownloadCsv: () => void;
  onDownloadPdf: () => void;
  onDelete: () => void;
}

function RunDetail({
  run,
  detail,
  loading,
  error,
  csvLoading,
  pdfLoading,
  deleteLoading,
  onDownloadCsv,
  onDownloadPdf,
  onDelete,
}: RunDetailProps) {
  const isError = run.status === "error" || run.status === "timeout";

  if (loading && !detail) {
    return <div className="detail-status">Carregando details...</div>;
  }
  if (error && !detail) {
    return <div className="detail-status">{error}</div>;
  }
  if (!detail) return null;

  const total =
    (detail.distribution?.above ?? 0) +
    (detail.distribution?.full ?? 0) +
    (detail.distribution?.denied ?? 0);
  const pct = (n: number) => (total > 0 ? (n / total) * 100 : 0);

  return (
    <>
      {/* TASK-11 — CSV / PDF */}
      <div className="run-actions">
        <button
          type="button"
          className={`run-download-btn${isError || csvLoading ? " disabled" : ""}`}
          onClick={onDownloadCsv}
          disabled={isError || csvLoading}
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          {csvLoading ? "Baixando..." : "Baixar results em CSV"}
        </button>
        <button
          type="button"
          className={`run-download-btn primary${isError || pdfLoading ? " disabled" : ""}`}
          onClick={onDownloadPdf}
          disabled={isError || pdfLoading}
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          {pdfLoading ? "Gerando PDF..." : "Exportar PDF"}
        </button>
        <button
          type="button"
          className={`run-download-btn danger${deleteLoading ? " disabled" : ""}`}
          onClick={onDelete}
          disabled={deleteLoading}
          title="Permanently delete this run"
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
          {deleteLoading ? "Deleting..." : "Delete run"}
        </button>
      </div>

      {/* KPIs detalhados */}
      <div className="run-body-grid">
        {isError ? (
          <div className="run-error-card">
            <div className="run-detail-label">Error reason</div>
            <div className="run-error-msg">
              {detail.error_reason ?? "The backend did not provide error details."}
            </div>
          </div>
        ) : (
          <>
            <div className="run-detail-card">
              <div className="run-detail-label">Clients analisados</div>
              <div className="run-detail-val">{detail.total_clients}</div>
              <div className="run-detail-sub">
                {detail.approved} approved ({formatPct(detail.approval_rate, 0)})
              </div>
            </div>
            <div className="run-detail-card">
              <div className="run-detail-label">Limit total sugerido</div>
              <div className="run-detail-val">{formatBRL(detail.total_limit)}</div>
              <div className="run-detail-sub">
                Average per client:{" "}
                {detail.approved > 0
                  ? formatBRL((detail.total_limit ?? 0) / detail.approved)
                  : "—"}
              </div>
            </div>
            <div className="run-detail-card">
              <div className="run-detail-label">Return expected</div>
              <div className="run-detail-val" style={{ color: "#15803d" }}>
                {formatBRL(detail.total_return)}
              </div>
              <div className="run-detail-sub">
                Average score:{" "}
                {detail.average_approved_score !== null
                  ? detail.average_approved_score.toFixed(0)
                  : "—"}
              </div>
            </div>
          </>
        )}
      </div>

      {}
      {detail.distribution && total > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div className="dist-section-title">Result distribution</div>
          <div className="run-dist-bar">
            <div
              className="dist-seg"
              style={{ width: `${pct(detail.distribution.above)}%`, background: "#15803d" }}
              title={`Above capacity: ${detail.distribution.above}`}
            />
            <div
              className="dist-seg"
              style={{ width: `${pct(detail.distribution.full)}%`, background: "#22c55e" }}
              title={`Integral: ${detail.distribution.full}`}
            />
            <div
              className="dist-seg"
              style={{ width: `${pct(detail.distribution.denied)}%`, background: "#e2e8f0" }}
              title={`Negado: ${detail.distribution.denied}`}
            />
          </div>
          <div className="dist-legend">
            <span className="dist-legend-item" style={{ color: "#15803d" }}>
              <span className="dist-legend-dot" style={{ background: "#15803d" }} />
              Acima ({detail.distribution.above})
            </span>
            <span className="dist-legend-item" style={{ color: "#22c55e" }}>
              <span className="dist-legend-dot" style={{ background: "#22c55e" }} />
              Integral ({detail.distribution.full})
            </span>
            <span className="dist-legend-item" style={{ color: "#94a3b8" }}>
              <span className="dist-legend-dot" style={{ background: "#94a3b8" }} />
              Negado ({detail.distribution.denied})
            </span>
          </div>
        </div>
      )}

      {/* Limit ranges */}
      {detail.limit_ranges && detail.limit_ranges.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div className="run-params-title">Distribution by limit range</div>
          <table className="ranges-table">
            <thead>
              <tr>
                <th>Faixa</th>
                <th>Clients</th>
                <th>%</th>
                <th className="range-bar-cell"></th>
              </tr>
            </thead>
            <tbody>
              {detail.limit_ranges.map((b) => (
                <tr key={b.range}>
                  <td>{b.range}</td>
                  <td className="num">{b.count}</td>
                  <td className="num">{b.percentage.toFixed(1)}%</td>
                  <td className="range-bar-cell">
                    <div className="range-bar">
                      <div
                        className="range-bar-fill"
                        style={{ width: `${Math.min(100, b.percentage)}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {}
      {detail.parameters && (
        <div style={{ marginBottom: 14 }}>
          <div className="run-params-title">Settings used</div>
          <div className="run-params-grid">
            <ParamChip label="LGD" value={formatPct(detail.parameters.lgd, 0)} />
            <ParamChip label="Rate use" value={formatPct(detail.parameters.utilization_rate, 0)} />
            <ParamChip
              label="Baseline"
              value={formatPct(detail.parameters.baseline_default_rate, 2)}
            />
            <ParamChip
              label="Interchange"
              value={formatPct(detail.parameters.interchange, 2)}
            />
            <ParamChip label="Min. limit" value={formatBRL(detail.parameters.min_limit)} />
            <ParamChip label="Max. limit" value={formatBRL(detail.parameters.max_limit)} />
          </div>
        </div>
      )}

      {/* Log operacional */}
      {detail.operational_log && detail.operational_log.length > 0 && (
        <div>
          <div className="run-params-title">Log operacional</div>
          <div className="log-list">
            {detail.operational_log.map((entry, idx) => (
              <div key={`${entry.t}-${idx}`} className="log-item">
                <div className="log-time">{entry.t}</div>
                <div className={`log-icon ${entry.tipo}`}>{logGlyph(entry.tipo)}</div>
                <div className="log-msg">{entry.msg}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function ParamChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="run-param-chip">
      {label} <strong>{value}</strong>
    </div>
  );
}

function logGlyph(tipo: "info" | "ok" | "warn" | "error"): string {
  if (tipo === "ok") return "✓";
  if (tipo === "warn") return "!";
  if (tipo === "error") return "×";
  return "i";
}

interface ComparisonResultProps {
  data: ComparisonRunsDataSchema;
  onClose: () => void;
  onExportPdf: () => void;
  pdfLoading: boolean;
}

function ComparisonResult({ data, onClose, onExportPdf, pdfLoading }: ComparisonResultProps) {
  const { reference, compared, deltas } = data;

  return (
    <div className="comparison-result">
      <div className="comparison-header">
        <div className="comparison-title">Run comparison</div>
        <div className="comparison-header-actions">
          <button className="comparison-pdf" onClick={onExportPdf} disabled={pdfLoading}>
            {pdfLoading ? "Gerando PDF..." : "Exportar PDF"}
          </button>
          <button className="comparison-close" onClick={onClose}>
            Fechar ✕
          </button>
        </div>
      </div>

      <div className="comparison-snapshots">
        <SnapshotCol label="Reference" badge="A" snapshot={reference} />
        <SnapshotCol label="Compared" badge="B" snapshot={compared} />
      </div>

      <div className="comparison-deltas-title">Differences (B relative to A)</div>
      <div className="comparison-deltas">
        <DeltaCard
          label="Limit total"
          delta={deltas.total_limit}
          formatter={formatBRLFull}
          positiveIsGood
        />
        <DeltaCard
          label="Return total"
          delta={deltas.total_return}
          formatter={formatBRLFull}
          positiveIsGood
        />
        <DeltaCard
          label="Approval rate"
          delta={deltas.approval_rate}
          formatter={(v) => formatPct(v, 1)}
          positiveIsGood
        />
        <DeltaCard
          label="Financial default rate"
          delta={deltas.financial_default_rate}
          formatter={(v) => formatPct(v, 2)}
          positiveIsGood={false}
        />
        <DeltaCard
          label="Clients"
          delta={deltas.total_clients}
          formatter={(v) => v.toLocaleString("en-US")}
          positiveIsGood
        />
      </div>
    </div>
  );
}

function SnapshotCol({
  label,
  badge,
  snapshot,
}: {
  label: string;
  badge: string;
  snapshot: ComparisonRunsDataSchema["reference"];
}) {
  return (
    <div className="snapshot-col">
      <div className="snapshot-head">
        <div className="snapshot-badge">{badge}</div>
        <div>
          <div className="snapshot-name">
            {formatRunId(snapshot.run_id)} · {label}
          </div>
          <div className="snapshot-sub">
            {formatAlgorithm(snapshot.algorithm)} · {snapshot.file_name}
          </div>
        </div>
      </div>
      <div className="snapshot-metrics">
        <Metric label="Clients" value={snapshot.metrics.total_clients.toLocaleString("en-US")} />
        <Metric label="Limit total" value={formatBRLFull(snapshot.metrics.total_limit)} />
        <Metric label="Return total" value={formatBRLFull(snapshot.metrics.total_return)} />
        <Metric
          label="Approval rate"
          value={formatPct(snapshot.metrics.approval_rate, 1)}
        />
        <Metric
          label="Financial default rate"
          value={formatPct(snapshot.metrics.financial_default_rate, 2)}
        />
      </div>
      <div className="snapshot-params-title">Parameters used</div>
      <div className="snapshot-params">
        <Metric label="LGD" value={formatPct(snapshot.parameters.lgd, 0)} />
        <Metric label="Rate use" value={formatPct(snapshot.parameters.utilization_rate, 0)} />
        <Metric
          label="Baseline"
          value={formatPct(snapshot.parameters.baseline_default_rate, 2)}
        />
        <Metric label="Interchange" value={formatPct(snapshot.parameters.interchange, 2)} />
        <Metric label="Min. limit" value={formatBRL(snapshot.parameters.min_limit)} />
        <Metric label="Max. limit" value={formatBRL(snapshot.parameters.max_limit)} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="snapshot-metric">
      <span className="snapshot-metric-label">{label}</span>
      <span className="snapshot-metric-val">{value}</span>
    </div>
  );
}

function DeltaCard({
  label,
  delta,
  formatter,
  positiveIsGood,
}: {
  label: string;
  delta: ComparisonDeltaItemSchema;
  formatter: (val: number) => string;
  positiveIsGood: boolean;
}) {
  const isPositive = delta.absoluto > 0;
  const isNegative = delta.absoluto < 0;
  const klass = isPositive
    ? positiveIsGood
      ? "delta-positive"
      : "delta-negative"
    : isNegative
      ? positiveIsGood
        ? "delta-negative"
        : "delta-positive"
      : "delta-neutral";
  const sign = isPositive ? "+" : "";
  return (
    <div className="delta-card">
      <div className="delta-card-label">{label}</div>
      <div className={`delta-card-val ${klass}`}>
        {sign}
        {formatter(delta.absoluto)}
      </div>
      {delta.percentage !== null && (
        <div className={`delta-card-pct ${klass}`}>
          {sign}
          {delta.percentage.toFixed(1)}%
        </div>
      )}
    </div>
  );
}
