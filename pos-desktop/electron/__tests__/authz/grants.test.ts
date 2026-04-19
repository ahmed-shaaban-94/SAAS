// Mock the secure-store so these tests don't need Electron's safeStorage.
// We route reads/writes through plain UTF-8 in the real secrets_dpapi table —
// enough to exercise the grants.ts logic without duplicating secure-store coverage.
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

import { scryptSync } from "node:crypto";
import Database from "better-sqlite3";
import * as path from "path";
import { applySchema } from "../../db/migrate";
import {
  currentGrant,
  saveGrant,
  clearGrant,
  grantState,
  refreshGrant,
  consumeOverrideCode,
  type OfflineGrantEnvelope,
} from "../../authz/grants";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const SCHEMA_PATH = path.join(__dirname, "../../db/schema.sql");

function openTestDb(): Database.Database {
  const db = new Database(":memory:");
  applySchema(db, SCHEMA_PATH);
  return db;
}

/** Build a minimal valid OfflineGrantEnvelope for tests. */
function makeEnvelope(overrides: Partial<OfflineGrantEnvelope["payload"]> = {}): OfflineGrantEnvelope {
  return {
    payload: {
      grant_id: "grant-001",
      offline_expires_at: new Date(Date.now() + 3_600_000).toISOString(), // 1 hour from now
      shift_id: 10,
      terminal_id: 1,
      tenant_id: 100,
      device_fingerprint: "sha256:aabbcc",
      ...overrides,
    },
    signature_ed25519: "sig_placeholder",
    key_id: "key-001",
  };
}

/** Compute a real scrypt hash with the SAME params as grants.ts. */
function computeScryptHash(code: string, salt: Buffer): Buffer {
  return scryptSync(Buffer.from(code, "utf8"), salt, 32, {
    N: 16384,
    r: 8,
    p: 1,
    maxmem: 64 * 1024 * 1024,
  });
}

// ─── currentGrant ─────────────────────────────────────────────────────────────

describe("currentGrant", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("returns null when no grant is stored", () => {
    expect(currentGrant(db)).toBeNull();
  });

  it("returns the parsed envelope after saveGrant", () => {
    const env = makeEnvelope();
    saveGrant(db, env);
    const got = currentGrant(db);
    expect(got).toEqual(env);
  });

  it("returns null when the stored blob is invalid JSON", () => {
    // Write a malformed blob directly into secrets_dpapi
    const now = new Date().toISOString();
    db.prepare(
      `INSERT INTO secrets_dpapi(key, ciphertext, updated_at) VALUES('offline_grant', ?, ?)`,
    ).run(Buffer.from("not-json", "utf8"), now);
    expect(currentGrant(db)).toBeNull();
  });
});

// ─── saveGrant ────────────────────────────────────────────────────────────────

describe("saveGrant", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("writes JSON to secrets_dpapi and is readable via currentGrant", () => {
    const env = makeEnvelope();
    saveGrant(db, env);
    const row = db
      .prepare("SELECT ciphertext FROM secrets_dpapi WHERE key='offline_grant'")
      .get() as { ciphertext: Buffer } | undefined;
    expect(row).toBeDefined();
    expect(JSON.parse(row!.ciphertext.toString("utf8"))).toEqual(env);
  });

  it("overwrites a previous grant on second save", () => {
    const env1 = makeEnvelope({ grant_id: "grant-001" });
    const env2 = makeEnvelope({ grant_id: "grant-002" });
    saveGrant(db, env1);
    saveGrant(db, env2);
    const got = currentGrant(db);
    expect(got?.payload.grant_id).toBe("grant-002");
  });
});

// ─── clearGrant ───────────────────────────────────────────────────────────────

describe("clearGrant", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("removes the stored grant so currentGrant returns null", () => {
    saveGrant(db, makeEnvelope());
    expect(currentGrant(db)).not.toBeNull();
    clearGrant(db);
    expect(currentGrant(db)).toBeNull();
  });

  it("does not throw when no grant exists", () => {
    expect(() => clearGrant(db)).not.toThrow();
  });
});

// ─── grantState ───────────────────────────────────────────────────────────────

describe("grantState", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("returns 'online' when a JWT is present in settings", () => {
    db.prepare("INSERT INTO settings(key, value) VALUES('jwt','some.jwt.token') ON CONFLICT(key) DO UPDATE SET value=excluded.value").run();
    expect(grantState(db)).toBe("online");
  });

  it("returns 'offline_expired' when no JWT and no grant", () => {
    expect(grantState(db)).toBe("offline_expired");
  });

  it("returns 'offline_valid' when no JWT + valid unexpired grant", () => {
    saveGrant(db, makeEnvelope());
    expect(grantState(db)).toBe("offline_valid");
  });

  it("returns 'offline_expired' when grant is in the past", () => {
    saveGrant(db, makeEnvelope({
      offline_expires_at: new Date(Date.now() - 1_000).toISOString(),
    }));
    expect(grantState(db)).toBe("offline_expired");
  });

  it("returns 'offline_expired' when offline_expires_at is not a valid date", () => {
    saveGrant(db, makeEnvelope({ offline_expires_at: "not-a-date" }));
    expect(grantState(db)).toBe("offline_expired");
  });
});

// ─── refreshGrant ────────────────────────────────────────────────────────────

describe("refreshGrant", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    jest.resetAllMocks();
    (global as Record<string, unknown>).fetch = jest.fn();
  });
  afterEach(() => { db.close(); });

  it("throws when no JWT in settings", async () => {
    await expect(refreshGrant(db, { baseUrl: "https://api.example.com" })).rejects.toThrow(
      "not authenticated",
    );
  });

  it("throws when JWT present but no currentGrant to refresh", async () => {
    db.prepare("INSERT INTO settings(key, value) VALUES('jwt','tok') ON CONFLICT(key) DO UPDATE SET value=excluded.value").run();
    // No grant stored
    await expect(refreshGrant(db, { baseUrl: "https://api.example.com" })).rejects.toThrow(
      "no current grant",
    );
  });

  it("POSTs to correct URL with JWT header and returns saved envelope", async () => {
    db.prepare("INSERT INTO settings(key, value) VALUES('jwt','tok') ON CONFLICT(key) DO UPDATE SET value=excluded.value").run();
    const existing = makeEnvelope({ shift_id: 55, device_fingerprint: "sha256:fp" });
    saveGrant(db, existing);

    const newEnvelope = makeEnvelope({ grant_id: "grant-new", shift_id: 55 });
    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => newEnvelope,
    });

    const result = await refreshGrant(db, { baseUrl: "https://api.example.com" });

    // Correct URL
    expect(fetch).toHaveBeenCalledWith(
      "https://api.example.com/api/v1/pos/shifts/55/refresh-grant",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer tok",
        }),
      }),
    );

    // Returns the server envelope
    expect(result).toEqual(newEnvelope);

    // Saved to DB
    expect(currentGrant(db)).toEqual(newEnvelope);
  });

  it("throws on non-ok response", async () => {
    db.prepare("INSERT INTO settings(key, value) VALUES('jwt','tok') ON CONFLICT(key) DO UPDATE SET value=excluded.value").run();
    saveGrant(db, makeEnvelope({ shift_id: 5 }));

    (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => "Unauthorized",
    });

    await expect(refreshGrant(db, { baseUrl: "https://api.example.com" })).rejects.toThrow("HTTP 401");
  });
});

// ─── consumeOverrideCode ──────────────────────────────────────────────────────

describe("consumeOverrideCode", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("returns { ok: false, reason: 'no_grant' } when no grant stored", () => {
    const result = consumeOverrideCode(db, "any-code");
    expect(result).toEqual({ ok: false, reason: "no_grant" });
  });

  it("returns { ok: false, reason: 'no_override_codes_in_grant' } when grant has no codes", () => {
    saveGrant(db, makeEnvelope({ override_codes: [] }));
    const result = consumeOverrideCode(db, "any-code");
    expect(result).toEqual({ ok: false, reason: "no_override_codes_in_grant" });
  });

  it("returns { ok: false, reason: 'no_override_codes_in_grant' } when override_codes is undefined", () => {
    const env = makeEnvelope();
    // override_codes is undefined by default (not set in makeEnvelope)
    delete (env.payload as unknown as Record<string, unknown>).override_codes;
    saveGrant(db, env);
    const result = consumeOverrideCode(db, "any-code");
    expect(result).toEqual({ ok: false, reason: "no_override_codes_in_grant" });
  });

  it("returns { ok: false, reason: 'invalid_code' } for wrong code", () => {
    const salt = Buffer.from("testsalt", "utf8");
    const hash = computeScryptHash("correct-code", salt);

    const env = makeEnvelope({
      override_codes: [
        {
          code_id: "code-001",
          salt: salt.toString("base64url"),
          hash: hash.toString("base64url"),
          issued_to_staff_id: "staff-1",
        },
      ],
    });
    saveGrant(db, env);

    const result = consumeOverrideCode(db, "wrong-code");
    expect(result).toEqual({ ok: false, reason: "invalid_code" });
  });

  it("returns { ok: true } for correct code (real scrypt verification)", () => {
    const code = "override-1234";
    const salt = Buffer.from("uniquesalt99", "utf8");
    const hash = computeScryptHash(code, salt);

    const env = makeEnvelope({
      grant_id: "grant-scrypt-test",
      override_codes: [
        {
          code_id: "code-scrypt",
          salt: salt.toString("base64url"),
          hash: hash.toString("base64url"),
          issued_to_staff_id: "staff-42",
        },
      ],
    });
    saveGrant(db, env);

    const result = consumeOverrideCode(db, code);
    expect(result).toEqual({ ok: true, code_id: "code-scrypt", issued_to_staff_id: "staff-42" });
  });

  it("inserts into consumed_override_codes and audit_log on successful consume", () => {
    const code = "override-audit";
    const salt = Buffer.from("saltsalt", "utf8");
    const hash = computeScryptHash(code, salt);

    const env = makeEnvelope({
      grant_id: "grant-audit",
      override_codes: [
        {
          code_id: "code-audit",
          salt: salt.toString("base64url"),
          hash: hash.toString("base64url"),
          issued_to_staff_id: "staff-99",
        },
      ],
    });
    saveGrant(db, env);
    consumeOverrideCode(db, code);

    const consumed = db
      .prepare("SELECT * FROM consumed_override_codes WHERE grant_id='grant-audit' AND code_id='code-audit'")
      .get();
    expect(consumed).toBeDefined();

    const auditRow = db
      .prepare("SELECT payload FROM audit_log WHERE event='override.consumed' ORDER BY id DESC LIMIT 1")
      .get() as { payload: string } | undefined;
    expect(auditRow).toBeDefined();
    const payload = JSON.parse(auditRow!.payload);
    expect(payload.code_id).toBe("code-audit");
    expect(payload.staff_id).toBe("staff-99");
  });

  it("returns { ok: false, reason: 'already_consumed' } on second attempt with same code", () => {
    const code = "override-double";
    const salt = Buffer.from("saltdouble", "utf8");
    const hash = computeScryptHash(code, salt);

    const env = makeEnvelope({
      grant_id: "grant-double",
      override_codes: [
        {
          code_id: "code-double",
          salt: salt.toString("base64url"),
          hash: hash.toString("base64url"),
          issued_to_staff_id: "staff-3",
        },
      ],
    });
    saveGrant(db, env);

    const first = consumeOverrideCode(db, code);
    expect(first).toEqual({ ok: true, code_id: "code-double", issued_to_staff_id: "staff-3" });

    const second = consumeOverrideCode(db, code);
    expect(second).toEqual({ ok: false, reason: "already_consumed" });
  });
});
