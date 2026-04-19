/**
 * Queue drain worker — push pending transactions to the server (§6.1).
 *
 * Push behaviour:
 *   • Claims one row at a time (status pending → syncing) to isolate failures.
 *   • 2xx → synced + confirmed; 409 replay → treated as 2xx.
 *   • 4xx non-409 → rejected (server decision); surfaces in Sync Issues.
 *   • 5xx / network error → back to pending with exponential backoff.
 *   • Row older than PROVISIONAL_TTL_HOURS → expired → rejected without push.
 *
 * The stored device_signature + signed_at are replayed verbatim (§8.9 crash-safe
 * replay: the original timestamp stays inside the server's idempotency window).
 */

import { createHash } from "node:crypto";
import type Database from "better-sqlite3";
import { nextAttemptAt } from "./queue-state";
import { markSyncing, markSynced, markRejected } from "../db/queue";
import { getSetting } from "../db/settings";
import {
  computeDeviceFingerprint,
  computeDeviceFingerprintV2,
  FingerprintMismatchError,
  getFingerprintV2Components,
  loadPrivateKey,
  signCanonical,
} from "../authz/keys";

const PROVISIONAL_TTL_HOURS = 72;
const MAX_ROWS_PER_CYCLE = 20;

interface QueueRowFull {
  local_id: string;
  client_txn_id: string;
  endpoint: string;
  payload: string;
  status: string;
  retry_count: number;
  signed_at: string;
  device_signature: string;
  auth_mode: string;
  next_attempt_at: string | null;
  created_at: string;
}

export function getBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_URL ??
    process.env.INTERNAL_API_URL ??
    "https://smartdatapulse.tech"
  );
}

function claimNextRow(db: Database.Database): QueueRowFull | null {
  return db
    .prepare(
      `SELECT local_id, client_txn_id, endpoint, payload, status, retry_count,
              signed_at, device_signature, auth_mode, next_attempt_at, created_at
       FROM transactions_queue
       WHERE status = 'pending'
         AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
       ORDER BY created_at ASC
       LIMIT 1`,
    )
    .get(new Date().toISOString()) as QueueRowFull | null;
}

function isExpired(createdAt: string): boolean {
  const created = Date.parse(createdAt);
  if (Number.isNaN(created)) return true;
  return Date.now() - created > PROVISIONAL_TTL_HOURS * 60 * 60 * 1000;
}

function backoffRow(
  db: Database.Database,
  localId: string,
  error: string,
  currentRetryCount: number,
): void {
  const now = new Date().toISOString();
  const nextCount = currentRetryCount + 1;
  db.prepare(
    `UPDATE transactions_queue
     SET status='pending', last_error=?, retry_count=?, next_attempt_at=?, updated_at=?
     WHERE local_id=?`,
  ).run(error, nextCount, nextAttemptAt(nextCount), now, localId);
}

function expireRow(db: Database.Database, localId: string): void {
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE transactions_queue
     SET status='rejected', last_error='provisional_expired', updated_at=?
     WHERE local_id=?`,
  ).run(now, localId);
}

async function pushRow(
  db: Database.Database,
  row: QueueRowFull,
): Promise<"synced" | "rejected" | "backoff"> {
  const jwt = getSetting(db, "jwt");
  const terminalId = getSetting(db, "terminal_id");
  const fingerprint = computeDeviceFingerprint(db);

  // Best-effort v2 fingerprint. Hardware-change mismatch rejects pushes
  // immediately (rather than silently submitting with the old digest) so
  // the admin sees a Sync Issue they can triage.
  let fingerprintV2: string | null = null;
  try {
    if (getFingerprintV2Components().reliable) {
      fingerprintV2 = computeDeviceFingerprintV2(db);
    }
  } catch (err) {
    if (err instanceof FingerprintMismatchError) {
      markRejected(
        db,
        row.local_id,
        `fingerprint_v2_mismatch: ${err.stored.slice(0, 16)} -> ${err.current.slice(0, 16)}`,
      );
      return "rejected";
    }
    throw err;
  }

  if (!jwt || !terminalId) return "backoff";

  // Derive the URL path from the stored endpoint ("POST /api/v1/...")
  const path = row.endpoint.replace(/^[A-Z]+\s+/, "");
  const baseUrl = getBaseUrl();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${jwt}`,
    "Idempotency-Key": row.client_txn_id,
    "X-Terminal-Id": terminalId,
    "X-Device-Fingerprint": fingerprint,
    "X-Signed-At": row.signed_at,
    "X-Terminal-Token": row.device_signature,
    ...(fingerprintV2 ? { "X-Device-Fingerprint-V2": fingerprintV2 } : {}),
  };

  let res: Response;
  try {
    res = await fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers,
      body: row.payload,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    backoffRow(db, row.local_id, `network: ${msg.slice(0, 200)}`, row.retry_count);
    return "backoff";
  }

  if (res.ok || res.status === 409) {
    const responseText = await res.text().catch(() => "{}");
    let serverId: number | null = null;
    try {
      const json = JSON.parse(responseText) as { transaction_id?: number };
      serverId = json.transaction_id ?? null;
    } catch { /* non-JSON response is fine */ }
    markSynced(db, row.local_id, serverId, responseText);
    return "synced";
  }

  if (res.status >= 400 && res.status < 500) {
    const errorText = await res.text().catch(() => "");
    markRejected(db, row.local_id, `HTTP ${res.status}: ${errorText.slice(0, 200)}`);
    return "rejected";
  }

  // 5xx or unexpected status → backoff
  const errorText = await res.text().catch(() => "");
  backoffRow(
    db,
    row.local_id,
    `HTTP ${res.status}: ${errorText.slice(0, 200)}`,
    row.retry_count,
  );
  return "backoff";
}

/**
 * Build the canonical string + sign it for a given enqueue operation.
 * Called by the IPC enqueue handler so the signature is stored at enqueue time.
 */
export function buildEnqueueSignature(
  db: Database.Database,
  opts: {
    path: string;
    clientTxnId: string;
    bodyJson: string;
    signedAt: string;
  },
): string {
  const terminalId = getSetting(db, "terminal_id") ?? "0";
  const privateKey = loadPrivateKey(db);

  // If device is not registered yet, return a placeholder (server will reject = Sync Issues).
  if (!privateKey) return "unregistered";

  const bodyHash = createHash("sha256").update(opts.bodyJson, "utf8").digest("hex");
  const canonical = [
    "POST",
    opts.path,
    opts.clientTxnId,
    terminalId,
    bodyHash,
    opts.signedAt,
  ].join("\n");

  return signCanonical(privateKey, canonical);
}

export async function drainQueue(db: Database.Database): Promise<{ pushed: number; rejected: number }> {
  let pushed = 0;
  let rejected = 0;

  for (let i = 0; i < MAX_ROWS_PER_CYCLE; i++) {
    const row = claimNextRow(db);
    if (!row) break;

    if (isExpired(row.created_at)) {
      expireRow(db, row.local_id);
      rejected++;
      continue;
    }

    markSyncing(db, row.local_id);

    const outcome = await pushRow(db, row);
    if (outcome === "synced") pushed++;
    else if (outcome === "rejected") rejected++;
    // "backoff" is neither pushed nor rejected — row stays in queue
  }

  return { pushed, rejected };
}
