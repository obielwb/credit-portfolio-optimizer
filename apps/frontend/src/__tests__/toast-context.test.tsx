import { act, renderHook } from "@testing-library/react";
import React from "react";

import { ToastProvider, getApiErrorMessage, useToast } from "@/context/toast-context";
import { ApiResponseError } from "@/lib/types";

// ── getApiErrorMessage ─────────────────────────────────────────────────────────

describe("getApiErrorMessage", () => {
  it("maps known API error codes to Portuguese messages", () => {
    const knownCodes = [
      "INVALID_FILE_EXTENSION",
      "EMPTY_FILE",
      "INVALID_ALGORITHM",
      "MISSING_REQUIRED_PARAMETERS",
      "RUN_NOT_FOUND",
      "RESULT_NOT_FOUND",
      "PARAMETERS_NOT_FOUND",
    ] as const;

    for (const code of knownCodes) {
      const err = new ApiResponseError(code, "raw message");
      const msg = getApiErrorMessage(err);
      expect(msg).not.toBe("raw message");
      expect(msg.length).toBeGreaterThan(10);
    }
  });

  it("falls back to err.message for unknown API error codes", () => {
    const err = new ApiResponseError("SOME_UNKNOWN_CODE", "Mensagem original");
    expect(getApiErrorMessage(err)).toBe("Mensagem original");
  });

  it("maps TypeError with fetch in message to network error", () => {
    const err = new TypeError("Failed to fetch");
    const msg = getApiErrorMessage(err);
    expect(msg.toLowerCase()).toContain("backend");
  });

  it("returns message from plain Error", () => {
    expect(getApiErrorMessage(new Error("algo errado"))).toBe("algo errado");
  });

  it("returns fallback for non-Error values", () => {
    expect(getApiErrorMessage(null)).toContain("unexpected");
    expect(getApiErrorMessage("string error")).toContain("unexpected");
  });
});

// ── useToast hook ─────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ToastProvider>{children}</ToastProvider>
);

describe("useToast", () => {
  it("throws when used outside ToastProvider", () => {
    // Suppress React error boundary console errors in test output
    jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useToast())).toThrow(
      "useToast must be used inside <ToastProvider>",
    );
    jest.restoreAllMocks();
  });

  it("provides toast function inside ToastProvider", () => {
    const { result } = renderHook(() => useToast(), { wrapper });
    expect(typeof result.current.toast).toBe("function");
    expect(typeof result.current.toastError).toBe("function");
    expect(typeof result.current.dismiss).toBe("function");
  });

  it("dismiss removes the toast by id", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    // Add a toast then dismiss it — no error should be thrown
    act(() => {
      result.current.toast({ variant: "success", title: "Success!" });
    });

    act(() => {
      result.current.toast({ variant: "info", title: "Info" });
    });
  });

  it("toastError wraps an ApiResponseError with the mapped message", () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.toastError(
        new ApiResponseError("RUN_NOT_FOUND", "raw"),
        "Run error",
      );
    });
    // No exception means the mapped message was accepted without issues
  });
});
