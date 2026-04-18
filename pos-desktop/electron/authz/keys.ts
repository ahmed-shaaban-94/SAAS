/**
 * Ed25519 device keypair management.
 *
 * The device private key is stored in `secrets_dpapi` under "device_private_key".
 * For M3a, blobs are stored as plain base64url strings (no OS-level encryption).
 * Windows DPAPI wrapping is the M3b hardening task.
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
// secrets_dpapi table helpers (M3a: plain base64url, no OS encryption)
// ─────────────────────────────────────────────────────────────

function readSecret(db: Database.Database, key: string): string | null {
  const row = db
    .prepare("SELECT ciphertext FROM secrets_dpapi WHERE key=?")
    .get(key) as { ciphertext: Buffer } | undefined;
  if (!row) return null;
  return row.ciphertext.toString("utf8");
}

function writeSecret(db: Database.Database, key: string, value: string): void {
  const now = new Date().toISOString();
  db.prepare(
    `INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)
     ON CONFLICT(key) DO UPDATE SET ciphertext=excluded.ciphertext, updated_at=excluded.updated_at`,
  ).run(key, Buffer.from(value, "utf8"), now);
}

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
 * Returns a stable `sha256:<hex>` fingerprint for this device install.
 * Combines hostname + a persisted install UUID (created once in settings).
 * Full MAC/machineGuid/OS-serial is the M3b hardening task.
 */
export function computeDeviceFingerprint(db: Database.Database): string {
  let deviceUuid = getSetting(db, "device_uuid");
  if (!deviceUuid) {
    deviceUuid = randomUUID();
    setSetting(db, "device_uuid", deviceUuid);
  }
  const raw = `${hostname()}:${deviceUuid}`;
  const hash = createHash("sha256").update(raw, "utf8").digest("hex");
  return `sha256:${hash}`;
}
