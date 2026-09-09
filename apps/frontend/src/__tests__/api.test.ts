




import { ApiResponseError } from "@/lib/types";

// Polyfill fetch with jest.fn() before importing api module
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Helper to build a mock fetch response
function makeResponse(
  body: unknown,
  status = 200,
  headers: Record<string, string> = {},
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    blob: () => Promise.resolve(new Blob([JSON.stringify(body)])),
    headers: {
      get: (key: string) => headers[key] ?? null,
    },
  } as unknown as Response;
}

describe("api module — envelope parsing", () => {
  beforeEach(() => mockFetch.mockReset());

  it("extracts data from { status: ok, data } envelope", async () => {
    const { getActiveParameters } = await import("@/lib/api");

    mockFetch.mockResolvedValueOnce(
      makeResponse({ status: "ok", data: { id: 1, utilization_rate: 0.7 } }),
    );

    const result = await getActiveParameters();
    expect(result).toMatchObject({ id: 1, utilization_rate: 0.7 });
  });

  it("throws ApiResponseError when envelope status is error", async () => {
    const { getActiveParameters } = await import("@/lib/api");

    mockFetch.mockResolvedValue(
      makeResponse(
        { status: "error", code: "PARAMETERS_NOT_FOUND", message: "Parameters not found" },
        404,
      ),
    );

    const err = await getActiveParameters().catch((e) => e);
    expect(err).toBeInstanceOf(ApiResponseError);
    expect(err.code).toBe("PARAMETERS_NOT_FOUND");
  });

  it("throws ApiResponseError on non-ok HTTP status with detail field", async () => {
    const { getActiveParameters } = await import("@/lib/api");

    mockFetch.mockResolvedValueOnce(
      makeResponse(
        { detail: { code: "RUN_NOT_FOUND", message: "not found" } },
        404,
      ),
    );

    const err = await getActiveParameters().catch((e) => e);
    expect(err).toBeInstanceOf(ApiResponseError);
    expect(err.code).toBe("RUN_NOT_FOUND");
    expect(err.httpStatus).toBe(404);
  });

  it("falls back to UNKNOWN_ERROR code when no code in body", async () => {
    const { getRunStatus } = await import("@/lib/api");

    mockFetch.mockResolvedValueOnce(makeResponse({ message: "Internal error" }, 500));

    const err = await getRunStatus(1).catch((e) => e);
    expect(err).toBeInstanceOf(ApiResponseError);
    expect(err.code).toBe("UNKNOWN_ERROR");
  });
});

describe("api module — getRunStatus", () => {
  beforeEach(() => mockFetch.mockReset());

  it("returns body directly (no envelope) when status is ok", async () => {
    const { getRunStatus } = await import("@/lib/api");

    const runStatus = {
      run_id: 5,
      state: "completed",
      current_stage: null,
      started_at: null,
      finished_at: null,
      error: null,
    };

    mockFetch.mockResolvedValueOnce(makeResponse(runStatus, 200));

    const result = await getRunStatus(5);
    expect(result.run_id).toBe(5);
    expect(result.state).toBe("completed");
  });

  it("throws ApiResponseError when run not found", async () => {
    const { getRunStatus } = await import("@/lib/api");

    mockFetch.mockResolvedValueOnce(
      makeResponse({ detail: { code: "RUN_NOT_FOUND", message: "Run not found" } }, 404),
    );

    const err = await getRunStatus(999).catch((e) => e);
    expect(err).toBeInstanceOf(ApiResponseError);
    expect(err.code).toBe("RUN_NOT_FOUND");
  });
});

describe("api module — getDashboard query params", () => {
  beforeEach(() => mockFetch.mockReset());

  it("builds correct query string with all params", async () => {
    const { getDashboard } = await import("@/lib/api");

    mockFetch.mockResolvedValueOnce(
      makeResponse({
        status: "ok",
        data: { file: {}, clients: [], totais: {}, pagina: 1, page_size: 10, total_items: 0, total_pages: 0, sort_by: null, sort_order: null },
      }),
    );

    await getDashboard({ run_id: 3, page: 2, page_size: 10, sort_by: "score", sort_order: "desc" });

    const url = (mockFetch.mock.calls[0] as [string])[0];
    expect(url).toContain("run_id=3");
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=10");
    expect(url).toContain("sort_by=score");
    expect(url).toContain("sort_order=desc");
  });
});

describe("api module — getExecutionHistory pagination", () => {
  beforeEach(() => mockFetch.mockReset());

  it("builds query string with status filter", async () => {
    const { getExecutionHistory } = await import("@/lib/api");

    mockFetch.mockResolvedValueOnce(
      makeResponse({ status: "ok", data: { items: [], total_items: 0 } }),
    );

    await getExecutionHistory({ page: 1, page_size: 20, status: "success" });

    const url = (mockFetch.mock.calls[0] as [string])[0];
    expect(url).toContain("status=success");
    expect(url).toContain("page=1");
    expect(url).toContain("page_size=20");
  });
});
