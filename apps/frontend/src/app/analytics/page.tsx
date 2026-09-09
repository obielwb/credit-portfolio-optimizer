"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  downloadReportPdf,
  downloadComparisonPdf,
  compareRuns,
  getExecutionHistory,
  getRunSnapshot,
} from "@/lib/api";
import {
  formatBRL,
  formatBRLFull,
  formatDateTime,
  formatPct,
  formatRunId,
} from "@/lib/format";
import {
  ApiResponseError,
  type ReturnGrouping,
  type ExecutionHistoryItemSchema,
  type RunComparisonSnapshotSchema,
} from "@/lib/types";
import { LimitsDistributionSketch } from "@/components/limits-distribution-sketch";

function limitVariation(capacity: number, limit: number): { label: string; positive: boolean } {
  if (!capacity) return { label: "0,0%", positive: true };
  const pct = ((limit - capacity) / capacity) * 100;
  const sign = pct >= 0 ? "+" : "";
  return {
    label: `${sign}${pct.toFixed(1).replace(".", ",")}%`,
    positive: pct >= 0,
  };
}

function agrupamentoCopy(agrupamento: ReturnGrouping) {
  if (agrupamento === "cluster") {
    return {
      returnTitle: "Return by cluster",
      returnSubtitle: "Breakdown by clustering group",
      compositionTitle: "Composition by cluster",
      analysisTitle: "Cluster analysis",
      groupColumn: "Cluster",
      pluralGroup: "clusters",
      emptyReturn:
        "No cluster data is available. Clustering may not have run for this execution.",
      emptyAnalise:
        "Cluster analysis depends on the groups produced during the run.",
    };
  }
  return {
    returnTitle: "Return by cohort",
    returnSubtitle: "Breakdown by reference period",
    compositionTitle: "Composition by cohort",
    analysisTitle: "Cohort analysis",
    groupColumn: "Cohort",
    pluralGroup: "cohorts",
    emptyReturn:
      "No cohort data is available. The cohort_reference field may be absent from the input file.",
    emptyAnalise:
      "Cohort analysis requires the cohort_reference field in the input file.",
  };
}

function kpiDeltaHtml(
  current: number,
  other: number | undefined,
  format: (v: number) => string,
): { className: string; label: string } | null {
  if (other === undefined || other === current) return null;
  const diff = current - other;
  if (diff === 0) return null;
  const pct = other !== 0 ? Math.abs((diff / other) * 100).toFixed(1) : null;
  const sign = diff > 0 ? "+" : "−";
  const arrow = diff > 0 ? "↑" : "↓";
  const cls = diff > 0 ? "positive" : "negative";
  const absLabel = format(Math.abs(diff));
  const label = pct
    ? `${arrow} ${sign}${absLabel} (${sign}${pct}%)`
    : `${arrow} ${sign}${absLabel}`;
  return { className: cls, label };
}

export default function AnalyticsPage() {
  const [history, setHistory] = useState<ExecutionHistoryItemSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<RunComparisonSnapshotSchema | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  const [compareSlots, setCompareSlots] = useState<[number | null, number | null]>([null, null]);
  const [compareActive, setCompareActive] = useState(false);
  const [compareSnapshots, setCompareSnapshots] = useState<
    [RunComparisonSnapshotSchema | null, RunComparisonSnapshotSchema | null]
  >([null, null]);
  const [compareLoading, setCompareLoading] = useState(false);

  const [popupOpen, setPopupOpen] = useState(false);
  const [histSlot, setHistSlot] = useState<0 | 1 | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const compareBtnRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const histRef = useRef<HTMLDivElement>(null);
  const comparisonRequestRef = useRef(0);


  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getExecutionHistory({ status: "success", page: 1, page_size: 50 })
      .then((hist) => {
        if (!active) return;
        setHistory(hist.items);
        if (hist.items.length > 0) {
          setActiveRunId(hist.items[0].run_id);
          setCompareSlots([hist.items[0].run_id, null]);
        } else {
          setActiveRunId(null);
        }
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(
          err instanceof ApiResponseError
            ? err.message
            : "Failed to load analytics.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // ── Active run snapshot (standard mode) ──
  useEffect(() => {
    if (compareActive || activeRunId === null) return;
    let cancelled = false;
    setSnapshot(null);
    setSnapshotLoading(true);
    getRunSnapshot(activeRunId)
      .then((data) => {
        if (!cancelled && data.run_id === activeRunId) setSnapshot(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSnapshot(null);
          setError(
            err instanceof ApiResponseError
              ? err.message
              : "Failed to load run metrics.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setSnapshotLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeRunId, compareActive]);

  const positionPanel = useCallback((anchor: HTMLElement, panel: HTMLElement) => {
    const rect = anchor.getBoundingClientRect();
    panel.style.top = `${rect.bottom + 8}px`;
    panel.style.right = `${window.innerWidth - rect.right}px`;
  }, []);

  useEffect(() => {
    if (!popupOpen || !compareBtnRef.current || !popupRef.current) return;
    positionPanel(compareBtnRef.current, popupRef.current);
  }, [popupOpen, positionPanel]);

  useEffect(() => {
    if (histSlot === null || !compareBtnRef.current || !histRef.current) return;
    positionPanel(compareBtnRef.current, histRef.current);
  }, [histSlot, positionPanel]);

  const closeAll = useCallback(() => {
    setPopupOpen(false);
    setHistSlot(null);
  }, []);

  const applyComparison = useCallback(async () => {
    const [a, b] = compareSlots;
    if (!a) return;
    closeAll();

    if (!b) {
      setCompareActive(false);
      setCompareSnapshots([null, null]);
      setActiveRunId(a);
      return;
    }

    const requestId = ++comparisonRequestRef.current;
    setCompareSnapshots([null, null]);
    setCompareLoading(true);
    setCompareActive(true);
    try {
      const data = await compareRuns(a, b);
      if (comparisonRequestRef.current !== requestId) return;
      setCompareSnapshots([data.reference, data.compared]);
    } catch (err) {
      if (comparisonRequestRef.current !== requestId) return;
      setCompareActive(false);
      setCompareSnapshots([null, null]);
      alert(err instanceof ApiResponseError ? err.message : "Failed to compare runs.");
    } finally {
      if (comparisonRequestRef.current === requestId) {
        setCompareLoading(false);
      }
    }
  }, [compareSlots, closeAll]);

  const exportPdf = useCallback(async () => {
    setPdfLoading(true);
    try {
      const [a, b] = compareSlots;
      if (compareActive && a !== null && b !== null) {
        await downloadComparisonPdf(a, b);
        return;
      }
      if (activeRunId === null) return;
      await downloadReportPdf({ run_id: activeRunId });
    } catch (err) {
      alert(err instanceof ApiResponseError ? err.message : "Failed to export the PDF.");
    } finally {
      setPdfLoading(false);
    }
  }, [activeRunId, compareActive, compareSlots]);

  const hasData = history.length > 0;
  const isComparing = compareActive && compareSnapshots[0] && compareSnapshots[1];
  const subtitle = snapshot
    ? `${formatRunId(snapshot.run_id)} · ${formatDateTime(snapshot.created_at)}`
    : activeRunId
      ? formatRunId(activeRunId)
      : "No run is available";

  if (loading) {
    return (
      <div className="screen active">
        <div className="breadcrumb">
          Home › <span>Analytics</span>
        </div>
        <h1 className="page-title">Analytics</h1>
        <div className="empty-state">
          <div className="empty-title">Loading analytics...</div>
        </div>
      </div>
    );
  }

  if (error && !hasData) {
    return (
      <div className="screen active">
        <div className="breadcrumb">
          Home › <span>Analytics</span>
        </div>
        <h1 className="page-title">Analytics</h1>
        <div className="empty-state">
          <div className="empty-title">Analytics could not be loaded</div>
          <div className="empty-sub">{error}</div>
        </div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="screen active">
        <div className="stats-header">
          <div>
            <div className="breadcrumb">
              Home › <span>Analytics</span>
            </div>
            <h1 className="page-title" style={{ marginBottom: 2 }}>
              Analytics
            </h1>
            <div className="stats-subtitle">No run is available</div>
          </div>
        </div>
        <div className="stats-empty-state">
          <div className="stats-empty-icon">
            <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
              <path d="M4 19V5" />
              <path d="M4 19h16" />
              <path d="M8 16v-5" />
              <path d="M12 16V8" />
              <path d="M16 16v-3" />
            </svg>
          </div>
          <div className="stats-empty-title">No analytics to display</div>
          <div className="stats-empty-sub">
            Run the algorithm from the home page to generate this view's indicators.
          </div>
          <Link href="/" className="btn-primary stats-empty-action">
            Ir para homepage
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="screen active">
      <div className="stats-header">
        <div>
          <div className="breadcrumb">
            Home › <span>Analytics</span>
          </div>
          <h1 className="page-title" style={{ marginBottom: 2 }}>
            Analytics
          </h1>
          <div className="stats-subtitle">{subtitle}</div>
        </div>
        <div className="stats-header-actions">
          <button
            ref={compareBtnRef}
            type="button"
            className={`btn-comparison${popupOpen || isComparing ? " active" : ""}${
              isComparing ? " comparing" : ""
            }`}
            onClick={() => setPopupOpen((v) => !v)}
          >
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M18 20V10M12 20V4M6 20v-6" />
            </svg>
            Comparison mode
          </button>
          <button
            type="button"
            className="btn-export"
            disabled={
              pdfLoading ||
              (compareActive
                ? compareSlots[0] === null || compareSlots[1] === null
                : activeRunId === null)
            }
            onClick={exportPdf}
          >
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            {pdfLoading
              ? "Exportando..."
              : isComparing
                ? "Export comparison"
                : "Export report"}
          </button>
        </div>
      </div>

      {error && <div className="inline-error">{error}</div>}

      {}
      <div
        className={`comp-overlay${popupOpen || histSlot !== null ? " active" : ""}`}
        onClick={closeAll}
      />
      <div ref={popupRef} className={`comp-popup${popupOpen ? " open" : ""}`}>
        <div className="comp-popup-title">Selected runs</div>
        <div className="comp-slots">
          {compareSlots.map((runId, idx) => {
            const run = runId ? history.find((h) => h.run_id === runId) : null;
            return (
              <div
                key={idx}
                className={`comp-slot${run ? " filled" : " empty"}`}
                onClick={() => setHistSlot(idx as 0 | 1)}
              >
                <div className="comp-slot-index">{idx === 0 ? "A" : "B"}</div>
                <div className="comp-slot-info">
                  <div className="comp-slot-name">
                    {run ? `${formatRunId(run.run_id)} · ${run.file_name}` : "None selected"}
                  </div>
                  <div className="comp-slot-hint">
                    {run ? "Click to change" : "Click to select"}
                  </div>
                </div>
                {run && (
                  <button
                    type="button"
                    className="comp-slot-clear"
                    onClick={(e) => {
                      e.stopPropagation();
                      setCompareSlots((prev) => {
                        const next: [number | null, number | null] = [...prev];
                        next[idx] = null;
                        return next;
                      });
                    }}
                  >
                    <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                )}
              </div>
            );
          })}
        </div>
        <div className="comp-popup-footer">
          <button type="button" className="btn-secondary" style={{ fontSize: 12, padding: "7px 14px" }} onClick={closeAll}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            style={{ fontSize: 12, padding: "7px 14px" }}
            disabled={!compareSlots[0] || compareLoading}
            onClick={applyComparison}
          >
            {compareLoading ? "Carregando..." : "Apply comparison"}
          </button>
        </div>
      </div>

      {}
      <div ref={histRef} className={`hist-panel${histSlot !== null ? " open" : ""}`}>
        <div className="hist-panel-header">
          <div className="hist-panel-title">
            Select for run {histSlot === 0 ? "A" : "B"}
          </div>
          <button type="button" className="hist-close-btn" onClick={() => setHistSlot(null)}>
            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="hist-list">
          {history.map((h, idx) => {
            const selected = histSlot !== null && compareSlots[histSlot] === h.run_id;
            const usedByOther =
              histSlot !== null && compareSlots[1 - histSlot] === h.run_id;
            return (
              <div
                key={h.run_id}
                className={`hist-item${selected ? " selected" : ""}${usedByOther ? " used" : ""}`}
                onClick={() => {
                  if (usedByOther || histSlot === null) return;
                  setCompareSlots((prev) => {
                    const next: [number | null, number | null] = [...prev];
                    next[histSlot] = h.run_id;
                    return next;
                  });
                  setHistSlot(null);
                }}
              >
                <div style={{ flex: 1 }}>
                  <div className="hist-item-label">
                    {formatRunId(h.run_id)} — {formatDateTime(h.created_at)}
                  </div>
                  {idx === 0 && history[0].run_id === h.run_id && (
                    <span className="hist-item-tag">Mais recente</span>
                  )}
                </div>
                {selected && (
                  <svg width="16" height="16" fill="none" stroke="var(--accent)" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                )}
                {usedByOther && <span className="hist-item-used">Em use</span>}
              </div>
            );
          })}
        </div>
      </div>

      {}
      {compareLoading && (
        <div className="empty-state" style={{ minHeight: 200 }}>
          <div className="empty-title">Loading comparison...</div>
        </div>
      )}

      {!compareLoading && isComparing && compareSnapshots[0] && compareSnapshots[1] && (
        <div className="comp-columns">
          <StatsColumn
            key={compareSnapshots[0].run_id}
            snapshot={compareSnapshots[0]}
            colLabel="A"
            other={compareSnapshots[1]}
            compact
          />
          <div className="comp-divider" />
          <StatsColumn
            key={compareSnapshots[1].run_id}
            snapshot={compareSnapshots[1]}
            colLabel="B"
            other={compareSnapshots[0]}
            compact
          />
        </div>
      )}

      {!compareLoading && !compareActive && (
        <>
          {snapshotLoading && (
            <div className="empty-state" style={{ minHeight: 200 }}>
              <div className="empty-title">Loading metrics...</div>
            </div>
          )}
          {!snapshotLoading && snapshot && snapshot.run_id === activeRunId && (
            <StatsColumn key={snapshot.run_id} snapshot={snapshot} />
          )}
        </>
      )}
    </div>
  );
}

interface StatsColumnProps {
  snapshot: RunComparisonSnapshotSchema;
  colLabel?: string;
  other?: RunComparisonSnapshotSchema;
  compact?: boolean;
}

function StatsColumn({ snapshot, colLabel, other, compact }: StatsColumnProps) {
  const m = snapshot.metrics;
  const agrupamento = snapshot.return_grouping ?? "cohort";
  const copy = agrupamentoCopy(agrupamento);

  const kpis: Array<{
    label: string;
    key: "total_limit" | "financial_default_rate" | "approval_rate";
    value: string;
    raw: number;
    format: (v: number) => string;
  }> = [
    {
      label: "Limit total sugerido",
      key: "total_limit",
      value: formatBRL(m.total_limit),
      raw: m.total_limit,
      format: formatBRL,
    },
    {
      label: "Financial default rate",
      key: "financial_default_rate",
      value: formatPct(m.financial_default_rate, 2),
      raw: m.financial_default_rate,
      format: (v: number) => formatPct(v, 2),
    },
    {
      label: "Approval percentage",
      key: "approval_rate",
      value: formatPct(m.approval_rate, 0),
      raw: m.approval_rate,
      format: (v: number) => formatPct(v, 0),
    },
  ];

  const totalReturn = m.total_return;
  const cohortRows = snapshot.return_by_cohort;
  const cohortTotalClients = cohortRows.reduce((acc, r) => acc + (r.total_clients ?? 0), 0);
  const cohortTotalReturn = cohortRows.reduce((acc, r) => acc + r.total_return, 0);

  return (
    <div className="comp-col">
      {colLabel && (
        <div className="comp-col-header">
          <span className="comp-col-badge">{colLabel}</span>
          <span className="comp-col-label">
            {formatRunId(snapshot.run_id)} · {snapshot.file_name}
          </span>
        </div>
      )}

      <div className={`kpi-grid${compact ? " kpi-grid-comp" : ""}`}>
        {kpis.map((kpi) => {
          const delta =
            other && kpiDeltaHtml(kpi.raw, other.metrics[kpi.key], kpi.format);
          return (
            <div key={kpi.label} className="kpi-card">
              <div className="kpi-label">{kpi.label}</div>
              <div className="kpi-value">{kpi.value}</div>
              {delta && <div className={`kpi-comp-delta ${delta.className}`}>{delta.label}</div>}
            </div>
          );
        })}
      </div>

      <div className={`charts-row${compact ? " charts-row-comp" : ""}`}>
        <div className="chart-card return-card">
          <div className="return-label">Total expected portfolio return (12m)</div>
          <div className={`return-value${compact ? " return-value-comp" : ""}`}>
            {formatBRLFull(totalReturn)}
          </div>
          {cohortRows.length > 0 ? (
            <div>
              <div className="return-breakdown-title">{copy.compositionTitle}</div>
              <div className="return-bars">
                {cohortRows.map((bar) => (
                  <div key={bar.cohort_reference} className="return-bar-row">
                    <span className="return-bar-label">{bar.cohort_reference}</span>
                    <div className="return-bar-track">
                      <div
                        className="return-bar-fill"
                        style={{ width: `${Math.min(100, bar.percentage)}%` }}
                      />
                    </div>
                    <span className="return-bar-val">{formatBRL(bar.total_return)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.55)" }}>
              {copy.emptyReturn}
            </div>
          )}
        </div>

        <div className="chart-card">
          <div className="chart-title">Suggested-limit distribution</div>
          <div className="chart-subtitle">by value range (R$)</div>
          {snapshot.limit_ranges.length > 0 ? (
            <LimitsDistributionSketch buckets={snapshot.limit_ranges} />
          ) : (
            <div className="empty-sub" style={{ marginTop: 16 }}>
              No limit range is available.
            </div>
          )}
        </div>
      </div>

      {}
      <div className="logs-card">
        <div className="logs-header">
          <div className="chart-title">{copy.returnTitle}</div>
          <div className="chart-subtitle">{copy.returnSubtitle}</div>
        </div>
        {cohortRows.length > 0 ? (
          <table className="logs-table">
            <thead>
              <tr>
                <th>{copy.groupColumn}</th>
                <th>Clients</th>
                <th>Return total</th>
                <th>Share</th>
              </tr>
            </thead>
            <tbody>
              {cohortRows.map((row) => (
                <tr key={row.cohort_reference} className="log-row">
                  <td className="log-cohort">{row.cohort_reference}</td>
                  <td className="log-num">{(row.total_clients ?? 0).toLocaleString("en-US")}</td>
                  <td className="log-num">{formatBRLFull(row.total_return)}</td>
                  <td className="log-num">{row.percentage.toFixed(1)}%</td>
                </tr>
              ))}
              <tr className="log-row logs-total-row">
                <td className="log-cohort">Total</td>
                <td className="log-num">{cohortTotalClients.toLocaleString("en-US")}</td>
                <td className="log-num">{formatBRLFull(cohortTotalReturn)}</td>
                <td className="log-num">100%</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <div className="empty-sub">{copy.emptyReturn}</div>
        )}
      </div>

      <div className="logs-card">
        <div className="logs-header">
          <div className="chart-title">{copy.analysisTitle}</div>
          <div className="chart-subtitle">
            {snapshot.cohort_analysis.length > 0
              ? `${Array.from(new Set(snapshot.cohort_analysis.map((r) => r.cohort))).length} ${copy.pluralGroup} processed in this run`
              : "Data is unavailable for this run"}
          </div>
        </div>
        {snapshot.cohort_analysis.length > 0 ? (
          <>
            <table className="logs-table">
              <thead>
                <tr>
                  <th>{copy.groupColumn}</th>
                  <th>Client count</th>
                  <th>Average payment capacity</th>
                  <th>Average limit</th>
                  <th>Variation</th>
                  <th>Approval rate</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.cohort_analysis.map((row) => {
                  const variacao = limitVariation(row.average_capacity, row.average_limit);
                  return (
                    <tr key={row.cohort} className="log-row">
                      <td className="log-cohort">{row.cohort}</td>
                      <td className="log-num">{row.client_count.toLocaleString("en-US")}</td>
                      <td className="log-num">{formatBRL(row.average_capacity)}</td>
                      <td className="log-num">{formatBRL(row.average_limit)}</td>
                      <td className={`log-num ${variacao.positive ? "delta-pos" : "delta-neg"}`}>
                        {variacao.label}
                      </td>
                      <td className="log-num">{formatPct(row.approval_rate, 0)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="logs-footer">
              <p className="logs-note">
                * Clients without history, with zero limits, below the configured policy, or under
                recovery were excluded from the analysis.
              </p>
            </div>
          </>
        ) : (
          <div className="empty-sub">{copy.emptyAnalise}</div>
        )}
      </div>
    </div>
  );
}
