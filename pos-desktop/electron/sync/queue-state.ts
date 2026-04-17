/**
 * Queue state machine helpers — pure TypeScript, no DB dependency.
 *
 * The canonical five-state machine (§6.1) is the single source of truth
 * for every safety gate in the client (shift-close guard, auto-updater
 * gate, Sync Issues UI count). Every section that needs "is this work
 * unresolved?" MUST call `isUnresolved(status)` instead of re-implementing.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §6.1.
 */

import type { Confirmation, QueueStatus } from "../ipc/contracts";

/** Exhaustive list of queue states. */
export const QUEUE_STATES = [
  "pending",
  "syncing",
  "synced",
  "rejected",
  "reconciled",
] as const;

/** States that block shift-close, updater install, and new-day rollover. */
export const UNRESOLVED_STATES: ReadonlyArray<QueueStatus> = [
  "pending",
  "syncing",
  "rejected",
];

/**
 * The single unresolved predicate reused by every safety gate.
 *
 * `syncing` is treated as unresolved because its outcome is not yet known —
 * a 5xx or 4xx could still turn it into a `rejected` row after a naive gate
 * passed. Gates must never race past in-flight provisional work.
 */
export function isUnresolved(status: QueueStatus): boolean {
  return UNRESOLVED_STATES.includes(status);
}

/**
 * Derive the confirmation marker for a queue row.
 *
 *   pending | syncing | rejected   → "provisional"
 *   synced                          → "confirmed"
 *   reconciled                      → "reconciled"
 *
 * This mirrors the receipt marker printed at the top of every receipt.
 */
export function confirmationFor(status: QueueStatus): Confirmation {
  switch (status) {
    case "synced":
      return "confirmed";
    case "reconciled":
      return "reconciled";
    default:
      return "provisional";
  }
}

/**
 * Legal status transitions — used to validate that a state change is
 * allowed before persisting it. A transition not in this map should be
 * rejected with a bug report; the canonical machine has no other edges.
 */
const ALLOWED_TRANSITIONS: Record<QueueStatus, ReadonlyArray<QueueStatus>> = {
  pending: ["syncing", "rejected"],
  syncing: ["synced", "pending", "rejected"], // back to pending on 5xx / network
  rejected: ["reconciled", "syncing"], // user retries via override → syncing
  synced: [],
  reconciled: [],
};

export function isValidTransition(from: QueueStatus, to: QueueStatus): boolean {
  if (from === to) return true; // idempotent no-op
  return ALLOWED_TRANSITIONS[from].includes(to);
}

/**
 * Compute the next backoff attempt timestamp (§6.1 — exponential with cap).
 * Returns an ISO-8601 UTC string.
 *
 *   attempt=0 → +1s
 *   attempt=1 → +2s
 *   attempt=2 → +4s
 *   attempt=3 → +8s
 *   attempt=4 → +30s
 *   attempt=5 → +2m
 *   attempt≥6 → +5m (cap)
 */
export function nextAttemptAt(retryCount: number, now: Date = new Date()): string {
  const tableSeconds = [1, 2, 4, 8, 30, 120, 300];
  const delaySec = tableSeconds[Math.min(retryCount, tableSeconds.length - 1)];
  return new Date(now.getTime() + delaySec * 1000).toISOString();
}

/**
 * Aggregate a list of rows into the stats object surfaced at `sync.state()`
 * and `db.queue.stats()`. Keeps the aggregation in one place so the main
 * process doesn't need to repeat the SQL count queries.
 */
export function aggregateStats(rows: ReadonlyArray<{ status: QueueStatus }>): {
  pending: number;
  syncing: number;
  rejected: number;
  unresolved: number;
} {
  let pending = 0;
  let syncing = 0;
  let rejected = 0;
  for (const r of rows) {
    if (r.status === "pending") pending++;
    else if (r.status === "syncing") syncing++;
    else if (r.status === "rejected") rejected++;
  }
  return {
    pending,
    syncing,
    rejected,
    unresolved: pending + syncing + rejected,
  };
}
