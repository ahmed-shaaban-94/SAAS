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
  buildCanonicalString,
} from "../../authz/keys";

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

describe("computeDeviceFingerprint", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("returns sha256:<64 hex chars> format", () => {
    const fp = computeDeviceFingerprint(db);
    expect(fp).toMatch(/^sha256:[0-9a-f]{64}$/);
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
