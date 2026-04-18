/**
 * Offline grant management (§8.8).
 *
 * M3a scope: storage/retrieval + grant-state detection.
 * Grant issuance is triggered by server at shift-open; the client stores the
 * signed envelope in secrets_dpapi and uses it while offline.
 *
 * Override-code consumption (scrypt verification) and grant signature
 * verification with tenant public key are in the M3b hardening scope.
 */

import type Database from "better-sqlite3";
import { getSetting } from "../db/settings";

export type GrantState = "online" | "offline_valid" | "offline_expired" | "revoked";

interface GrantPayload {
  grant_id: string;
  offline_expires_at: string;
  shift_id: number;
  terminal_id: number;
  tenant_id: number;
  device_fingerprint: string;
}

export interface OfflineGrantEnvelope {
  payload: GrantPayload;
  signature_ed25519: string;
  key_id: string;
}

// ─────────────────────────────────────────────────────────────
// Storage helpers
// ─────────────────────────────────────────────────────────────

function readSecret(db: Database.Database, key: string): string | null {
  const row = db
    .prepare("SELECT ciphertext FROM secrets_dpapi WHERE key=?")
    .get(key) as { ciphertext: Buffer } | undefined;
  return row ? row.ciphertext.toString("utf8") : null;
}

function writeSecret(db: Database.Database, key: string, value: string): void {
  const now = new Date().toISOString();
  db.prepare(
    `INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)
     ON CONFLICT(key) DO UPDATE SET ciphertext=excluded.ciphertext, updated_at=excluded.updated_at`,
  ).run(key, Buffer.from(value, "utf8"), now);
}

// ─────────────────────────────────────────────────────────────
// Grant access
// ─────────────────────────────────────────────────────────────

export function currentGrant(db: Database.Database): OfflineGrantEnvelope | null {
  const blob = readSecret(db, "offline_grant");
  if (!blob) return null;
  try {
    return JSON.parse(blob) as OfflineGrantEnvelope;
  } catch {
    return null;
  }
}

export function saveGrant(db: Database.Database, envelope: OfflineGrantEnvelope): void {
  writeSecret(db, "offline_grant", JSON.stringify(envelope));
}

export function clearGrant(db: Database.Database): void {
  db.prepare("DELETE FROM secrets_dpapi WHERE key='offline_grant'").run();
}

export function grantState(db: Database.Database): GrantState {
  const jwt = getSetting(db, "jwt");
  if (jwt) return "online";

  const grant = currentGrant(db);
  if (!grant) return "offline_expired";

  const expiresAt = Date.parse(grant.payload.offline_expires_at);
  if (Number.isNaN(expiresAt)) return "offline_expired";
  if (Date.now() > expiresAt) return "offline_expired";

  return "offline_valid";
}

// ─────────────────────────────────────────────────────────────
// Override code consumption (M3b: scrypt verification)
// ─────────────────────────────────────────────────────────────

export function consumeOverrideCode(
  _db: Database.Database,
  _code: string,
): { ok: false; reason: string } {
  // Scrypt verification + device-signed override token minting is M3b.
  return { ok: false, reason: "override_codes_not_yet_implemented" };
}
