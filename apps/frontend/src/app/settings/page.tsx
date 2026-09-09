"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type ReactNode,
} from "react";

import { getActiveParameters, updateParameters } from "@/lib/api";
import { ApiResponseError, type Multiplier, type ParametersSchema } from "@/lib/types";

type ConfigTab = "pre" | "definition" | "pos";

interface MultiplierRow {
  min_pd: number;
  max_pd: number;
  multiplier: number;
}

interface ConfigFormState {
  utilization_rate: number;
  lgd: number;
  min_pd: number;
  max_pd: number;
  constraint_flag_1: boolean;
  interchange: number;
  enabled: boolean;
  min_clusters: number;
  max_clients_per_cluster: number;
  n_clusters: number | null;
  max_limit: number;
  baseline_default_rate: number;
  min_limit: number;
  max_rejected_limit: number;
  discretize: boolean;
  multipliers: MultiplierRow[];
}

const TAB_LABELS: Record<ConfigTab, string> = {
  pre: "Pre-analysis",
  definition: "Limit definition",
  pos: "Post-analysis",
};

const TAB_FIELDS: Record<ConfigTab, (keyof ConfigFormState)[]> = {
  pre: [
    "utilization_rate",
    "lgd",
    "max_pd",
    "interchange",
    "constraint_flag_1",
    "enabled",
    "min_clusters",
    "max_clients_per_cluster",
    "multipliers",
  ],
  definition: ["max_limit", "baseline_default_rate"],
  pos: ["min_limit", "discretize", "max_rejected_limit"],
};

const INTERPRETATION_BADGES = [
  "badge-minimum",
  "badge-baixo",
  "badge-moderado",
  "badge-alto",
  "badge-muito-alto",
] as const;

const INTERPRETATION_LABELS = [
  "Minimum",
  "Baixo",
  "Moderado",
  "Alto",
  "Muito alto",
] as const;

function parseNumeric(value: string): number {
  return parseFloat(value.replace(",", ".").trim()) || 0;
}

function formatPdDisplay(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

function parseMultipliers(raw: Multiplier[]): MultiplierRow[] {
  return raw.map((item) => ({
    min_pd: Number(item.min_pd),
    max_pd: Number(item.max_pd),
    multiplier: Number(item.multiplier),
  }));
}

function serializeMultipliers(rows: MultiplierRow[]): Multiplier[] {
  return rows.map((row) => ({
    min_pd: String(row.min_pd),
    max_pd: String(row.max_pd),
    multiplier: String(row.multiplier),
  }));
}

function paramsToForm(params: ParametersSchema): ConfigFormState {
  return {
    utilization_rate: params.utilization_rate,
    lgd: params.lgd,
    min_pd: params.min_pd,
    max_pd: params.max_pd,
    constraint_flag_1: params.filter,
    interchange: params.interchange,
    enabled: params.enabled,
    min_clusters: params.min_clusters,
    max_clients_per_cluster: params.max_clients_per_cluster,
    n_clusters: params.n_clusters,
    max_limit: params.max_limit,
    baseline_default_rate: params.baseline_default_rate,
    min_limit: params.min_limit,
    max_rejected_limit: params.max_rejected_limit,
    discretize: params.discretize,
    multipliers: parseMultipliers(params.multipliers),
  };
}

function multipliersEqual(a: MultiplierRow[], b: MultiplierRow[]): boolean {
  if (a.length !== b.length) return false;
  return a.every(
    (row, idx) =>
      row.min_pd === b[idx].min_pd &&
      row.max_pd === b[idx].max_pd &&
      row.multiplier === b[idx].multiplier,
  );
}

function fieldsEqual(
  a: ConfigFormState,
  b: ConfigFormState,
  fields: (keyof ConfigFormState)[],
): boolean {
  return fields.every((key) => {
    const av = a[key];
    const bv = b[key];
    if (key === "multipliers") {
      return multipliersEqual(
        av as MultiplierRow[],
        bv as MultiplierRow[],
      );
    }
    return av === bv;
  });
}

function validateForm(form: ConfigFormState): string | null {
  if (!(form.utilization_rate > 0 && form.utilization_rate <= 1)) {
    return "Utilization rate must be between 0% and 100%, excluding 0%.";
  }
  if (!(form.lgd > 0 && form.lgd <= 1)) {
    return "LGD must be between 0% and 100%, excluding 0%.";
  }
  if (
    !(
      form.baseline_default_rate > 0 &&
      form.baseline_default_rate < 1
    )
  ) {
    return "The default-rate baseline must be between 0% and 100%, excluding the endpoints.";
  }
  if (form.min_pd >= form.max_pd) {
    return "Minimum PD must be lower than maximum PD.";
  }
  if (form.max_rejected_limit < 200) {
    return "The rejected limit cannot be lower than R$ 200.";
  }
  if (form.max_clients_per_cluster <= 0) {
    return "Maximum clients per cluster must be greater than zero.";
  }
  if (form.min_clusters < 100) {
    return "Minimum cluster count must be at least 100.";
  }
  return null;
}

function formatSaveError(err: unknown): string {
  if (!(err instanceof ApiResponseError)) {
    return "Failed to save settings.";
  }
  if (err.code === "MISSING_REQUIRED_PARAMETERS") {
    const missing = err.details.missing;
    if (Array.isArray(missing) && missing.length > 0) {
      return `Missing required fields: ${missing.join(", ")}`;
    }
    return err.message;
  }
  return err.message;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<ConfigTab>("pre");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [paramId, setParamId] = useState<number | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const [initial, setInitial] = useState<ConfigFormState | null>(null);
  const [form, setForm] = useState<ConfigFormState | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [editingMultipliers, setEditingMultipliers] = useState(false);
  const multCardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(null);
    getActiveParameters()
      .then((data) => {
        if (!active) return;
        const next = paramsToForm(data);
        setInitial(next);
        setForm(next);
        setParamId(data.id);
        setUpdatedAt(data.created_at);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setInitial(null);
        setForm(null);
        setLoadError(
          err instanceof ApiResponseError
            ? err.message
            : "Failed to load active parameters.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!editingMultipliers) return;
    function onClick(event: MouseEvent) {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      if (multCardRef.current?.contains(target)) return;
      if (target.closest(".btn-edit-small")) return;
      setEditingMultipliers(false);
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [editingMultipliers]);

  const modifiedTabs = useMemo(() => {
    if (!initial || !form) return new Set<ConfigTab>();
    const modified = new Set<ConfigTab>();
    (Object.keys(TAB_FIELDS) as ConfigTab[]).forEach((tab) => {
      if (!fieldsEqual(form, initial, TAB_FIELDS[tab])) modified.add(tab);
    });
    return modified;
  }, [form, initial]);

  const patchForm = useCallback((patch: Partial<ConfigFormState>) => {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));
    setSaveError(null);
    setSaveSuccess(false);
  }, []);

  const resetTab = useCallback(
    (tab: ConfigTab) => {
      if (!initial || !form) return;
      const fields = TAB_FIELDS[tab];
      const patch: Partial<ConfigFormState> = {};
      fields.forEach((key) => {
        (patch as Record<string, unknown>)[key] = initial[key];
      });
      patchForm(patch);
    },
    [form, initial, patchForm],
  );

  const resetAll = useCallback(() => {
    if (!initial) return;
    setForm({ ...initial, multipliers: initial.multipliers.map((r) => ({ ...r })) });
    setSaveError(null);
    setSaveSuccess(false);
    setEditingMultipliers(false);
  }, [initial]);

  const handleResetCurrent = useCallback(() => {
    const label = TAB_LABELS[activeTab];
    if (!confirm(`Reset the settings for "${label}" to their saved values?`)) {
      return;
    }
    resetTab(activeTab);
  }, [activeTab, resetTab]);

  const handleResetAll = useCallback(() => {
    if (!confirm("Reset ALL settings to their saved values?")) return;
    resetAll();
  }, [resetAll]);

  const handleSave = useCallback(async () => {
    if (!form) return;
    const validationError = validateForm(form);
    if (validationError) {
      setSaveError(validationError);
      return;
    }

    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const saved = await updateParameters({
        utilization_rate: form.utilization_rate,
        lgd: form.lgd,
        min_pd: form.min_pd,
        max_pd: form.max_pd,
        filter: form.constraint_flag_1,
        interchange: form.interchange,
        enabled: form.enabled,
        min_clusters: form.min_clusters,
        max_clients_per_cluster: form.max_clients_per_cluster,
        n_clusters: form.n_clusters,
        max_limit: form.max_limit,
        baseline_default_rate: form.baseline_default_rate,
        min_limit: form.min_limit,
        max_rejected_limit: form.max_rejected_limit,
        discretize: form.discretize,
        multipliers: serializeMultipliers(form.multipliers),
      });
      const next = paramsToForm(saved);
      setInitial(next);
      setForm(next);
      setParamId(saved.id);
      setUpdatedAt(saved.created_at);
      setSaveSuccess(true);
      setEditingMultipliers(false);
      setTimeout(() => setSaveSuccess(false), 1800);
    } catch (err) {
      setSaveError(formatSaveError(err));
    } finally {
      setSaving(false);
    }
  }, [form]);

  if (loading) {
    return (
      <div className="screen active">
        <div className="breadcrumb">
          Settings › <span>{TAB_LABELS.pre}</span>
        </div>
        <h1 className="page-title">Settings</h1>
        <div className="empty-state">
          <div className="empty-title">Loading parameters...</div>
        </div>
      </div>
    );
  }

  if (loadError || !form || !initial) {
    return (
      <div className="screen active">
        <div className="breadcrumb">
          Settings › <span>—</span>
        </div>
        <h1 className="page-title">Settings</h1>
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="empty-title">Settings could not be loaded</div>
          <div className="empty-sub">{loadError}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="screen active">
      <div className="breadcrumb">
        Settings › <span>{TAB_LABELS[activeTab]}</span>
      </div>
      <h1 className="page-title">Settings</h1>

      {paramId !== null && (
        <div className="config-meta">
          Active version #{paramId}
          {updatedAt ? ` · updated on ${new Date(updatedAt).toLocaleString("en-US")}` : ""}
        </div>
      )}

      <div className="config-tabs">
        {(Object.keys(TAB_LABELS) as ConfigTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            className={`config-tab${activeTab === tab ? " active" : ""}${
              modifiedTabs.has(tab) ? " modified" : ""
            }`}
            onClick={() => setActiveTab(tab)}
          >
            <span className="tab-modified" />
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {saveError && <div className="inline-error">{saveError}</div>}

      {}
      <div className={`config-panel${activeTab === "pre" ? " active" : ""}`}>
        <div className="config-info-bar">
          <span>
            The following parameters are applied before limit assignment and may cause
            some clients to receive no allocated limit.
          </span>
          <button type="button" className="help-btn" title="Ajuda">
            ?
          </button>
        </div>

        <div className="param-grid-top">
          <PercentSliderCard
            title="Rate de use expected"
            description="The utilization rate estimates how much of an accepted limit a client will use."
            min={0}
            max={100}
            step={1}
            valuePct={form.utilization_rate * 100}
            onChange={(pct) => patchForm({ utilization_rate: pct / 100 })}
          />
          <PercentSliderCard
            title="Loss Given Default"
            description="Loss Given Default is the share of exposure lost when clients default."
            min={0}
            max={100}
            step={1}
            valuePct={form.lgd * 100}
            onChange={(pct) => patchForm({ lgd: pct / 100 })}
          />
          <PercentSliderCard
            title="Maximum accepted probability of default"
            description="The estimated likelihood that a client defaults. Clients above this threshold are excluded."
            min={0}
            max={100}
            step={1}
            valuePct={form.max_pd * 100}
            onChange={(pct) => patchForm({ max_pd: pct / 100 })}
          />
        </div>

        <div className="param-grid-bottom">
          <div className="param-grid-bottom-left">
            <PercentSliderCard
              title="Interchange"
              description="The interchange percentage applied to client transactions."
              min={0}
              max={10}
              step={0.1}
              decimals={2}
              valuePct={form.interchange * 100}
              onChange={(pct) => patchForm({ interchange: pct / 100 })}
            />

            <div className="param-card">
              <div className="param-card-title" style={{ marginBottom: 14 }}>
                Client constraints
              </div>
              <ToggleRow
                checked={form.constraint_flag_1}
                onChange={(checked) => patchForm({ constraint_flag_1: checked })}
                title="Desconsiderar clients constrained"
                subtitle="by business rules"
              />
            </div>

            <div className="param-card">
              <div className="param-card-title">Client clustering</div>
              <div className="param-card-desc">
                Groups similar clients before optimization to reduce analysis
                granularity.
              </div>
              <ToggleRow
                checked={form.enabled}
                onChange={(checked) =>
                  patchForm({
                    enabled: checked,
                    n_clusters: checked ? form.n_clusters : null,
                  })
                }
                title="Clustering enabled"
                subtitle="yes/no"
              />
              <div className="cluster-fields">
                <label className="number-field">
                  <span>Minimum number of clusters</span>
                  <input
                    type="number"
                    min={100}
                    step={1}
                    value={form.min_clusters}
                    disabled={!form.enabled}
                    onChange={(e) => {
                      const value = parseInt(e.target.value, 10);
                      patchForm({ min_clusters: Number.isNaN(value) ? 100 : Math.max(100, value) });
                    }}
                  />
                </label>
                <label className="number-field">
                  <span>Maximum clients per cluster</span>
                  <input
                    type="number"
                    min={1}
                    step={1}
                    value={form.max_clients_per_cluster}
                    disabled={!form.enabled}
                    onChange={(e) => {
                      const value = parseInt(e.target.value, 10);
                      patchForm({
                        max_clients_per_cluster: Number.isNaN(value) ? 1 : Math.max(1, value),
                      });
                    }}
                  />
                </label>
              </div>
            </div>
          </div>

          <MultiplierTable
            ref={multCardRef}
            rows={form.multipliers}
            editing={editingMultipliers}
            onToggleEdit={() => setEditingMultipliers((v) => !v)}
            onChange={(rows) => patchForm({ multipliers: rows })}
          />
        </div>
      </div>

      {}
      <div className={`config-panel${activeTab === "definition" ? " active" : ""}`}>
        <div className="config-info-bar">
          <span>
            The following parameters are applied by the limit-assignment model and are
            directly responsible for individual client limits and the portfolio's
            default probability.
          </span>
          <button type="button" className="help-btn" title="Ajuda">
            ?
          </button>
        </div>

        <div className="config-grid-2">
          <div className="param-card">
            <div className="param-card-title">Maximum limit</div>
            <div className="param-card-desc">
              The maximum limit caps the credit offered to any individual client.
            </div>
            <CurrencyInput
              value={form.max_limit}
              onChange={(value) => patchForm({ max_limit: value })}
            />
          </div>

          <PercentSliderCard
            title="Maximum financial default-rate baseline"
            description="The financial default-rate baseline caps portfolio default exposure using estimated default probabilities."
            min={0}
            max={100}
            step={0.01}
            decimals={2}
            valuePct={form.baseline_default_rate * 100}
            onChange={(pct) => patchForm({ baseline_default_rate: pct / 100 })}
          />
        </div>
      </div>

      {}
      <div className={`config-panel${activeTab === "pos" ? " active" : ""}`}>
        <div className="config-info-bar">
          <span>
            The following parameters are applied after limit assignment and may cause
            some clients to receive no limit or have their recommendation adjusted.
          </span>
          <button type="button" className="help-btn" title="Ajuda">
            ?
          </button>
        </div>

        <div className="config-grid-2">
          <div className="param-card">
            <div className="param-card-title">Minimum limit</div>
            <CurrencyInput
              value={form.min_limit}
              onChange={(value) => patchForm({ min_limit: value })}
              style={{ marginTop: 16 }}
            />
          </div>

          <div className="param-card">
            <div className="param-card-title">Rejected limit (approval floor)</div>
            <div className="param-card-desc">
              Minimum approved amount when the configured minimum limit is zero (at least R$ 200).
            </div>
            <CurrencyInput
              value={form.max_rejected_limit}
              onChange={(value) => patchForm({ max_rejected_limit: value })}
            />
          </div>

          <div className="param-card">
            <div className="param-card-title">Discretization</div>
            <ToggleRow
              checked={form.discretize}
              onChange={(checked) => patchForm({ discretize: checked })}
              title="Discretize limit values"
              subtitle="in multiples of 50"
              style={{ marginTop: 14 }}
            />
          </div>
        </div>
      </div>

      <div className="config-footer" style={{ marginTop: 24 }}>
        <button type="button" className="btn-secondary" onClick={handleResetCurrent} disabled={saving}>
          Redefinir esta tela
        </button>
        <button type="button" className="btn-secondary" onClick={handleResetAll} disabled={saving}>
          Redefinir tudo
        </button>
        <button
          type="button"
          className={`btn-primary${saveSuccess ? " saved" : ""}`}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Salvando..." : saveSuccess ? "Salvo ✓" : "Salvar"}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

interface PercentSliderCardProps {
  title: string;
  description: string;
  min: number;
  max: number;
  step: number;
  valuePct: number;
  decimals?: number;
  onChange: (pct: number) => void;
}

function PercentSliderCard({
  title,
  description,
  min,
  max,
  step,
  valuePct,
  decimals = 0,
  onChange,
}: PercentSliderCardProps) {
  const sliderRef = useRef<HTMLInputElement>(null);
  const clamped = Math.min(max, Math.max(min, valuePct));

  useEffect(() => {
    const slider = sliderRef.current;
    if (!slider) return;
    const pct = ((clamped - min) / (max - min)) * 100;
    slider.style.background = `linear-gradient(to right, var(--navy) ${pct}%, var(--border) ${pct}%)`;
  }, [clamped, min, max]);

  const display =
    decimals > 0 ? clamped.toFixed(decimals) : String(Math.round(clamped));

  return (
    <div className="param-card">
      <div className="param-card-title">{title}</div>
      <div className="param-card-desc">{description}</div>
      <div className="slider-labels">
        <span>{min}%</span>
        <span>{max}%</span>
      </div>
      <div className="native-slider-wrap">
        <input
          ref={sliderRef}
          type="range"
          className="native-slider"
          min={min}
          max={max}
          step={step}
          value={clamped}
          onChange={(e) => onChange(parseFloat(e.target.value))}
        />
      </div>
      <div className="slider-input-group">
        <input
          type="text"
          inputMode="decimal"
          value={display}
          onChange={(e) => {
            const num = parseNumeric(e.target.value);
            onChange(Math.min(max, Math.max(min, num)));
          }}
        />
        <span className="unit">%</span>
      </div>
    </div>
  );
}

function ToggleRow({
  checked,
  onChange,
  title,
  subtitle,
  style,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  title: string;
  subtitle: string;
  style?: CSSProperties;
}) {
  return (
    <div className="toggle-row" style={style}>
      <label className="toggle">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className="toggle-slider" />
      </label>
      <div className="toggle-info">
        <div className="toggle-title">{title}</div>
        <div className="toggle-sub">{subtitle}</div>
      </div>
    </div>
  );
}

function CurrencyInput({
  value,
  onChange,
  style,
}: {
  value: number;
  onChange: (value: number) => void;
  style?: CSSProperties;
}) {
  const [draft, setDraft] = useState(() => formatCurrencyDraft(value));

  useEffect(() => {
    setDraft(formatCurrencyDraft(value));
  }, [value]);

  return (
    <div className="input-currency-wrap" style={style}>
      <div className="input-prefix">R$</div>
      <input
        type="text"
        inputMode="decimal"
        value={draft}
        onChange={(e: ChangeEvent<HTMLInputElement>) => {
          const sanitized = e.target.value.replace(/[^0-9.,]/g, "");
          setDraft(sanitized);
          onChange(parseNumeric(sanitized));
        }}
        onBlur={() => setDraft(formatCurrencyDraft(value))}
      />
      <select className="input-currency-select" disabled>
        <option>BRL ▾</option>
      </select>
    </div>
  );
}

function formatCurrencyDraft(value: number): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPdRange(row: MultiplierRow, index: number, total: number): ReactNode {
  if (index === 0 && row.min_pd === 0) {
    return <span className="pd-range-text">PD ≤ {formatPdDisplay(row.max_pd)}</span>;
  }
  if (index === total - 1 && row.max_pd >= 1) {
    return <span className="pd-range-text">PD &gt; {formatPdDisplay(row.min_pd)}</span>;
  }
  return (
    <span className="pd-range-text">
      {formatPdDisplay(row.min_pd)} &lt; PD ≤ {formatPdDisplay(row.max_pd)}
    </span>
  );
}

interface MultiplierTableProps {
  rows: MultiplierRow[];
  editing: boolean;
  onToggleEdit: () => void;
  onChange: (rows: MultiplierRow[]) => void;
}

const MultiplierTable = forwardRef<HTMLDivElement, MultiplierTableProps>(function MultiplierTable(
  { rows, editing, onToggleEdit, onChange },
  ref,
) {
  const updateRow = (index: number, patch: Partial<MultiplierRow>) => {
    const next = rows.map((row, idx) => (idx === index ? { ...row, ...patch } : row));
    onChange(next);
  };

  return (
    <div ref={ref} className={`mult-table-card${editing ? " editing" : ""}`}>
      <div className="mult-table-header">
        <div className="param-card-title" style={{ marginBottom: 0 }}>
          Multipliers de alavancagem
        </div>
        <button type="button" className="btn-edit-small" onClick={onToggleEdit}>
          {editing ? (
            <>
              <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M5 13l4 4L19 7" />
              </svg>
              Pronto
            </>
          ) : (
            <>
              <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              Editar
            </>
          )}
        </button>
      </div>
      <table className="mult-table">
        <thead>
          <tr>
            <th>Faixa de PD</th>
            <th>Multiplier</th>
            <th>Interpretation</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const badge = INTERPRETATION_BADGES[index] ?? INTERPRETATION_BADGES.at(-1)!;
            const label = INTERPRETATION_LABELS[index] ?? INTERPRETATION_LABELS.at(-1)!;
            const isLow = row.multiplier < 1;
            return (
              <tr key={index}>
                <td>
                  {editing ? (
                    <span className="pd-range-text">
                      <input
                        type="text"
                        className="pd-value-input"
                        value={formatPdDisplay(row.min_pd)}
                        onChange={(e) =>
                          updateRow(index, { min_pd: parseNumeric(e.target.value) })
                        }
                      />
                      {" < PD ≤ "}
                      <input
                        type="text"
                        className="pd-value-input"
                        value={formatPdDisplay(row.max_pd)}
                        onChange={(e) =>
                          updateRow(index, { max_pd: parseNumeric(e.target.value) })
                        }
                      />
                    </span>
                  ) : (
                    formatPdRange(row, index, rows.length)
                  )}
                </td>
                <td>
                  <input
                    type="text"
                    inputMode="decimal"
                    className={`mult-input-badge${isLow ? " low" : ""}`}
                    value={row.multiplier.toFixed(2)}
                    readOnly={!editing}
                    onChange={(e) =>
                      updateRow(index, { multiplier: parseNumeric(e.target.value) })
                    }
                  />
                </td>
                <td>
                  <span className={`interpretation-badge ${badge}`}>{label}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
});
