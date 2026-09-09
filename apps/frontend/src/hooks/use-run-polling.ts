"use client";






import { useEffect, useState } from "react";

import { getRunStatus } from "@/lib/api";
import { ApiResponseError, type RunStatusSchema } from "@/lib/types";

const POLL_INTERVAL_MS = 1500;
const TERMINAL: ReadonlySet<RunStatusSchema["state"]> = new Set([
  "completed",
  "failed",
]);

export interface UseRunPollingResult {
  status: RunStatusSchema | null;
  error: string | null;
  isPolling: boolean;
}







export function useRunPolling(runId: number | null): UseRunPollingResult {
  const [status, setStatus] = useState<RunStatusSchema | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (runId === null) {
      setStatus(null);
      setError(null);
      setIsPolling(false);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setStatus(null);
    setError(null);
    setIsPolling(true);

    
    async function tick(): Promise<void> {
      try {
        const next = await getRunStatus(runId as number);
        if (cancelled) return;
        setStatus(next);
        if (TERMINAL.has(next.state)) {
          setIsPolling(false);
          return;
        }
        timer = setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiResponseError
            ? err.message
            : "Failed to retrieve run status.",
        );
        setIsPolling(false);
      }
    }

    void tick();

    return () => {
      cancelled = true;
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [runId]);

  return { status, error, isPolling };
}
