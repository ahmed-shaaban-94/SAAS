/**
 * Crash reporting wiring for the Electron main process.
 *
 * Issue: #481 (POS hardening epic #479).
 *
 * ## Opt-in
 * Disabled by default — the app never phones home without explicit consent.
 * Enabled when EITHER holds:
 *   1. `DATAPULSE_CRASH_REPORTING=1` (or `=true`) in the environment, OR
 *   2. The SQLite `settings` row `crash_reporting_opt_in` = `"1"` / `"true"`.
 *
 * Pilots flip the sqlite row until a Settings UI lands (follow-up).
 *
 * ## PII scrubbing
 * `beforeSend` strips request bodies and common customer-identifying tags
 * (`customer_id`, `national_id`, `phone`) from every event. Verified by
 * unit tests in `__tests__/observability/sentry.test.ts` — we test the
 * scrubber directly against constructed event objects so the Sentry SDK
 * itself is never part of the test surface.
 *
 * ## Scope boundaries (this PR)
 * - MAIN process only. Renderer init is deferred (the frontend bundle is
 *   shared with the SaaS web build and we can't verify SaaS build here).
 * - No source-map upload in CI yet (`SENTRY_AUTH_TOKEN` not wired).
 */

import type { Event as SentryEvent } from "@sentry/electron/main";
import type Database from "better-sqlite3";

import { getSetting } from "../db/settings";

/** Keys on `event.tags` that MUST be scrubbed before any send. */
export const PII_TAG_KEYS = ["customer_id", "national_id", "phone"] as const;

/** Keys inside arbitrary free-form maps (`contexts`, `extra`) that look
 * like customer identifiers and should also be stripped. Keep this list in
 * sync with PII_TAG_KEYS so a typo tag under `contexts.business` can't leak. */
const PII_FREEFORM_KEYS: readonly string[] = PII_TAG_KEYS;

export interface InitSentryParams {
  dsn: string;
  release: string;
  environment: string;
  /** 0-1 sample rate for performance traces. Defaults to 0.05 to keep
   * volume low for pilots. */
  tracesSampleRate?: number;
}

/**
 * Read the opt-in state. `db` may be null for env-only checks (tests,
 * early boot). Environment always wins over the sqlite row.
 */
export function isCrashReportingEnabled(db: Database.Database | null): boolean {
  const envFlag = process.env.DATAPULSE_CRASH_REPORTING;
  if (envFlag === "1" || envFlag?.toLowerCase() === "true") return true;
  if (envFlag === "0" || envFlag?.toLowerCase() === "false") return false;

  if (!db) return false;
  const row = getSetting(db, "crash_reporting_opt_in");
  return row === "1" || row?.toLowerCase() === "true";
}

/**
 * Pure PII scrubber for `Sentry.init({ beforeSend })`. Exported so tests
 * can exercise every branch without booting Sentry. Returns the event
 * (possibly mutated) or null to drop it entirely — we never drop, only
 * scrub.
 */
export function scrubPii(event: SentryEvent): SentryEvent {
  // Drop arbitrary request bodies — they can carry cart payloads, voucher
  // codes, national IDs, or anything else a caller decided to serialize.
  if (event.request && "data" in event.request) {
    delete (event.request as { data?: unknown }).data;
  }

  // Tag map scrub. Sentry guarantees tags are string -> primitive.
  if (event.tags && typeof event.tags === "object") {
    for (const k of PII_TAG_KEYS) {
      if (k in event.tags) {
        delete (event.tags as Record<string, unknown>)[k];
      }
    }
  }

  // Nested free-form maps — `contexts` and `extra` can carry anything.
  stripFreeformKeys(event.contexts as Record<string, unknown> | undefined);
  stripFreeformKeys(event.extra as Record<string, unknown> | undefined);

  // User identifiers. We never send logged-in POS staff either — the
  // staff_id UUID is enough to correlate, but email/username could leak
  // through if a caller ever populated them.
  if (event.user) {
    delete event.user.email;
    delete event.user.username;
    delete event.user.ip_address;
  }

  return event;
}

/**
 * Walk a shallow map and remove any top-level key that looks like a
 * customer identifier. We intentionally do NOT recurse — the point is to
 * catch the common mistake of tagging `contexts.business = { customer_id }`
 * not to do deep payload inspection.
 */
function stripFreeformKeys(
  map: Record<string, unknown> | undefined,
): void {
  if (!map) return;
  for (const topKey of Object.keys(map)) {
    const inner = map[topKey];
    if (inner && typeof inner === "object") {
      for (const leak of PII_FREEFORM_KEYS) {
        if (leak in (inner as Record<string, unknown>)) {
          delete (inner as Record<string, unknown>)[leak];
        }
      }
    }
  }
}

// ── Renderer-error capture bridge ──────────────────────────────
//
// Structured payload the renderer posts through the
// `observability.captureError` IPC channel. Schema is intentionally
// fixed + minimal so the renderer cannot stuff arbitrary PII into the
// payload: the `scrubPii` `beforeSend` is still applied, but a narrow
// surface is the first line of defence.
export interface RendererErrorPayload {
  message: string;
  stack?: string;
  /** Short source classifier — e.g. "error-boundary", "unhandled-rejection",
   *  "window-error". Rendered as a Sentry tag so we can filter the dashboard. */
  source?: string;
}

const RENDERER_SOURCE_ALLOWLIST = new Set([
  "error-boundary",
  "unhandled-rejection",
  "window-error",
  "manual",
]);

type SentryMainModule = typeof import("@sentry/electron/main");

// Cache the SDK module handle from the first init so soft-error capture
// doesn't re-import on every IPC call (renderer crashes can burst).
let sentryReady = false;
let sentryModule: SentryMainModule | null = null;

/** Test-only — reset the init state so each test case starts clean. */
export function _resetSentryForTests(): void {
  sentryReady = false;
  sentryModule = null;
}

/** Test-only — inject a stub SDK module + mark ready. Used by Jest to
 *  assert `captureException` call shape without running `initSentry`. */
export function __setSentryModuleForTests(
  mod: Pick<SentryMainModule, "captureException">,
): void {
  sentryModule = mod as SentryMainModule;
  sentryReady = true;
}

/** Read init state — exposed for handler code + tests; do not mutate. */
export function isSentryReady(): boolean {
  return sentryReady;
}

/**
 * Lazy side-effect init. The caller is responsible for only invoking this
 * when `isCrashReportingEnabled` returned true, so we don't import
 * `@sentry/electron/main` at module scope (that would pull the SDK into
 * the bundle even when the user has opted out).
 */
export async function initSentry(params: InitSentryParams): Promise<void> {
  // Dynamic import so a user who has opted out never pays for the SDK
  // at package install / boot time.
  const mod = await import("@sentry/electron/main");
  mod.init({
    dsn: params.dsn,
    release: params.release,
    environment: params.environment,
    tracesSampleRate: params.tracesSampleRate ?? 0.05,
    // `beforeSend` is typed against Sentry's `ErrorEvent` (narrower than
    // our more permissive `SentryEvent`). The scrubber is event-type
    // agnostic — it only mutates shallow top-level fields — so we cast
    // on the way in.
    beforeSend: (event) => scrubPii(event as SentryEvent) as typeof event,
  });
  sentryModule = mod;
  sentryReady = true;
}

/**
 * Forward a soft renderer error to Sentry. Called by the
 * `observability.captureError` IPC handler.
 *
 * Hard renderer crashes (`render-process-gone`) are already captured by
 * `@sentry/electron/main`'s default integrations — this path is only for
 * uncaught JS exceptions + unhandled promise rejections inside the page.
 *
 * No-op (silent) when Sentry was not initialised — respects opt-out
 * without forcing the caller to guard every call site.
 */
export function captureRendererError(payload: RendererErrorPayload): void {
  if (!sentryReady || !sentryModule) return;
  const err = new Error(payload.message);
  if (payload.stack) err.stack = payload.stack;
  const source =
    payload.source && RENDERER_SOURCE_ALLOWLIST.has(payload.source)
      ? payload.source
      : "manual";
  sentryModule.captureException(err, {
    tags: { process: "renderer", renderer_source: source },
  });
}
