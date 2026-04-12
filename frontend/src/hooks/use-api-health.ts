import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Monitors API health when errors are detected.
 *
 * Starts polling `/health/ready` every 10 seconds when signalled via
 * {@link reportError}.  Stops polling once the API responds with 200.
 * On recovery, calls {@link onRecover} so the caller can trigger a
 * global SWR revalidation.
 */
export function useApiHealth(onRecover?: () => void) {
  const [isApiDown, setIsApiDown] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const downSinceRef = useRef<Date | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    try {
      const res = await fetch("/health/ready", { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        stopPolling();
        setIsRecovering(true);
        setIsApiDown(false);
        downSinceRef.current = null;
        onRecover?.();
        // Show recovery banner for 3 seconds then clear
        setTimeout(() => setIsRecovering(false), 3000);
      }
    } catch {
      // Still down — keep polling
    }
  }, [stopPolling, onRecover]);

  /** Call this when any SWR hook encounters a network/5xx error. */
  const reportError = useCallback(() => {
    if (intervalRef.current) return; // already polling
    downSinceRef.current = new Date();
    setIsApiDown(true);
    setIsRecovering(false);
    // Poll /health/ready every 10s
    intervalRef.current = setInterval(poll, 10_000);
  }, [poll]);

  // Cleanup on unmount
  useEffect(() => stopPolling, [stopPolling]);

  return { isApiDown, isRecovering, reportError };
}
