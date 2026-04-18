/**
 * One-time device registration (§8.9.1).
 *
 * First-launch flow (requires online + authenticated user):
 *   1. Generate Ed25519 keypair if not already present.
 *   2. Compute device fingerprint (hostname + install UUID).
 *   3. POST /api/v1/pos/terminals/register-device with public key + fingerprint.
 *   4. Persist registration flag so subsequent boots skip this step.
 */

import type Database from "better-sqlite3";
import { getSetting, setSetting } from "../db/settings";
import { computeDeviceFingerprint, getOrCreateKeypair } from "./keys";

export function isDeviceRegistered(db: Database.Database): boolean {
  return getSetting(db, "device_registered") === "true";
}

export interface RegisterDeviceOpts {
  baseUrl: string;
  jwt: string;
  terminalId: number;
}

export interface RegisterDeviceResult {
  device_id: number;
  terminal_id: number;
}

export async function registerDevice(
  db: Database.Database,
  opts: RegisterDeviceOpts,
): Promise<RegisterDeviceResult> {
  const kp = getOrCreateKeypair(db);
  const fingerprint = computeDeviceFingerprint(db);

  const res = await fetch(`${opts.baseUrl}/api/v1/pos/terminals/register-device`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${opts.jwt}`,
    },
    body: JSON.stringify({
      terminal_id: opts.terminalId,
      public_key: kp.publicKey,
      device_fingerprint: fingerprint,
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`register-device failed (HTTP ${res.status}): ${detail.slice(0, 200)}`);
  }

  const data = (await res.json()) as RegisterDeviceResult;
  setSetting(db, "device_registered", "true");
  setSetting(db, "device_id", String(data.device_id));
  return data;
}
