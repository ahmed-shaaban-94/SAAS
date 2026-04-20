"use client";

import { useEffect } from "react";

/**
 * Forwards renderer-side soft errors (uncaught exceptions + unhandled
 * promise rejections) to the Electron main process via the
 * `observability.captureError` IPC channel. From there the main-process
 * Sentry SDK posts them with `process=renderer` tags + PII scrub.
 *
 * ### Scope
 *
 * - Runs **only** when `window.electronAPI.observability?.captureError`
 *   is present. On the SaaS web build (`window.electronAPI` undefined)
 *   the optional chain resolves to `undefined` and the hook mounts a
 *   no-op unsubscribe.
 * - Captures soft errors only. Hard renderer crashes
 *   (`render-process-gone`) are already handled by the main-process
 *   SDK's default integrations — this hook intentionally does NOT
 *   reimplement that.
 *
 * ### Safety
 *
 * The IPC invoke is wrapped in try/catch + `.catch(noop)` so a failure
 * to reach the bridge cannot itself throw an error that retriggers the
 * capture path. Silent drop is the correct failure mode here.
 *
 * Mount from `frontend/src/app/(pos)/layout.tsx` only — do not mount in
 * the SaaS (app) layout since it's POS-specific.
 */
export function useRendererCrashBridge(): void {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const api = window.electronAPI?.observability?.captureError;
    if (!api) return; // SaaS web or older POS build without the bridge

    const forward = (
      payload: {
        message: string;
        stack?: string;
        source: "unhandled-rejection" | "window-error";
      },
    ): void => {
      try {
        api(payload).catch(() => {
          // Swallow — see module doc: silent drop on IPC failure.
        });
      } catch {
        // Same rationale — never throw from the capture path.
      }
    };

    const onError = (ev: ErrorEvent): void => {
      const err = ev.error;
      const message =
        (err && typeof err === "object" && "message" in err && typeof err.message === "string"
          ? err.message
          : undefined) ?? ev.message ?? "window error";
      const stack =
        err && typeof err === "object" && "stack" in err && typeof err.stack === "string"
          ? err.stack
          : undefined;
      forward({ message, stack, source: "window-error" });
    };

    const onRejection = (ev: PromiseRejectionEvent): void => {
      const reason = ev.reason;
      const message =
        reason instanceof Error
          ? reason.message
          : typeof reason === "string"
            ? reason
            : "unhandled promise rejection";
      const stack = reason instanceof Error ? reason.stack : undefined;
      forward({ message, stack, source: "unhandled-rejection" });
    };

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
}
