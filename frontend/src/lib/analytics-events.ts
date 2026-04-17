/**
 * Golden-Path event helpers (Phase 2, Task 0 / #399).
 *
 * Four events instrument the upload-to-insight funnel so TTFI can be
 * measured as the delta between `upload_started` and `first_insight_seen`
 * in PostHog. See docs/brain/incidents/2026-04-17-ttfi-baseline.md.
 *
 * Each helper is idempotent within a session via sessionStorage guards,
 * so accidental remounts or navigation loops do not skew the funnel.
 */

import { trackEvent } from "@/lib/analytics";

export const GOLDEN_PATH_EVENTS = {
  UPLOAD_STARTED: "upload_started",
  UPLOAD_COMPLETED: "upload_completed",
  FIRST_DASHBOARD_VIEW: "first_dashboard_view",
  FIRST_INSIGHT_SEEN: "first_insight_seen",
} as const;

type GoldenPathEvent = (typeof GOLDEN_PATH_EVENTS)[keyof typeof GOLDEN_PATH_EVENTS];

const SESSION_GUARD_PREFIX = "ttfi_fired:";

function hasFired(key: string): boolean {
  if (typeof sessionStorage === "undefined") return false;
  return sessionStorage.getItem(SESSION_GUARD_PREFIX + key) === "1";
}

function markFired(key: string): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(SESSION_GUARD_PREFIX + key, "1");
}

/**
 * Name of the window-level CustomEvent dispatched on every golden-path
 * capture. Listeners (E2E specs, dev tooling, future observability bridges)
 * can subscribe without depending on PostHog being configured.
 */
export const TTFI_WINDOW_EVENT = "ttfi:event";

function dispatchWindowEvent(
  name: GoldenPathEvent,
  properties: Record<string, unknown>,
): void {
  if (typeof window === "undefined" || typeof CustomEvent !== "function") return;
  try {
    window.dispatchEvent(
      new CustomEvent(TTFI_WINDOW_EVENT, { detail: { name, properties } }),
    );
  } catch {
    // Emitter is best-effort — never let a tracking failure bubble up.
  }
}

function fireOnce(
  guardKey: string,
  event: GoldenPathEvent,
  props: Record<string, unknown>,
): void {
  if (hasFired(guardKey)) return;
  markFired(guardKey);
  const stamped = { ...props, ttfi_seam: event };
  trackEvent(event, stamped);
  // Also emit a CustomEvent so tests + tooling can observe the funnel
  // regardless of whether PostHog is configured (e.g., CI without a key).
  dispatchWindowEvent(event, stamped);
}

export function trackUploadStarted(): void {
  fireOnce(GOLDEN_PATH_EVENTS.UPLOAD_STARTED, GOLDEN_PATH_EVENTS.UPLOAD_STARTED, {});
}

export interface UploadCompletedProps {
  run_id: string;
  duration_seconds: number;
  rows_loaded: number | null;
}

export function trackUploadCompleted(props: UploadCompletedProps): void {
  // Dedup per run_id — a single session can legitimately complete multiple runs.
  const guardKey = `${GOLDEN_PATH_EVENTS.UPLOAD_COMPLETED}:${props.run_id}`;
  fireOnce(guardKey, GOLDEN_PATH_EVENTS.UPLOAD_COMPLETED, { ...props });
}

export function trackFirstDashboardView(): void {
  fireOnce(
    GOLDEN_PATH_EVENTS.FIRST_DASHBOARD_VIEW,
    GOLDEN_PATH_EVENTS.FIRST_DASHBOARD_VIEW,
    {},
  );
}

export interface FirstInsightSeenProps {
  kind: string;
  confidence: number;
}

export function trackFirstInsightSeen(props: FirstInsightSeenProps): void {
  fireOnce(
    GOLDEN_PATH_EVENTS.FIRST_INSIGHT_SEEN,
    GOLDEN_PATH_EVENTS.FIRST_INSIGHT_SEEN,
    { ...props },
  );
}

/**
 * Test-only. Clears session guards so helpers can re-fire.
 * Not exported from any barrel; reach for it explicitly in tests.
 */
export function __resetGoldenPathSessionGuardsForTest(): void {
  if (typeof sessionStorage === "undefined") return;
  const toRemove: string[] = [];
  for (let i = 0; i < sessionStorage.length; i++) {
    const k = sessionStorage.key(i);
    if (k && k.startsWith(SESSION_GUARD_PREFIX)) toRemove.push(k);
  }
  toRemove.forEach((k) => sessionStorage.removeItem(k));
}
