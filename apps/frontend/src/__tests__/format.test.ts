import {
  avatarColorFor,
  classifyLimit,
  classifyScore,
  etapaProgress,
  formatAlgorithm,
  formatBRL,
  formatBRLFull,
  formatDuracao,
  formatPct,
  tokenInitials,
} from "@/lib/format";

describe("formatBRL", () => {
  it("formats values above 1M with M suffix", () => {
    expect(formatBRL(1_500_000)).toBe("R$ 1.5M");
    expect(formatBRL(2_000_000)).toBe("R$ 2.0M");
  });

  it("formats values above 1K with K suffix", () => {
    expect(formatBRL(5000)).toBe("R$ 5K");
    expect(formatBRL(12_300)).toBe("R$ 12K");
  });

  it("formats small values as BRL currency", () => {
    const result = formatBRL(150);
    expect(result).toMatch(/R\$/);
    expect(result).toMatch(/150/);
  });

  it("returns — for null, undefined and NaN", () => {
    expect(formatBRL(null)).toBe("—");
    expect(formatBRL(undefined)).toBe("—");
    expect(formatBRL(NaN)).toBe("—");
  });
});

describe("formatBRLFull", () => {
  it("formats any positive value as full BRL currency", () => {
    const result = formatBRLFull(1234.56);
    expect(result).toMatch(/R\$/);
    expect(result).toMatch(/1\.234/);
  });

  it("returns — for null", () => {
    expect(formatBRLFull(null)).toBe("—");
  });
});

describe("formatPct", () => {
  it("converts decimal to percentage string with correct decimals", () => {
    expect(formatPct(0.5, 0)).toBe("50%");
    expect(formatPct(0.123, 1)).toBe("12.3%");
    expect(formatPct(1.0, 0)).toBe("100%");
  });

  it("returns — for null/undefined/NaN", () => {
    expect(formatPct(null)).toBe("—");
    expect(formatPct(undefined)).toBe("—");
    expect(formatPct(NaN)).toBe("—");
  });
});

describe("formatDuracao", () => {
  it("formats milliseconds to m/s string", () => {
    expect(formatDuracao(90_000)).toBe("1m 30s");
    expect(formatDuracao(0)).toBe("0m 00s");
    expect(formatDuracao(3_600_000)).toBe("60m 00s");
  });

  it("returns — for null/undefined/NaN", () => {
    expect(formatDuracao(null)).toBe("—");
    expect(formatDuracao(undefined)).toBe("—");
    expect(formatDuracao(NaN)).toBe("—");
  });
});

describe("formatAlgorithm", () => {
  it("formats known algorithm identifiers", () => {
    expect(formatAlgorithm("simplex")).toBe("Simplex");
    expect(formatAlgorithm("simplex_ortools")).toBe("Simplex OR-Tools");
    expect(formatAlgorithm("branch_bound")).toBe("Branch and Bound");
  });
});

describe("classifyScore", () => {
  it("classifies high score as Excelente", () => {
    expect(classifyScore(850).label).toBe("Excelente");
    expect(classifyScore(700).label).toBe("Excelente");
  });

  it("classifies mid score as Bom", () => {
    expect(classifyScore(500).label).toBe("Bom");
    expect(classifyScore(699).label).toBe("Bom");
  });

  it("classifies low score as Regular", () => {
    expect(classifyScore(0).label).toBe("Regular");
    expect(classifyScore(499).label).toBe("Regular");
  });

  it("returns fallback for null/undefined", () => {
    expect(classifyScore(null).label).toBe("—");
    expect(classifyScore(undefined).label).toBe("—");
  });
});

describe("classifyLimit", () => {
  it("returns denied when limit is null, undefined or zero", () => {
    expect(classifyLimit(null, 1000)).toBe("denied");
    expect(classifyLimit(undefined, 1000)).toBe("denied");
    expect(classifyLimit(0, 1000)).toBe("denied");
  });

  it("returns above when limit exceeds capacity", () => {
    expect(classifyLimit(2000, 1000)).toBe("above");
  });

  it("returns full when limit is within capacity", () => {
    expect(classifyLimit(500, 1000)).toBe("full");
    expect(classifyLimit(1000, 1000)).toBe("full");
  });
});

describe("etapaProgress", () => {
  it("returns 0% for null/undefined state", () => {
    expect(etapaProgress(null).pct).toBe(0);
    expect(etapaProgress(undefined).pct).toBe(0);
  });

  it("returns 100% for completed", () => {
    expect(etapaProgress("completed").pct).toBe(100);
  });

  it("returns 100% for failed", () => {
    expect(etapaProgress("failed").pct).toBe(100);
  });

  it("returns incremental progress for known stages", () => {
    const pct1 = etapaProgress("ingestion").pct;
    const pct2 = etapaProgress("tableau_calculation").pct;
    expect(pct1).toBeGreaterThan(0);
    expect(pct2).toBeGreaterThan(pct1);
  });
});

describe("avatarColorFor", () => {
  it("returns a valid hex color string", () => {
    const color = avatarColorFor("CLI-001");
    expect(color).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("returns the same color for the same token (deterministic)", () => {
    expect(avatarColorFor("TOKEN-A")).toBe(avatarColorFor("TOKEN-A"));
  });

  it("may return different colors for different tokens", () => {
    const colors = ["A", "B", "C", "D", "E", "F"].map(avatarColorFor);
    const unique = new Set(colors);
    expect(unique.size).toBeGreaterThan(1);
  });
});

describe("tokenInitials", () => {
  it("returns last 3 alphanumeric chars in uppercase", () => {
    expect(tokenInitials("CLI-001")).toBe("001");
    expect(tokenInitials("ABCDE")).toBe("CDE");
  });

  it("strips non-alphanumeric characters", () => {
    expect(tokenInitials("A-B-C")).toBe("ABC");
  });
});
