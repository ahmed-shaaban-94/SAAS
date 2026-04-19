/**
 * Ed25519 device keypair management.
 *
 * The device private key is stored in `secrets_dpapi` under "device_private_key".
 * Storage goes through `./secure-store`, which wraps Electron `safeStorage`
 * (DPAPI on Windows, Keychain on macOS, libsecret on Linux) so the SQLite
 * file can't be lifted and read offline — M3b hardening (§8.9).
 *
 * All raw keys are 32 bytes, transmitted as base64url (no padding) to match
 * the server's `_pad_b64url` helper in `pos/devices.py`.
 *
 * Design ref: §8.9
 */

import {
  createHash,
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
  randomUUID,
  sign as nodeSign,
  verify as nodeVerify,
} from "node:crypto";
import { hostname } from "node:os";
import type Database from "better-sqlite3";
import { getSetting, setSetting } from "../db/settings";
import { readSecret, writeSecret } from "./secure-store";
import { computeFingerprintV2, type FingerprintResult } from "./fingerprint";

export interface Keypair {
  publicKey: string;  // base64url, raw 32-byte Ed25519
  privateKey: string; // base64url, raw 32-byte Ed25519
}

// DER header bytes for wrapping a raw 32-byte Ed25519 private key in PKCS8.
// Sequence(version=0, AlgorithmIdentifier(id-Ed25519), OctetString(OctetString(key)))
const PKCS8_ED25519_HEADER = Buffer.from("302e020100300506032b657004220420", "hex");

// DER header bytes for wrapping a raw 32-byte Ed25519 public key in SPKI.
// Sequence(AlgorithmIdentifier(id-Ed25519), BitString(0-unused, key))
const SPKI_ED25519_HEADER = Buffer.from("302a300506032b6570032100", "hex");

// ─────────────────────────────────────────────────────────────
// Keypair generation
// ─────────────────────────────────────────────────────────────

export function generateKeypair(): Keypair {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const pubRaw = Buffer.from(publicKey.export({ type: "spki", format: "der" })).slice(-32);
  const privRaw = Buffer.from(privateKey.export({ type: "pkcs8", format: "der" })).slice(-32);
  return {
    publicKey: pubRaw.toString("base64url"),
    privateKey: privRaw.toString("base64url"),
  };
}

// ─────────────────────────────────────────────────────────────
// Signing
// ─────────────────────────────────────────────────────────────

/**
 * Sign the canonical UTF-8 string with the device Ed25519 private key.
 *
 * The canonical string is NOT pre-hashed — `devices.py::device_token_verifier`
 * passes the raw canonical bytes directly to Ed25519PublicKey.verify().
 * Do NOT SHA256 the canonical string before signing here.
 */
export function signCanonical(privateKeyB64: string, canonical: string): string {
  const privRaw = Buffer.from(privateKeyB64, "base64url");
  const pkcs8 = Buffer.concat([PKCS8_ED25519_HEADER, privRaw]);
  const keyObject = createPrivateKey({ key: pkcs8, format: "der", type: "pkcs8" });
  return nodeSign(null, Buffer.from(canonical, "utf8"), keyObject).toString("base64url");
}

/**
 * Verify an Ed25519 signature (for testing and grant verification).
 */
export function verifySignature(publicKeyB64: string, data: Buffer, signatureB64: string): boolean {
  try {
    const pubRaw = Buffer.from(publicKeyB64, "base64url");
    const spki = Buffer.concat([SPKI_ED25519_HEADER, pubRaw]);
    const keyObject = createPublicKey({ key: spki, format: "der", type: "spki" });
    return nodeVerify(null, data, keyObject, Buffer.from(signatureB64, "base64url"));
  } catch {
    return false;
  }
}

/**
 * Build the canonical string for request signing (§8.9.2).
 * Must match `devices.py::device_token_verifier` exactly.
 */
export function buildCanonicalString(opts: {
  method: string;
  path: string;
  idempotencyKey: string;
  terminalId: string;
  bodyJson: string;
  signedAt: string;
}): string {
  const bodyHash = createHash("sha256").update(opts.bodyJson, "utf8").digest("hex");
  return [
    opts.method.toUpperCase(),
    opts.path,
    opts.idempotencyKey,
    opts.terminalId,
    bodyHash,
    opts.signedAt,
  ].join("\n");
}

// ─────────────────────────────────────────────────────────────
// Persistence (via secure-store: OS-encrypted where available, plain fallback
// otherwise — see ./secure-store for the envelope format)
// ─────────────────────────────────────────────────────────────

export function loadPrivateKey(db: Database.Database): string | null {
  return readSecret(db, "device_private_key");
}

export function loadPublicKey(db: Database.Database): string | null {
  return readSecret(db, "device_public_key");
}

export function saveKeypair(db: Database.Database, kp: Keypair): void {
  writeSecret(db, "device_private_key", kp.privateKey);
  writeSecret(db, "device_public_key", kp.publicKey);
}

export function getOrCreateKeypair(db: Database.Database): Keypair {
  const priv = loadPrivateKey(db);
  const pub = loadPublicKey(db);
  if (priv && pub) return { privateKey: priv, publicKey: pub };
  const kp = generateKeypair();
  saveKeypair(db, kp);
  return kp;
}

// ─────────────────────────────────────────────────────────────
// Device fingerprint — stable per machine+install
// ─────────────────────────────────────────────────────────────

/**
 * Legacy v1 fingerprint (install-specific): `sha256:<hex>` of
 * hostname + persisted UUID. Kept for existing registered devices during
 * the v2 deprecation window; will be removed once all pilots migrate.
 *
 * Still used by `registerDevice` for backward compatibility — new rows
 * carry both v1 and v2. The server stores both and accepts either header
 * during the window (see `migrations/093_add_pos_device_fingerprint_v2.sql`
 * and `src/datapulse/pos/devices.py`).
 */
export function computeDeviceFingerprintV1(db: Database.Database): string {
  let deviceUuid = getSetting(db, "device_uuid");
  if (!deviceUuid) {
    deviceUuid = randomUUID();
    setSetting(db, "device_uuid", deviceUuid);
  }
  const raw = `${hostname()}:${deviceUuid}`;
  const hash = createHash("sha256").update(raw, "utf8").digest("hex");
  return `sha256:${hash}`;
}

/**
 * v2 fingerprint: OS-level identifiers (machineId + MAC + hostname).
 * Delegates the actual hashing to `./fingerprint.ts::computeFingerprintV2`
 * — this wrapper just persists the result on first call and detects
 * hardware-change mismatches on subsequent calls.
 *
 * Returns the `sha256v2:<hex>` digest. Use `getFingerprintV2Components()`
 * if you need the unhashed components for diagnostics.
 *
 * Throws `FingerprintMismatchError` if the persisted v2 doesn't match the
 * current hardware — caller should refuse to use the device key and
 * prompt the admin to re-register, per #480 acceptance criteria.
 */
export class FingerprintMismatchError extends Error {
  constructor(
    public readonly stored: string,
    public readonly current: string,
  ) {
    super("device fingerprint v2 changed — hardware has changed or been tampered with");
    this.name = "FingerprintMismatchError";
  }
}

export function computeDeviceFingerprintV2(
  db: Database.Database,
  deps?: Parameters<typeof computeFingerprintV2>[0],
): string {
  const result = computeFingerprintV2(deps);
  const stored = getSetting(db, "device_fingerprint_v2");

  if (!stored) {
    // First boot on v2 — persist so subsequent boots can detect changes.
    setSetting(db, "device_fingerprint_v2", result.digest);
    return result.digest;
  }

  if (stored !== result.digest) {
    throw new FingerprintMismatchError(stored, result.digest);
  }
  return result.digest;
}

/**
 * Expose the raw fingerprint components (hostname, machineId, primaryMac,
 * reliable flag). Does NOT persist — use `computeDeviceFingerprintV2` for
 * the persistent flow. Callers should only read components for diagnostic
 * logging; never serialise them verbatim to disk or the wire.
 */
export function getFingerprintV2Components(
  deps?: Parameters<typeof computeFingerprintV2>[0],
): FingerprintResult {
  return computeFingerprintV2(deps);
}

/**
 * Default fingerprint used by `sync/push.ts` for the `X-Device-Fingerprint`
 * header. Kept as an alias for v1 to preserve wire compatibility with the
 * current server until the deprecation window closes. New requests also
 * include an `X-Device-Fingerprint-V2` header (see `push.ts`).
 */
export const computeDeviceFingerprint = computeDeviceFingerprintV1;
