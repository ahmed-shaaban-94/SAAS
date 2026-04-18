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

import { scryptSync, timingSafeEqual } from "node:crypto";
import type Database from "better-sqlite3";
import { getSetting } from "../db/settings";

export type GrantState = "online" | "offline_valid" | "offline_expired" | "revoked";

interface OverrideCodeEntry {
  code_id: string;
  salt: string;              // base64url, no padding — matches grants.py _pad_b64url output
  hash: string;              // base64url, no padding
  issued_to_staff_id: string;
}

interface GrantPayload {
  grant_id: string;
  offline_expires_at: string;
  shift_id: number;
  terminal_id: number;
  tenant_id: number;
  device_fingerprint: string;
  override_codes?: OverrideCodeEntry[];
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
  db: Database.Database,
  code: string,
): { ok: true; code_id: string; issued_to_staff_id: string } | { ok: false; reason: string } {
  const grant = currentGrant(db);
  if (!grant) return { ok: false, reason: "no_grant" };

  const entries = grant.payload.override_codes ?? [];
  if (entries.length === 0) return { ok: false, reason: "no_override_codes_in_grant" };

  const codeInput = Buffer.from(code, "utf8");

  for (const entry of entries) {
    const salt = Buffer.from(entry.salt, "base64url");
    const expectedHash = Buffer.from(entry.hash, "base64url");

    let actualHash: Buffer;
    try {
      // N=2^14=16384, r=8, p=1 — must match server grants.py SCRYPT_* constants.
      actualHash = scryptSync(codeInput, salt, 32, {
        N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024,
      });
    } catch {
      continue;
    }

    if (!timingSafeEqual(actualHash, expectedHash)) continue;

    // Matching code — check for prior consumption (atomic via PRIMARY KEY constraint).
    const already = db
      .prepare("SELECT 1 FROM consumed_override_codes WHERE grant_id=? AND code_id=?")
      .get(grant.payload.grant_id, entry.code_id);
    if (already) return { ok: false, reason: "already_consumed" };

    db.prepare(
      "INSERT INTO consumed_override_codes(grant_id, code_id) VALUES(?,?)",
    ).run(grant.payload.grant_id, entry.code_id);

    db.prepare(
      "INSERT INTO audit_log(event, payload, created_at) VALUES(?,?,?)",
    ).run(
      "override.consumed",
      JSON.stringify({
        grant_id: grant.payload.grant_id,
        code_id: entry.code_id,
        staff_id: entry.issued_to_staff_id,
      }),
      new Date().toISOString(),
    );

    return { ok: true, code_id: entry.code_id, issued_to_staff_id: entry.issued_to_staff_id };
  }

  return { ok: false, reason: "invalid_code" };
}
