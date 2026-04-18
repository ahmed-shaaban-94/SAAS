import { randomUUID } from "node:crypto";
import type Database from "better-sqlite3";
import type { QueueRow, QueueStats, QueueStatus, Confirmation } from "../ipc/contracts";
import { nextAttemptAt } from "../sync/queue-state";

interface QueueRowRaw {
  local_id: string;
  client_txn_id: string;
  endpoint: string;
  status: string;
  confirmation: string;
  retry_count: number;
  last_error: string | null;
  next_attempt_at: string | null;
  signed_at: string;
  created_at: string;
  updated_at: string;
}

function toQueueRow(raw: QueueRowRaw): QueueRow {
  return {
    local_id: raw.local_id,
    client_txn_id: raw.client_txn_id,
    endpoint: raw.endpoint,
    status: raw.status as QueueStatus,
    confirmation: raw.confirmation as Confirmation,
    retry_count: raw.retry_count,
    last_error: raw.last_error,
    next_attempt_at: raw.next_attempt_at,
    signed_at: raw.signed_at,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

interface EnqueueInput {
  endpoint: string;
  payload: unknown;
  signed_at: string;
  auth_mode: "bearer" | "offline_grant";
  grant_id: string | null;
  device_signature: string;
}

/** Insert a new transaction into the queue with status=pending. */
export function enqueueTransaction(
  db: Database.Database,
  input: EnqueueInput,
): { local_id: string; client_txn_id: string } {
  const now = new Date().toISOString();
  const local_id = randomUUID();
  const client_txn_id = randomUUID();

  db.prepare(
    `INSERT INTO transactions_queue
       (local_id, client_txn_id, endpoint, payload, status, confirmation,
        signed_at, auth_mode, grant_id, device_signature,
        retry_count, next_attempt_at, created_at, updated_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
  ).run(
    local_id,
    client_txn_id,
    input.endpoint,
    JSON.stringify(input.payload),
    "pending",
    "provisional",
    input.signed_at,
    input.auth_mode,
    input.grant_id ?? null,
    input.device_signature,
    0,
    now,  // attempt immediately
    now,
    now,
  );

  return { local_id, client_txn_id };
}

/** All rows in pending status, oldest-first. */
export function getPendingQueue(db: Database.Database): QueueRow[] {
  const rows = db
    .prepare(
      `SELECT local_id, client_txn_id, endpoint, status, confirmation,
              retry_count, last_error, next_attempt_at, signed_at, created_at, updated_at
       FROM transactions_queue
       WHERE status = 'pending'
       ORDER BY created_at ASC`,
    )
    .all() as QueueRowRaw[];
  return rows.map(toQueueRow);
}

/** All rows in rejected status. */
export function getRejectedQueue(db: Database.Database): QueueRow[] {
  const rows = db
    .prepare(
      `SELECT local_id, client_txn_id, endpoint, status, confirmation,
              retry_count, last_error, next_attempt_at, signed_at, created_at, updated_at
       FROM transactions_queue
       WHERE status = 'rejected'
       ORDER BY created_at ASC`,
    )
    .all() as QueueRowRaw[];
  return rows.map(toQueueRow);
}

/** Count rows per status + last successful sync timestamp. */
export function getQueueStats(db: Database.Database): QueueStats {
  const counts = db
    .prepare(
      `SELECT
         SUM(CASE WHEN status='pending'  THEN 1 ELSE 0 END) AS pending,
         SUM(CASE WHEN status='syncing'  THEN 1 ELSE 0 END) AS syncing,
         SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected
       FROM transactions_queue`,
    )
    .get() as { pending: number | null; syncing: number | null; rejected: number | null };

  const lastSync = db
    .prepare(
      `SELECT MAX(updated_at) AS ts FROM transactions_queue WHERE status='synced'`,
    )
    .get() as { ts: string | null };

  const pending = counts.pending ?? 0;
  const syncing = counts.syncing ?? 0;
  const rejected = counts.rejected ?? 0;

  return {
    pending,
    syncing,
    rejected,
    unresolved: pending + syncing + rejected,
    last_sync_at: lastSync.ts,
  };
}

/** Transition pending → syncing. */
export function markSyncing(db: Database.Database, localId: string): void {
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE transactions_queue
     SET status='syncing', updated_at=?
     WHERE local_id=? AND status='pending'`,
  ).run(now, localId);
}

/** Transition syncing → synced; record server_id and server_response. */
export function markSynced(
  db: Database.Database,
  localId: string,
  serverId: number | null,
  serverResponse: string,
): void {
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE transactions_queue
     SET status='synced', confirmation='confirmed',
         server_id=?, server_response=?, updated_at=?
     WHERE local_id=?`,
  ).run(serverId ?? null, serverResponse, now, localId);
}

/** Transition syncing → rejected; increment retry_count. */
export function markRejected(
  db: Database.Database,
  localId: string,
  error: string,
): void {
  const now = new Date().toISOString();
  const row = db
    .prepare("SELECT retry_count FROM transactions_queue WHERE local_id=?")
    .get(localId) as { retry_count: number } | undefined;
  const retryCount = (row?.retry_count ?? 0) + 1;

  db.prepare(
    `UPDATE transactions_queue
     SET status='rejected', last_error=?, retry_count=?, next_attempt_at=?, updated_at=?
     WHERE local_id=?`,
  ).run(error, retryCount, nextAttemptAt(retryCount), now, localId);
}

/** Reconcile a rejected row. */
export function reconcileTransaction(
  db: Database.Database,
  localId: string,
  kind: "retry_override" | "record_loss" | "corrective_void",
  note: string,
  overrideCode: string | null,
): { status: QueueStatus; confirmation: Confirmation; reconciled_at: string } {
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE transactions_queue
     SET status='reconciled', confirmation='reconciled',
         reconciliation_kind=?, reconciliation_note=?,
         reconciliation_by=?, reconciled_at=?, updated_at=?
     WHERE local_id=?`,
  ).run(kind, note, overrideCode, now, now, localId);
  return { status: "reconciled", confirmation: "reconciled", reconciled_at: now };
}
