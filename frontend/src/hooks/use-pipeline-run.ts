"use client";

import { useState, useCallback, useRef } from "react";
import { postAPI } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";

interface TriggerResponse {
  run_id: string;
  status: string;
}

interface RunProgress {
  run_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  rows_loaded: number | null;
  error_message: string | null;
}

const STAGE_ORDER = ["pending", "running", "bronze_complete", "silver_complete", "gold_complete", "success"] as const;

export function getStageIndex(status: string): number {
  const idx = STAGE_ORDER.indexOf(status as (typeof STAGE_ORDER)[number]);
  return idx >= 0 ? idx : 0;
}

export function getStageLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Queued",
    running: "Bronze Loading",
    bronze_complete: "Silver Transform",
    silver_complete: "Gold Aggregation",
    gold_complete: "Finalizing",
    success: "Completed",
    failed: "Failed",
  };
  return labels[status] ?? status;
}

export function usePipelineRun() {
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const subscribe = useCallback(
    (runId: string) => {
      cleanup();
      setIsRunning(true);
      setError(null);

      const url = `${API_BASE_URL}/api/v1/pipeline/runs/${runId}/stream`;
      const es = new EventSource(url);
      eventSourceRef.current = es;

      const handleEvent = (e: MessageEvent) => {
        try {
          const data: RunProgress = JSON.parse(e.data);
          setProgress(data);

          if (data.status === "success" || data.status === "failed") {
            setIsRunning(false);
            if (data.status === "failed") {
              setError(data.error_message ?? "Pipeline failed");
            }
            cleanup();
          }
        } catch {
          // ignore parse errors
        }
      };

      es.addEventListener("status_change", handleEvent);
      es.addEventListener("complete", handleEvent);
      es.addEventListener("error", (e) => {
        // SSE spec fires error on reconnect too — only treat actual failures
        if (es.readyState === EventSource.CLOSED) {
          setIsRunning(false);
          setError("Connection to pipeline stream lost");
          cleanup();
        }
      });
      es.addEventListener("timeout", () => {
        setIsRunning(false);
        setError("Pipeline stream timed out");
        cleanup();
      });
    },
    [cleanup],
  );

  const trigger = useCallback(async () => {
    setError(null);
    setProgress(null);
    try {
      const res = await postAPI<TriggerResponse>("/api/v1/pipeline/trigger");
      setProgress({
        run_id: res.run_id,
        status: res.status,
        started_at: new Date().toISOString(),
        finished_at: null,
        duration_seconds: null,
        rows_loaded: null,
        error_message: null,
      });
      subscribe(res.run_id);
      return res.run_id;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to trigger pipeline";
      setError(msg);
      return null;
    }
  }, [subscribe]);

  return { progress, isRunning, error, trigger, cleanup };
}
