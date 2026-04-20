/**
 * Structured logging for the Electron main process.
 *
 * Wraps `pino` with:
 *   - daily rotation (10MB cap, 14-file retention) via `pino-roll`
 *   - redaction of auth headers + customer identifiers + voucher codes
 *   - JSON output to disk, pretty-printed console in dev
 *
 * The disk location is `app.getPath('logs')` which maps to:
 *   - Windows: `%APPDATA%\\DataPulse POS\\logs\\`
 *   - macOS:   `~/Library/Logs/DataPulse POS/`
 *   - Linux:   `~/.config/DataPulse POS/logs/`
 *
 * Pilots reporting "the app froze yesterday" can zip this directory and
 * send it in — nothing inside should carry PII after redaction.
 *
 * Design ref: POS hardening epic (#479), issue #482.
 */

import * as path from "node:path";
import { mkdirSync } from "node:fs";
import pino, { type Logger, type LoggerOptions, type DestinationStream } from "pino";

// Values that must never appear in logs. Kept in one place so reviewers
// can scan before shipping a new field name that carries customer data.
// Pino redact uses fast-string-pattern matching — it does NOT descend into
// arbitrary depth, so deep-nested paths need to be listed explicitly.
const REDACT_PATHS: readonly string[] = [
  // HTTP auth headers (any shape)
  "req.headers.authorization",
  "req.headers.cookie",
  "headers.authorization",
  "headers.cookie",
  "authorization",
  // Customer identifiers
  "req.body.national_id",
  "req.body.customer_id",
  "req.body.phone",
  "body.national_id",
  "body.customer_id",
  "body.phone",
  "national_id",
  "customer_id",
  "phone",
  // Payment / discount inputs we don't need to retain
  "req.body.cash_tendered",
  "req.body.voucher_code",
  "voucher_code",
  "cash_tendered",
  // Secret-like wildcards (catches nested password / token fields)
  "*.password",
  "*.token",
  "*.refresh_token",
  "*.device_private_key",
];

const DEFAULT_FILENAME = "pos-desktop.log";
const DEFAULT_LEVEL = "info";

export interface LoggerDeps {
  /** Directory to write rotated files into. Normally `app.getPath('logs')`. */
  logsDir?: string;
  /** File stem — rotation suffixes (`.1`, `.2`, ...) are appended. */
  filename?: string;
  /** Override log level. Reads `LOG_LEVEL` env var, then falls back to "info". */
  level?: string;
  /** Pretty-print to stdout instead of JSON-to-file. Tests + dev only. */
  pretty?: boolean;
  /** Inject a custom destination stream (tests). Skips rotation setup. */
  destination?: DestinationStream;
  /** Release tag (typically `app.getVersion()`). Stamped on every log line
   * via pino's `base` so operators can cross-correlate a Sentry event
   * (which uses the same string via `initSentry`) with this build's logs. */
  release?: string;
  /** Deployment environment (`"production"`, `"development"`, ...). Same
   * correlation use-case as `release` — keep in lockstep with Sentry's
   * `environment` field. */
  environment?: string;
  /** Force a fresh instance even if a cached one already exists.
   *
   * The singleton semantics of `createLogger` mean a subsequent call
   * normally returns the first instance — useful so tests + app code
   * share one configuration. The exception is the boot path in
   * `main.ts`: the first call happens before `app.whenReady()` (so
   * `app.getPath('logs')` is not yet resolvable) and the second call
   * passes the real `logsDir`. Without `reinit: true`, that second
   * call is silently ignored and production file logs end up under
   * `process.cwd()` instead of the platform logs directory.
   */
  reinit?: boolean;
}

// Singleton — modules should `import { logger }` rather than call createLogger
// multiple times, so all rotation + redaction config stays centralised.
let _logger: Logger | null = null;

/**
 * Build a logger with the standard redact paths + rotation. Safe to call
 * more than once — subsequent calls return the existing singleton unless
 * a fresh destination is passed (used in tests to isolate writes).
 */
export function createLogger(deps: LoggerDeps = {}): Logger {
  if (_logger && !deps.destination && !deps.reinit) return _logger;

  const level = deps.level ?? process.env.LOG_LEVEL ?? DEFAULT_LEVEL;
  // Build the `base` map dynamically — only attach `release` / `environment`
  // when they were supplied. Lets tests and early-boot calls (before Electron
  // is ready) create a logger without fabricating placeholder values.
  const base: Record<string, unknown> = { app: "pos-desktop", pid: process.pid };
  if (deps.release) base.release = deps.release;
  if (deps.environment) base.environment = deps.environment;

  const opts: LoggerOptions = {
    level,
    redact: {
      paths: [...REDACT_PATHS],
      censor: "[REDACTED]",
      remove: false,
    },
    // ISO timestamps are easier to correlate with server logs than pino's
    // default epoch milliseconds.
    timestamp: pino.stdTimeFunctions.isoTime,
    // Standard structured fields for server-side ingestion.
    base,
  };

  let stream: DestinationStream;
  if (deps.destination) {
    stream = deps.destination;
  } else if (deps.pretty || process.env.NODE_ENV === "test") {
    // Dev / tests: raw JSON to stdout — avoids spinning up a worker thread
    // for rotation when we don't need persistence. `pino-pretty` would be
    // nicer in dev but is a dep we don't want in the shipped installer.
    stream = pino.destination(1);
  } else {
    const logsDir = deps.logsDir ?? process.cwd();
    mkdirSync(logsDir, { recursive: true });
    const logPath = path.join(logsDir, deps.filename ?? DEFAULT_FILENAME);
    // `pino-roll` ships as a Pino transport (async, worker-thread backed).
    // Using `pino.transport()` lets us configure it synchronously while
    // the actual setup + rotation happens off the main thread. 10MB/daily
    // with a 14-file ceiling fits a standard pharmacy day without
    // truncating and keeps disk usage bounded.
    stream = pino.transport({
      target: "pino-roll",
      options: {
        file: logPath,
        size: "10M",
        frequency: "daily",
        limit: { count: 14 },
        mkdir: true,
      },
    });
  }

  const instance = pino(opts, stream);
  if (!deps.destination) _logger = instance;
  return instance;
}

/**
 * Reset the singleton — tests only. Do NOT call from app code; the logger
 * is meant to live for the lifetime of the process so rotation stats are
 * stable.
 */
export function _resetLoggerForTests(): void {
  _logger = null;
}

/**
 * The configured redact paths (exported for test assertions; the list
 * must stay synced with the server-side `LOG_REDACT_FIELDS`).
 */
export const REDACT_PATHS_FOR_TESTS: readonly string[] = REDACT_PATHS;

/**
 * Lazy singleton — most call sites want `logger.info(...)` without
 * needing to pass a logs directory. Resolves the directory on first
 * access (requires Electron's `app` to be initialised).
 */
export function getLogger(): Logger {
  return createLogger();
}
