/**
 * Secure storage for POS secrets (device keys, offline grant envelope, override
 * code scrypt material, JWT/refresh tokens).
 *
 * Wraps Electron's `safeStorage` API which hooks into:
 *   - Windows: DPAPI (user-scoped encryption)
 *   - macOS:   Keychain
 *   - Linux:   libsecret (GNOME Keyring / KWallet); unavailable in minimal envs
 *
 * Storage envelope (stored as the raw bytes of `secrets_dpapi.ciphertext`):
 *
 *   byte[0]    = version tag
 *                  0x01 -> safeStorage-wrapped ciphertext follows
 *                  0x00 -> plain UTF-8 bytes follow (fallback for Linux w/o libsecret)
 *   byte[1..]  = payload (encrypted blob for v1, raw UTF-8 for v0)
 *
 * Legacy pre-versioning entries were written as raw UTF-8 bytes with no
 * version prefix. We detect those by inspecting the first byte — any prefix
 * that is not 0x00 or 0x01 is treated as legacy and the whole blob is
 * decoded as UTF-8. This is safe because neither 0x00 nor 0x01 appears as
 * the first byte of any string we've ever stored (all existing payloads
 * start with printable ASCII: base64url chars or '{' for JSON).
 *
 * This dual-format is load-bearing for forward/backward compatibility:
 *   - Existing deployments with plain entries keep working (read unchanged)
 *   - New writes use v1 immediately
 *   - Boot-time migration (upgradeSecretsToEncrypted) rewrites old rows in-place
 *   - Rolling back to an older app version re-issues keys/grant on next online tick
 *
 * Design ref: §8.9 (M3b hardening).
 */

import { safeStorage as electronSafeStorage } from "electron";
import type Database from "better-sqlite3";

export const SECURE_STORE_VERSION_V1 = 0x01 as const;
export const SECURE_STORE_VERSION_V0 = 0x00 as const;

/**
 * Subset of Electron's safeStorage API we use. Declared locally so tests can
 * inject a mock without pulling in the real Electron module.
 */
export interface SafeStorageLike {
  isEncryptionAvailable(): boolean;
  encryptString(plainText: string): Buffer;
  decryptString(encrypted: Buffer): string;
}

export interface SecureStoreDeps {
  /** Injected for testability — defaults to the real Electron safeStorage. */
  safeStorage?: SafeStorageLike;
  /** Injected for testability — defaults to console.warn. */
  log?: (msg: string) => void;
}

function resolveSafeStorage(deps: SecureStoreDeps): SafeStorageLike {
  return deps.safeStorage ?? (electronSafeStorage as unknown as SafeStorageLike);
}

function resolveLogger(deps: SecureStoreDeps): (msg: string) => void {
  return deps.log ?? ((msg: string) => console.warn(msg));
}

/**
 * Returns true if the platform exposes a working OS-level secret store.
 * Swallows any throw from safeStorage (can happen during very early boot).
 */
export function isEncryptionAvailable(deps: SecureStoreDeps = {}): boolean {
  const api = resolveSafeStorage(deps);
  try {
    return api.isEncryptionAvailable();
  } catch {
    return false;
  }
}

/**
 * Fetch and decrypt a secret by key. Returns null if the row does not exist.
 *
 * Decryption failures (e.g. DPAPI blob written by a different user account,
 * corrupt row) throw so the caller can decide how to recover — we never
 * silently return a wrong value.
 */
export function readSecret(
  db: Database.Database,
  key: string,
  deps: SecureStoreDeps = {},
): string | null {
  const row = db
    .prepare("SELECT ciphertext FROM secrets_dpapi WHERE key=?")
    .get(key) as { ciphertext: Buffer } | undefined;
  if (!row) return null;

  const blob = row.ciphertext;
  if (blob.length === 0) return "";

  const version = blob[0];
  if (version === SECURE_STORE_VERSION_V1) {
    const api = resolveSafeStorage(deps);
    return api.decryptString(blob.subarray(1));
  }
  if (version === SECURE_STORE_VERSION_V0) {
    return blob.subarray(1).toString("utf8");
  }
  // Legacy: pre-versioning entry. Treat whole blob as UTF-8.
  return blob.toString("utf8");
}

/**
 * Encrypt (if available) and store a secret under `key`.
 *
 * When safeStorage is unavailable (Linux w/o libsecret, CI sandboxes) we fall
 * back to v0 (plain UTF-8 with a version prefix) and log a loud warning. The
 * DB still carries the version tag so a later upgrade — once encryption
 * becomes available — can rewrite the row.
 */
export function writeSecret(
  db: Database.Database,
  key: string,
  value: string,
  deps: SecureStoreDeps = {},
): void {
  const api = resolveSafeStorage(deps);
  const log = resolveLogger(deps);

  let blob: Buffer;
  let available = false;
  try {
    available = api.isEncryptionAvailable();
  } catch {
    available = false;
  }

  if (available) {
    const encrypted = api.encryptString(value);
    blob = Buffer.concat([Buffer.from([SECURE_STORE_VERSION_V1]), encrypted]);
  } else {
    log(
      "[secure-store] OS encryption unavailable — falling back to plain v0 storage. " +
        "On Linux, install libsecret (libsecret-1-dev / GNOME Keyring / KWallet) to enable.",
    );
    blob = Buffer.concat([Buffer.from([SECURE_STORE_VERSION_V0]), Buffer.from(value, "utf8")]);
  }

  const now = new Date().toISOString();
  db.prepare(
    `INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)
     ON CONFLICT(key) DO UPDATE SET ciphertext=excluded.ciphertext, updated_at=excluded.updated_at`,
  ).run(key, blob, now);
}

/** Delete a secret row. No-op if the row does not exist. */
export function deleteSecret(db: Database.Database, key: string): void {
  db.prepare("DELETE FROM secrets_dpapi WHERE key=?").run(key);
}

/**
 * One-shot migration: find all non-v1 entries, re-encrypt them with v1, persist.
 *
 * Safe to call on every startup — v1 entries are skipped so repeated calls
 * are idempotent and cheap. Returns count of entries upgraded.
 *
 * If safeStorage is unavailable on this platform, this is a no-op (returns 0)
 * — there's no point rewriting v0 as v0. A later boot on a box where
 * encryption is available will do the upgrade.
 */
export function upgradeSecretsToEncrypted(
  db: Database.Database,
  deps: SecureStoreDeps = {},
): number {
  const api = resolveSafeStorage(deps);
  let available = false;
  try {
    available = api.isEncryptionAvailable();
  } catch {
    available = false;
  }
  if (!available) return 0;

  const rows = db
    .prepare("SELECT key, ciphertext FROM secrets_dpapi")
    .all() as { key: string; ciphertext: Buffer }[];

  let upgraded = 0;
  const updateStmt = db.prepare(
    "UPDATE secrets_dpapi SET ciphertext=?, updated_at=? WHERE key=?",
  );

  for (const row of rows) {
    const blob = row.ciphertext;
    if (blob.length > 0 && blob[0] === SECURE_STORE_VERSION_V1) continue;

    let plain: string;
    if (blob.length > 0 && blob[0] === SECURE_STORE_VERSION_V0) {
      plain = blob.subarray(1).toString("utf8");
    } else {
      // Legacy pre-versioning entry: whole blob is UTF-8.
      plain = blob.toString("utf8");
    }

    const encrypted = api.encryptString(plain);
    const newBlob = Buffer.concat([Buffer.from([SECURE_STORE_VERSION_V1]), encrypted]);
    updateStmt.run(newBlob, new Date().toISOString(), row.key);
    upgraded++;
  }

  return upgraded;
}
