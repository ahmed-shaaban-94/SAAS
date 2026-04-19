// Mock the secure-store so these tests don't need Electron's safeStorage.
// We route reads/writes through plain UTF-8 in the real secrets_dpapi table —
// enough to exercise the keys.ts logic without duplicating secure-store coverage.
jest.mock("../../authz/secure-store", () => {
  return {
    readSecret: (db: import("better-sqlite3").Database, key: string): string | null => {
      const row = db
        .prepare("SELECT ciphertext FROM secrets_dpapi WHERE key=?")
        .get(key) as { ciphertext: Buffer } | undefined;
      return row ? row.ciphertext.toString("utf8") : null;
    },
    writeSecret: (db: import("better-sqlite3").Database, key: string, value: string): void => {
      const now = new Date().toISOString();
      db.prepare(
        `INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)
         ON CONFLICT(key) DO UPDATE SET ciphertext=excluded.ciphertext, updated_at=excluded.updated_at`,
      ).run(key, Buffer.from(value, "utf8"), now);
    },
    deleteSecret: (db: import("better-sqlite3").Database, key: string): void => {
      db.prepare("DELETE FROM secrets_dpapi WHERE key=?").run(key);
    },
  };
});

import { createHash, createPublicKey, verify as nodeVerify } from "node:crypto";
import Database from "better-sqlite3";
import * as path from "path";
import { applySchema } from "../../db/migrate";
import {
  generateKeypair,
  signCanonical,
  getOrCreateKeypair,
  loadPrivateKey,
  loadPublicKey,
  saveKeypair,
  computeDeviceFingerprint,
  computeDeviceFingerprintV1,
  computeDeviceFingerprintV2,
  getFingerprintV2Components,
  FingerprintMismatchError,
  buildCanonicalString,
} from "../../authz/keys";
import { getSetting, setSetting } from "../../db/settings";

const SCHEMA_PATH = path.join(__dirname, "../../db/schema.sql");
const SPKI_ED25519_HEADER = Buffer.from("302a300506032b6570032100", "hex");

function openTestDb(): Database.Database {
  const db = new Database(":memory:");
  applySchema(db, SCHEMA_PATH);
  return db;
}

describe("generateKeypair", () => {
  it("produces 32 raw bytes for both keys", () => {
    const kp = generateKeypair();
    expect(Buffer.from(kp.publicKey, "base64url")).toHaveLength(32);
    expect(Buffer.from(kp.privateKey, "base64url")).toHaveLength(32);
  });

  it("produces a different pair on each call", () => {
    const kp1 = generateKeypair();
    const kp2 = generateKeypair();
    expect(kp1.privateKey).not.toBe(kp2.privateKey);
  });
});

describe("signCanonical", () => {
  it("produces a signature verifiable with node:crypto", () => {
    const kp = generateKeypair();
    const canonical = [
      "POST",
      "/api/v1/pos/transactions/commit",
      "idem-key-123",
      "42",
      createHash("sha256").update("body", "utf8").digest("hex"),
      "2026-01-01T00:00:00.000Z",
    ].join("\n");

    const sig = signCanonical(kp.privateKey, canonical);

    const pubRaw = Buffer.from(kp.publicKey, "base64url");
    const spki = Buffer.concat([SPKI_ED25519_HEADER, pubRaw]);
    const pubKeyObj = createPublicKey({ key: spki, format: "der", type: "spki" });

    const valid = nodeVerify(
      null,
      Buffer.from(canonical, "utf8"),
      pubKeyObj,
      Buffer.from(sig, "base64url"),
    );
    expect(valid).toBe(true);
  });

  it("signature differs for different canonical strings", () => {
    const kp = generateKeypair();
    const sig1 = signCanonical(kp.privateKey, "canonical-a");
    const sig2 = signCanonical(kp.privateKey, "canonical-b");
    expect(sig1).not.toBe(sig2);
  });
});

describe("buildCanonicalString", () => {
  it("joins fields with newlines and hashes the body", () => {
    const bodyJson = '{"foo":"bar"}';
    const bodyHash = createHash("sha256").update(bodyJson, "utf8").digest("hex");
    const canonical = buildCanonicalString({
      method: "POST",
      path: "/api/v1/pos/transactions/commit",
      idempotencyKey: "idem-123",
      terminalId: "42",
      bodyJson,
      signedAt: "2026-01-01T00:00:00.000Z",
    });
    const parts = canonical.split("\n");
    expect(parts).toHaveLength(6);
    expect(parts[0]).toBe("POST");
    expect(parts[4]).toBe(bodyHash);
  });
});

describe("saveKeypair / loadPrivateKey / loadPublicKey", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("saves and reloads keypair from secrets_dpapi", () => {
    const kp = generateKeypair();
    saveKeypair(db, kp);
    expect(loadPrivateKey(db)).toBe(kp.privateKey);
    expect(loadPublicKey(db)).toBe(kp.publicKey);
  });

  it("returns null when no keypair stored", () => {
    expect(loadPrivateKey(db)).toBeNull();
    expect(loadPublicKey(db)).toBeNull();
  });

  it("overwrites previous keypair on second save", () => {
    const kp1 = generateKeypair();
    const kp2 = generateKeypair();
    saveKeypair(db, kp1);
    saveKeypair(db, kp2);
    expect(loadPrivateKey(db)).toBe(kp2.privateKey);
  });
});

describe("getOrCreateKeypair", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("creates a keypair on first call", () => {
    const kp = getOrCreateKeypair(db);
    expect(kp.publicKey).toBeTruthy();
    expect(kp.privateKey).toBeTruthy();
  });

  it("returns same keypair on subsequent calls (idempotent)", () => {
    const kp1 = getOrCreateKeypair(db);
    const kp2 = getOrCreateKeypair(db);
    expect(kp1.privateKey).toBe(kp2.privateKey);
    expect(kp1.publicKey).toBe(kp2.publicKey);
  });
});

describe("computeDeviceFingerprint / computeDeviceFingerprintV1 (wire-compat alias)", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("returns sha256:<64 hex chars> format", () => {
    const fp = computeDeviceFingerprint(db);
    expect(fp).toMatch(/^sha256:[0-9a-f]{64}$/);
  });

  it("computeDeviceFingerprint is an alias for V1", () => {
    expect(computeDeviceFingerprint).toBe(computeDeviceFingerprintV1);
  });

  it("is stable across calls on the same db", () => {
    const fp1 = computeDeviceFingerprint(db);
    const fp2 = computeDeviceFingerprint(db);
    expect(fp1).toBe(fp2);
  });

  it("differs across different installs (different device_uuid)", () => {
    const db2 = openTestDb();
    const fp1 = computeDeviceFingerprint(db);
    const fp2 = computeDeviceFingerprint(db2);
    db2.close();
    // Different dbs = different install UUIDs = different fingerprints
    expect(fp1).not.toBe(fp2);
  });
});

describe("computeDeviceFingerprintV2", () => {
  let db: Database.Database;

  const reliableDeps = {
    hostname: () => "pos-host",
    platform: () => "linux" as const,
    networkInterfaces: () => ({
      eth0: [{ address: "10.0.0.1", mac: "aa:bb:cc:dd:ee:01", internal: false, family: "IPv4" }],
    }),
    readFile: () => "machineid-abcdef0123456789abcdef0123456789\n",
    execSync: () => "",
  };

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("returns sha256v2:<64 hex> digest", () => {
    const fp = computeDeviceFingerprintV2(db, reliableDeps);
    expect(fp).toMatch(/^sha256v2:[0-9a-f]{64}$/);
  });

  it("persists the digest on first call", () => {
    expect(getSetting(db, "device_fingerprint_v2")).toBeNull();
    const fp = computeDeviceFingerprintV2(db, reliableDeps);
    expect(getSetting(db, "device_fingerprint_v2")).toBe(fp);
  });

  it("is idempotent across subsequent calls when hardware unchanged", () => {
    const fp1 = computeDeviceFingerprintV2(db, reliableDeps);
    const fp2 = computeDeviceFingerprintV2(db, reliableDeps);
    expect(fp1).toBe(fp2);
  });

  it("throws FingerprintMismatchError when hardware changes after persistence", () => {
    // First boot — persist the v2 digest.
    const stored = computeDeviceFingerprintV2(db, reliableDeps);

    // Subsequent boot on different hardware (MAC changed = NIC swap).
    const changedDeps = {
      ...reliableDeps,
      networkInterfaces: () => ({
        eth0: [
          { address: "10.0.0.1", mac: "ff:ff:ff:ff:ff:ff", internal: false, family: "IPv4" },
        ],
      }),
    };

    try {
      computeDeviceFingerprintV2(db, changedDeps);
      throw new Error("expected FingerprintMismatchError");
    } catch (err) {
      expect(err).toBeInstanceOf(FingerprintMismatchError);
      const mismatch = err as FingerprintMismatchError;
      expect(mismatch.stored).toBe(stored);
      expect(mismatch.current).not.toBe(stored);
      expect(mismatch.current).toMatch(/^sha256v2:[0-9a-f]{64}$/);
    }
  });

  it("does not overwrite the stored digest when a mismatch is thrown", () => {
    const stored = computeDeviceFingerprintV2(db, reliableDeps);
    const changedDeps = {
      ...reliableDeps,
      hostname: () => "different-host",
    };
    expect(() => computeDeviceFingerprintV2(db, changedDeps)).toThrow(FingerprintMismatchError);
    // Stored value must still be the original — mismatch does not self-heal.
    expect(getSetting(db, "device_fingerprint_v2")).toBe(stored);
  });

  it("returns the persisted value even if caller supplies different deps on re-entry", () => {
    // Simulate: admin pre-seeds the row manually (or it was written by a prior boot).
    setSetting(db, "device_fingerprint_v2", "sha256v2:deadbeef");
    // Same call should throw, because "deadbeef" does not match what the host
    // actually reports now. This protects against registry tampering.
    expect(() => computeDeviceFingerprintV2(db, reliableDeps)).toThrow(FingerprintMismatchError);
  });
});

describe("getFingerprintV2Components", () => {
  it("exposes hostname / machineId / primaryMac without persisting", () => {
    const r = getFingerprintV2Components({
      hostname: () => "diag-host",
      platform: () => "linux",
      networkInterfaces: () => ({
        eth0: [{ address: "1.2.3.4", mac: "aa:bb:cc:dd:ee:01", internal: false, family: "IPv4" }],
      }),
      readFile: () => "diag-machine-id-0000000000000000\n",
    });
    expect(r.components.hostname).toBe("diag-host");
    expect(r.components.primaryMac).toBe("aa:bb:cc:dd:ee:01");
    expect(r.components.machineId).toBe("diag-machine-id-0000000000000000");
    expect(r.reliable).toBe(true);
    expect(r.digest).toMatch(/^sha256v2:[0-9a-f]{64}$/);
  });

  it("reliable=false on a bare sandbox (no machineId + no MAC)", () => {
    const r = getFingerprintV2Components({
      hostname: () => "sandbox",
      platform: () => "linux",
      networkInterfaces: () => ({}),
      readFile: () => { throw new Error("ENOENT"); },
      execSync: () => { throw new Error("no reg"); },
    });
    expect(r.reliable).toBe(false);
  });
});

describe("FingerprintMismatchError", () => {
  it("has name and message with tamper wording", () => {
    const err = new FingerprintMismatchError("sha256v2:aaaa", "sha256v2:bbbb");
    expect(err.name).toBe("FingerprintMismatchError");
    expect(err.message).toMatch(/hardware has changed or been tampered with/);
    expect(err.stored).toBe("sha256v2:aaaa");
    expect(err.current).toBe("sha256v2:bbbb");
  });
});
