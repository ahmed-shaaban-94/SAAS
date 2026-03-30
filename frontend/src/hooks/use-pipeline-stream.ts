import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "next-auth/react";

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
 * SSE hook for real-time pipeline run progress using fetch + ReadableStream.
 *
 * Uses fetch (not EventSource) so we can send Authorization headers.
 * Connects to GET /api/v1/pipeline/runs/{runId}/stream and parses
 * `status_change` and `complete` SSE events. Auto-reconnects on
 * transient failures with exponential backoff (max 30s).
 * Closes automatically on terminal states or auth errors.
 */
export function usePipelineStream(
  runId: string | null,
): UsePipelineStreamResult {
  const [event, setEvent] = useState<PipelineStreamEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const close = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = undefined;
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setConnected(false);
  }, []);

  useEffect(() => {
    if (!runId) {
      close();
      return;
    }

    async function connect() {
      const url = `${API_BASE_URL}/api/v1/pipeline/runs/${runId}/stream`;
      const controller = new AbortController();
      abortRef.current = controller;

      // Build auth headers
      const headers: Record<string, string> = {};
      try {
        const session = await getSession();
        if (session?.accessToken) {
          headers["Authorization"] = `Bearer ${session.accessToken}`;
        }
      } catch {
        // Fall through without auth
      }

      try {
        const res = await fetch(url, {
          headers,
          signal: controller.signal,
        });

        // Permanent errors — don't retry
        if (res.status === 401 || res.status === 403 || res.status === 404) {
          setError(`HTTP ${res.status}: ${res.statusText}`);
          setConnected(false);
          return;
        }

        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`);
        }

        setConnected(true);
        setError(null);
        retryCountRef.current = 0;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            const lines = part.split("\n");
            let eventType = "";
            let eventData = "";

            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7);
              } else if (line.startsWith("data: ")) {
                eventData = line.slice(6);
              }
            }

            if (eventData) {
              try {
                const data: PipelineStreamEvent = JSON.parse(eventData);
                setEvent(data);

                if (
                  eventType === "complete" ||
                  eventType === "timeout" ||
                  eventType === "error"
                ) {
                  close();
                  return;
                }
              } catch {
                // Skip malformed events
              }
            }
          }
        }

        // Stream ended normally
        setConnected(false);
      } catch (err) {
        if (controller.signal.aborted) return;

        // Transient error — reconnect with exponential backoff
        setConnected(false);
        const delay = Math.min(1000 * 2 ** retryCountRef.current, 30000);
        retryCountRef.current += 1;
        setError(`Connection lost. Retrying in ${delay / 1000}s...`);
        retryTimerRef.current = setTimeout(connect, delay);
      }
    }

    connect();

    return () => {
      close();
    };
  }, [runId, close]);

  return { event, connected, error, close };
}
