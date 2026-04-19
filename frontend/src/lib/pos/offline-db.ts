/**
 * Adapter that routes POS data reads/writes to Electron IPC when running
 * inside the desktop app, or to the HTTP API when running in a browser.
 *
 * The goal: renderer components should NOT branch on `hasElectron()`
 * themselves — they call the adapter and get the right implementation.
 *
 * Phase-1 scope covers reads the existing web POS already does
 * (product search, stock lookup, shift state, queue stats). Mutations
 * (commit, void, shift-close) still go through the existing SWR hooks
 * against the HTTP API — Electron wraps them with idempotency + device
 * signing at the HTTP layer via the main process's `net` forwarder
 * (landing in M3).
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

import { ApiError, fetchAPI } from "../api-client";
import { db, hasElectron } from "./ipc";
import type { Confirmation, QueueRow, QueueStatus } from "./ipc";

export type ReconcileKind = "retry_override" | "record_loss" | "corrective_void";

export interface ReconcileResult {
  status: QueueStatus;
  confirmation: Confirmation;
  reconciled_at: string;
}

export interface PosProductResult {
  drug_code: string;
  drug_name: string;
  drug_brand: string | null;
  unit_price: string;
  is_controlled: boolean;
  requires_pharmacist: boolean;
}

export async function searchProducts(
  q: string,
  limit = 20,
): Promise<PosProductResult[]> {
  if (hasElectron()) {
    const rows = await db.products.search(q, limit);
    return rows.map((r) => ({
      drug_code: r.drug_code,
      drug_name: r.drug_name,
      drug_brand: r.drug_brand,
      unit_price: r.unit_price,
      is_controlled: r.is_controlled,
      requires_pharmacist: r.requires_pharmacist,
    }));
  }
  const qs = new URLSearchParams({ q, limit: String(limit) }).toString();
  return fetchAPI<PosProductResult[]>(`/pos/products/search?${qs}`);
}

export async function getProductByCode(
  drugCode: string,
): Promise<PosProductResult | null> {
  if (hasElectron()) {
    const p = await db.products.byCode(drugCode);
    if (!p) return null;
    return {
      drug_code: p.drug_code,
      drug_name: p.drug_name,
      drug_brand: p.drug_brand,
      unit_price: p.unit_price,
      is_controlled: p.is_controlled,
      requires_pharmacist: p.requires_pharmacist,
    };
  }
  try {
    return await fetchAPI<PosProductResult>(
      `/pos/products/${encodeURIComponent(drugCode)}`,
    );
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export interface PosQueueStats {
  pending: number;
  syncing: number;
  rejected: number;
  unresolved: number;
  last_sync_at: string | null;
}

/**
 * Returns queue stats when running in Electron; in the browser returns an
 * empty/"everything synced" snapshot since the web POS has no local queue.
 * Components that render the offline banner should treat zeros as "no
 * unresolved work" regardless of source.
 */
export async function getQueueStats(): Promise<PosQueueStats> {
  if (hasElectron()) {
    return db.queue.stats();
  }
  return { pending: 0, syncing: 0, rejected: 0, unresolved: 0, last_sync_at: null };
}

/**
 * Returns rejected queue rows awaiting reconciliation when running in
 * Electron; in the browser returns an empty array — the web POS has no
 * local queue and therefore nothing to reconcile.
 */
export async function getRejectedQueue(): Promise<QueueRow[]> {
  if (hasElectron()) {
    return db.queue.rejected();
  }
  return [];
}

/**
 * Resolves a rejected queue row via one of the three reconciliation kinds:
 * `retry_override` (retry with a scrypt-verified manager override code),
 * `record_loss` (abandon as a loss), or `corrective_void` (issue a
 * compensating void for a later-rejected already-synced txn).
 *
 * Only valid inside Electron — callers must guard with `hasElectron()`.
 */
export async function reconcileQueue(
  localId: string,
  kind: ReconcileKind,
  note: string,
  overrideCode: string | null,
): Promise<ReconcileResult> {
  if (!hasElectron()) {
    throw new Error("Not available in browser");
  }
  return db.queue.reconcile(localId, kind, note, overrideCode);
}
