




import type { RunStatusFinal } from "./types";







export function formatBRL(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  if (Math.abs(val) >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(1)}M`;
  if (Math.abs(val) >= 1_000) return `R$ ${(val / 1_000).toFixed(0)}K`;
  return val.toLocaleString("en-US", { style: "currency", currency: "BRL" });
}







export function formatBRLFull(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return val.toLocaleString("en-US", { style: "currency", currency: "BRL" });
}








export function formatPct(val: number | null | undefined, decimals = 1): string {
  if (val === null || val === undefined || Number.isNaN(val)) return "—";
  return `${(val * 100).toFixed(decimals)}%`;
}







export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "—";
  return (
    dt.toLocaleDateString("en-US", { day: "2-digit", month: "2-digit", year: "numeric" }) +
    " às " +
    dt.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  );
}







export function formatDuracao(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  const total = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}m ${String(s).padStart(2, "0")}s`;
}







export function daysFromNow(iso: string): number {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return Number.POSITIVE_INFINITY;
  return Math.floor((Date.now() - dt.getTime()) / (1000 * 60 * 60 * 24));
}







export function formatRunId(id: number): string {
  return `RUN-${String(id).padStart(4, "0")}`;
}







export function formatAlgorithm(value: string | null | undefined): string {
  if (!value) return "—";
  const normalized = value.toLowerCase();
  if (normalized === "branch_bound") return "Branch and Bound";
  if (normalized === "simplex") return "Simplex";
  if (normalized === "simplex_ortools") return "Simplex OR-Tools";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export const STATUS_LABEL: Record<RunStatusFinal, string> = {
  success: "Completed",
  error: "With error",
  timeout: "Timeout",
  pending: "Pending",
};

export const STATUS_BADGE_CLASS: Record<RunStatusFinal, string> = {
  success: "run-badge-ok",
  error: "run-badge-error",
  timeout: "run-badge-error",
  pending: "run-badge-warn",
};

export interface ScoreCategory {
  label: string;
  className: string;
}







export function classifyScore(score: number | null | undefined): ScoreCategory {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return { label: "—", className: "badge-bom" };
  }
  if (score >= 700) return { label: "Excelente", className: "badge-excelente" };
  if (score >= 500) return { label: "Bom", className: "badge-bom" };
  return { label: "Regular", className: "badge-regular" };
}

export type LimitCategory = "full" | "above" | "denied";








export function classifyLimit(
  limit: number | null | undefined,
  capacity: number | null | undefined,
): LimitCategory {
  if (limit === null || limit === undefined || limit <= 0) return "denied";
  if (capacity && limit > capacity) return "above";
  return "full";
}

export const LIMIT_BADGE_LABEL: Record<LimitCategory, string> = {
  full: "Integral",
  above: "Acima da capacity",
  denied: "Negado",
};

export const LIMIT_BADGE_CLASS: Record<LimitCategory, string> = {
  full: "lb-full",
  above: "lb-above",
  denied: "lb-parcial",
};

const AVATAR_COLORS = ["#0d1f3c", "#162a4a", "#1a3354", "#254a78", "#1e3a5f"];







export function avatarColorFor(token: string): string {
  let sum = 0;
  for (let i = 0; i < token.length; i++) sum += token.charCodeAt(i);
  return AVATAR_COLORS[sum % AVATAR_COLORS.length];
}







export function tokenInitials(token: string): string {
  const trimmed = token.replace(/[^A-Za-z0-9]/g, "");
  return (trimmed.slice(-3) || token.slice(-3) || "—").toUpperCase();
}

export const ETAPA_LABEL: Record<string, string> = {
  waiting_for_processing: "Waiting processamento",
  ingestion: "Loading application data",
  calculating_constraints: "Applying parameters configured",
  tableau_calculation: "Calculating optimization matrix",
  generating_recommendations: "Generating limit recommendations",
  validating_constraints: "Validating business constraints",
  completed: "Completed",
  failed: "Failed",
};

const ETAPAS_ORDEM = [
  "ingestion",
  "calculating_constraints",
  "tableau_calculation",
  "generating_recommendations",
  "validating_constraints",
] as const;

export const ETAPAS_FLUXO = ETAPAS_ORDEM;







export function etapaProgress(state: string | null | undefined): {
  index: number;
  pct: number;
} {
  if (!state) return { index: -1, pct: 0 };
  if (state === "completed") return { index: ETAPAS_ORDEM.length, pct: 100 };
  if (state === "failed") return { index: -1, pct: 100 };
  const idx = ETAPAS_ORDEM.indexOf(state as (typeof ETAPAS_ORDEM)[number]);
  if (idx < 0) return { index: 0, pct: 8 };
  const total = ETAPAS_ORDEM.length;
  return {
    index: idx,
    pct: Math.min(99, Math.round(((idx + 0.5) / total) * 100)),
  };
}
