import Database from "better-sqlite3";
import * as path from "path";
import { applySchema } from "../../db/migrate";
import {
  readSecret,
  writeSecret,
  deleteSecret,
  isEncryptionAvailable,
  upgradeSecretsToEncrypted,
  SECURE_STORE_VERSION_V0,
  SECURE_STORE_VERSION_V1,
  type SafeStorageLike,
} from "../../authz/secure-store";

const SCHEMA_PATH = path.join(__dirname, "../../db/schema.sql");

function openTestDb(): Database.Database {
  const db = new Database(":memory:");
  applySchema(db, SCHEMA_PATH);
  return db;
}

/**
 * A deterministic safeStorage double that prefixes plaintext with `enc:`
 * when encrypting. Good enough to verify dispatch without pulling Electron.
 */
function makeMockSafeStorage(overrides: Partial<SafeStorageLike> = {}): SafeStorageLike & {
  isEncryptionAvailable: jest.Mock;
  encryptString: jest.Mock;
  decryptString: jest.Mock;
} {
  return {
    isEncryptionAvailable: jest.fn(() => true),
    encryptString: jest.fn((s: string) => Buffer.from(`enc:${s}`, "utf8")),
    decryptString: jest.fn((b: Buffer) => b.toString("utf8").replace(/^enc:/, "")),
    ...overrides,
  } as SafeStorageLike & {
    isEncryptionAvailable: jest.Mock;
    encryptString: jest.Mock;
    decryptString: jest.Mock;
  };
}

function readRawBlob(db: Database.Database, key: string): Buffer | undefined {
  const row = db
    .prepare("SELECT ciphertext FROM secrets_dpapi WHERE key=?")
    .get(key) as { ciphertext: Buffer } | undefined;
  return row?.ciphertext;
}

// ─── writeSecret ─────────────────────────────────────────────────────────────

describe("writeSecret", () => {
  let db: Database.Database;
  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("stores [0x01, ...ciphertext] when safeStorage is available", () => {
    const ss = makeMockSafeStorage();
    writeSecret(db, "device_private_key", "super-secret-bytes", { safeStorage: ss });

    const blob = readRawBlob(db, "device_private_key");
    expect(blob).toBeDefined();
    expect(blob![0]).toBe(SECURE_STORE_VERSION_V1);
    expect(blob!.subarray(1).toString("utf8")).toBe("enc:super-secret-bytes");
    expect(ss.encryptString).toHaveBeenCalledWith("super-secret-bytes");
  });

  it("stores [0x00, ...utf8] and warns when safeStorage is unavailable", () => {
    const ss = makeMockSafeStorage({ isEncryptionAvailable: jest.fn(() => false) });
    const log = jest.fn();
    writeSecret(db, "offline_grant", "grant-json-blob", { safeStorage: ss, log });

    const blob = readRawBlob(db, "offline_grant");
    expect(blob).toBeDefined();
    expect(blob![0]).toBe(SECURE_STORE_VERSION_V0);
    expect(blob!.subarray(1).toString("utf8")).toBe("grant-json-blob");
    expect(ss.encryptString).not.toHaveBeenCalled();
    expect(log).toHaveBeenCalledWith(
      expect.stringContaining("OS encryption unavailable"),
    );
  });

  it("falls back to v0 if isEncryptionAvailable throws", () => {
    const ss = makeMockSafeStorage({
      isEncryptionAvailable: jest.fn(() => { throw new Error("boom"); }),
    });
    const log = jest.fn();
    writeSecret(db, "k", "v", { safeStorage: ss, log });
    expect(readRawBlob(db, "k")![0]).toBe(SECURE_STORE_VERSION_V0);
  });
});

// ─── readSecret ──────────────────────────────────────────────────────────────

describe("readSecret", () => {
  let db: Database.Database;
  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("decrypts v1 entries via safeStorage", () => {
    const ss = makeMockSafeStorage();
    writeSecret(db, "k", "plaintext-value", { safeStorage: ss });
    const got = readSecret(db, "k", { safeStorage: ss });
    expect(got).toBe("plaintext-value");
    expect(ss.decryptString).toHaveBeenCalled();
  });

  it("returns plain UTF-8 for v0 entries (no safeStorage call)", () => {
    // Stage a v0 blob directly.
    const payload = Buffer.concat([
      Buffer.from([SECURE_STORE_VERSION_V0]),
      Buffer.from("legacy-value", "utf8"),
    ]);
    db.prepare(
      "INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)",
    ).run("k", payload, new Date().toISOString());

    const ss = makeMockSafeStorage();
    const got = readSecret(db, "k", { safeStorage: ss });
    expect(got).toBe("legacy-value");
    expect(ss.decryptString).not.toHaveBeenCalled();
  });

  it("treats a legacy pre-versioning entry (printable first byte) as raw UTF-8", () => {
    // Pre-M3b entries were raw utf-8 with no prefix. Printable ASCII first byte
    // (e.g. base64url 'A' = 0x41, JSON '{' = 0x7b) is neither 0x00 nor 0x01.
    const legacy = Buffer.from("AAAAraw-base64url-like", "utf8");
    db.prepare(
      "INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)",
    ).run("k", legacy, new Date().toISOString());

    const ss = makeMockSafeStorage();
    const got = readSecret(db, "k", { safeStorage: ss });
    expect(got).toBe("AAAAraw-base64url-like");
    expect(ss.decryptString).not.toHaveBeenCalled();
  });

  it("returns null for a missing key", () => {
    expect(readSecret(db, "nothing-here")).toBeNull();
  });

  it("round-trips: write(v1) -> read recovers the exact value", () => {
    const ss = makeMockSafeStorage();
    const original = "ed25519-private-key-base64url";
    writeSecret(db, "device_private_key", original, { safeStorage: ss });
    expect(readSecret(db, "device_private_key", { safeStorage: ss })).toBe(original);
  });
});

// ─── deleteSecret ────────────────────────────────────────────────────────────

describe("deleteSecret", () => {
  let db: Database.Database;
  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("removes the row", () => {
    const ss = makeMockSafeStorage();
    writeSecret(db, "k", "v", { safeStorage: ss });
    expect(readRawBlob(db, "k")).toBeDefined();
    deleteSecret(db, "k");
    expect(readRawBlob(db, "k")).toBeUndefined();
  });

  it("is a no-op when the key does not exist", () => {
    expect(() => deleteSecret(db, "ghost")).not.toThrow();
  });
});

// ─── upgradeSecretsToEncrypted ───────────────────────────────────────────────

describe("upgradeSecretsToEncrypted", () => {
  let db: Database.Database;
  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  function insertRaw(db: Database.Database, key: string, blob: Buffer): void {
    db.prepare(
      "INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)",
    ).run(key, blob, new Date().toISOString());
  }

  it("upgrades v0 and legacy entries to v1, leaves v1 alone", () => {
    const ss = makeMockSafeStorage();

    // v0 entry
    insertRaw(
      db,
      "key_v0",
      Buffer.concat([Buffer.from([SECURE_STORE_VERSION_V0]), Buffer.from("v0-val", "utf8")]),
    );
    // legacy entry (no prefix)
    insertRaw(db, "key_legacy", Buffer.from("legacy-val", "utf8"));
    // v1 entry (should be skipped)
    writeSecret(db, "key_v1", "v1-val", { safeStorage: ss });
    ss.encryptString.mockClear();

    const count = upgradeSecretsToEncrypted(db, { safeStorage: ss });
    expect(count).toBe(2);

    // Both upgraded entries are now v1
    expect(readRawBlob(db, "key_v0")![0]).toBe(SECURE_STORE_VERSION_V1);
    expect(readRawBlob(db, "key_legacy")![0]).toBe(SECURE_STORE_VERSION_V1);
    // Can read the upgraded values back correctly
    expect(readSecret(db, "key_v0", { safeStorage: ss })).toBe("v0-val");
    expect(readSecret(db, "key_legacy", { safeStorage: ss })).toBe("legacy-val");
    // v1 untouched
    expect(readSecret(db, "key_v1", { safeStorage: ss })).toBe("v1-val");
  });

  it("is a no-op when safeStorage is unavailable (returns 0)", () => {
    const ss = makeMockSafeStorage({ isEncryptionAvailable: jest.fn(() => false) });
    // Stage a v0 entry that *would* be upgradable if encryption was available.
    const v0 = Buffer.concat([Buffer.from([SECURE_STORE_VERSION_V0]), Buffer.from("x", "utf8")]);
    db.prepare(
      "INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)",
    ).run("k", v0, new Date().toISOString());

    expect(upgradeSecretsToEncrypted(db, { safeStorage: ss })).toBe(0);
    // Row untouched
    expect(readRawBlob(db, "k")![0]).toBe(SECURE_STORE_VERSION_V0);
    expect(ss.encryptString).not.toHaveBeenCalled();
  });

  it("returns 0 on an empty database", () => {
    const ss = makeMockSafeStorage();
    expect(upgradeSecretsToEncrypted(db, { safeStorage: ss })).toBe(0);
  });

  it("is idempotent — running twice upgrades once", () => {
    const ss = makeMockSafeStorage();
    const v0 = Buffer.concat([Buffer.from([SECURE_STORE_VERSION_V0]), Buffer.from("val", "utf8")]);
    db.prepare(
      "INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES(?,?,?)",
    ).run("k", v0, new Date().toISOString());

    expect(upgradeSecretsToEncrypted(db, { safeStorage: ss })).toBe(1);
    expect(upgradeSecretsToEncrypted(db, { safeStorage: ss })).toBe(0);
  });
});

// ─── isEncryptionAvailable ───────────────────────────────────────────────────

describe("isEncryptionAvailable", () => {
  it("proxies to safeStorage.isEncryptionAvailable (true)", () => {
    const ss = makeMockSafeStorage({ isEncryptionAvailable: jest.fn(() => true) });
    expect(isEncryptionAvailable({ safeStorage: ss })).toBe(true);
    expect(ss.isEncryptionAvailable).toHaveBeenCalled();
  });

  it("proxies to safeStorage.isEncryptionAvailable (false)", () => {
    const ss = makeMockSafeStorage({ isEncryptionAvailable: jest.fn(() => false) });
    expect(isEncryptionAvailable({ safeStorage: ss })).toBe(false);
  });

  it("swallows throws and returns false", () => {
    const ss = makeMockSafeStorage({
      isEncryptionAvailable: jest.fn(() => { throw new Error("no electron"); }),
    });
    expect(isEncryptionAvailable({ safeStorage: ss })).toBe(false);
  });
});
