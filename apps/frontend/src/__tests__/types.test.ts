import { ApiResponseError } from "@/lib/types";

describe("ApiResponseError", () => {
  it("creates an instance with correct properties", () => {
    const err = new ApiResponseError("RUN_NOT_FOUND", "Run not found", { run_id: 42 }, 404);

    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ApiResponseError);
    expect(err.code).toBe("RUN_NOT_FOUND");
    expect(err.message).toBe("Run not found");
    expect(err.details).toEqual({ run_id: 42 });
    expect(err.httpStatus).toBe(404);
    expect(err.name).toBe("ApiResponseError");
  });

  it("works without optional httpStatus", () => {
    const err = new ApiResponseError("EMPTY_FILE", "File is empty");
    expect(err.httpStatus).toBeUndefined();
    expect(err.details).toEqual({});
  });

  it("is catchable as a standard Error", () => {
    expect(() => {
      throw new ApiResponseError("TEST", "test error");
    }).toThrow("test error");
  });

  it("instanceof check works in catch block", () => {
    try {
      throw new ApiResponseError("RUN_NOT_FOUND", "not found", {}, 404);
    } catch (e) {
      expect(e instanceof ApiResponseError).toBe(true);
      if (e instanceof ApiResponseError) {
        expect(e.code).toBe("RUN_NOT_FOUND");
        expect(e.httpStatus).toBe(404);
      }
    }
  });
});
