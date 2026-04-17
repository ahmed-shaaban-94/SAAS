/**
 * Canonical signed-envelope digest (§8.9.2).
 *
 * Every mutating POS request is signed with the device's Ed25519 private key.
 * The signed payload is a SHA-256 over a canonical string built from:
 *
 *   method \n path \n idempotency_key \n terminal_id \n body_sha256 \n signed_at
 *
 * The digest formula is shared between main-process signing and server-side
 * verification (in `src/datapulse/pos/devices.py::device_token_verifier`).
 * Both sides MUST build the digest identically, including the exact
 * newline-as-separator and the exact `X-Signed-At` string (not re-parsed from
 * the header — the original value is part of the signature).
 *
 * This module uses only Node's built-in `crypto` — no native deps.
 */

import { createHash } from "node:crypto";

/** Canonical-digest version. Bump when the formula changes. */
export const ENVELOPE_VERSION = 1;

export interface EnvelopeInput {
  method: string; // uppercase HTTP verb
  path: string; // URL path only (e.g. "/api/v1/pos/transactions/commit")
  idempotencyKey: string;
  terminalId: number;
  body: Uint8Array | string; // raw request body; empty string for GET
  signedAt: string; // RFC-3339 / ISO-8601 UTC
}

/**
 * Build the canonical digest over which the device private key signs.
 * Returns raw 32-byte SHA-256 output (hex-encode or base64 at the caller).
 */
export function buildCanonicalDigest(input: EnvelopeInput): Buffer {
  const bodyBuf =
    typeof input.body === "string"
      ? Buffer.from(input.body, "utf8")
      : Buffer.from(input.body);
  const bodySha = createHash("sha256").update(bodyBuf).digest("hex");

  const canonical = [
    input.method.toUpperCase(),
    input.path,
    input.idempotencyKey,
    String(input.terminalId),
    bodySha,
    input.signedAt,
  ].join("\n");

  return createHash("sha256").update(canonical, "utf8").digest();
}

/**
 * Convenience: return the canonical string itself (for logging / diffing
 * when debugging signature failures). Never log this value in production
 * — it contains the idempotency key.
 */
export function canonicalString(input: EnvelopeInput): string {
  const bodyBuf =
    typeof input.body === "string"
      ? Buffer.from(input.body, "utf8")
      : Buffer.from(input.body);
  const bodySha = createHash("sha256").update(bodyBuf).digest("hex");
  return [
    input.method.toUpperCase(),
    input.path,
    input.idempotencyKey,
    String(input.terminalId),
    bodySha,
    input.signedAt,
  ].join("\n");
}

/**
 * Validate that a signed-at timestamp is parseable + not in the impossible
 * future. Server-side also checks it against the grant window; that check
 * is NOT duplicated here — it requires the grant payload.
 *
 * @param signedAt  ISO-8601 string
 * @param maxSkewMs allowed clock drift ahead of "now" (default 2 min)
 */
export function signedAtLooksFresh(
  signedAt: string,
  now: Date = new Date(),
  maxSkewMs: number = 2 * 60 * 1000,
): boolean {
  const t = Date.parse(signedAt);
  if (Number.isNaN(t)) return false;
  return t <= now.getTime() + maxSkewMs;
}
