import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/constants";

export interface PipelineStreamEvent {
  run_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  rows_loaded: number | null;
  error_message: string | null;
}

interface UsePipelineStreamResult {
  /** Latest event received from the SSE stream */
  event: PipelineStreamEvent | null;
  /** Whether the stream is currently connected */
  connected: boolean;
  /** Any error that occurred */
  error: string | null;
  /** Manually close the stream */
  close: () => void;
}

/**
 * SSE hook for real-time pipeline run progress.
 *
 * Connects to GET /api/v1/pipeline/runs/{runId}/stream and receives
 * `status_change` and `complete` events. Auto-reconnects on failure
 * with exponential backoff (max 30s). Closes automatically on
 * terminal states (success/failed/cancelled).
 */
export function usePipelineStream(
  runId: string | null,
): UsePipelineStreamResult {
  const [event, setEvent] = useState<PipelineStreamEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const close = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = undefined;
    }
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!runId) {
      close();
      return;
    }

    function connect() {
      const url = `${API_BASE_URL}/api/v1/pipeline/runs/${runId}/stream`;
      const es = new EventSource(url);
      sourceRef.current = es;

      es.onopen = () => {
        setConnected(true);
        setError(null);
        retryCountRef.current = 0;
      };

      const handleEvent = (e: MessageEvent) => {
        try {
          const data: PipelineStreamEvent = JSON.parse(e.data);
          setEvent(data);

          // Close on terminal events
          if (e.type === "complete" || e.type === "timeout" || e.type === "error") {
            close();
          }
        } catch {
          // Ignore malformed events
        }
      };

      es.addEventListener("status_change", handleEvent);
      es.addEventListener("complete", handleEvent);
      es.addEventListener("timeout", handleEvent);
      es.addEventListener("error", (e) => {
        // EventSource fires 'error' on both connection loss and server errors
        if (es.readyState === EventSource.CLOSED) {
          setConnected(false);
          // Reconnect with exponential backoff (max 30s)
          const delay = Math.min(1000 * 2 ** retryCountRef.current, 30000);
          retryCountRef.current += 1;
          setError(`Connection lost. Retrying in ${delay / 1000}s...`);
          retryTimerRef.current = setTimeout(connect, delay);
        }
      });
    }

    connect();

    return () => {
      close();
    };
  }, [runId, close]);

  return { event, connected, error, close };
}
