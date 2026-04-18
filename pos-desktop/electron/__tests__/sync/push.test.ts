import Database from "better-sqlite3";
import * as path from "path";
import { applySchema } from "../../db/migrate";
import { enqueueTransaction } from "../../db/queue";
import { setSetting } from "../../db/settings";
import { saveKeypair, generateKeypair } from "../../authz/keys";
import { drainQueue, buildEnqueueSignature, getBaseUrl } from "../../sync/push";

const SCHEMA_PATH = path.join(__dirname, "../../db/schema.sql");

function openTestDb(): Database.Database {
  const db = new Database(":memory:");
  applySchema(db, SCHEMA_PATH);
  return db;
}

function seedQueue(db: Database.Database, overrides: Partial<Parameters<typeof enqueueTransaction>[1]> = {}) {
  return enqueueTransaction(db, {
    endpoint: "POST /api/v1/pos/transactions/commit",
    payload: { terminal_id: 1, items: [] },
    signed_at: new Date().toISOString(),
    auth_mode: "bearer",
    grant_id: null,
    device_signature: "stub-sig",
    ...overrides,
  });
}

function setupDb(db: Database.Database) {
  setSetting(db, "jwt", "test.jwt.token");
  setSetting(db, "terminal_id", "1");
  const kp = generateKeypair();
  saveKeypair(db, kp);
  return kp;
}

afterEach(() => {
  jest.restoreAllMocks();
});

describe("getBaseUrl", () => {
  it("returns process.env.NEXT_PUBLIC_API_URL when set", () => {
    const orig = process.env.NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_API_URL = "https://custom.example.com";
    expect(getBaseUrl()).toBe("https://custom.example.com");
    process.env.NEXT_PUBLIC_API_URL = orig;
  });
});

describe("buildEnqueueSignature", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    setupDb(db);
  });
  afterEach(() => { db.close(); });

  it("returns a non-empty base64url string when keypair is present", () => {
    const sig = buildEnqueueSignature(db, {
      path: "/api/v1/pos/transactions/commit",
      clientTxnId: "client-123",
      bodyJson: '{"test":true}',
      signedAt: "2026-01-01T00:00:00.000Z",
    });
    expect(sig).toBeTruthy();
    expect(sig).not.toBe("unregistered");
    // base64url characters only
    expect(sig).toMatch(/^[A-Za-z0-9\-_]+$/);
  });

  it("returns 'unregistered' when no private key in db", () => {
    const emptyDb = openTestDb();
    const sig = buildEnqueueSignature(emptyDb, {
      path: "/api/v1/pos/transactions/commit",
      clientTxnId: "client-123",
      bodyJson: '{}',
      signedAt: "2026-01-01T00:00:00.000Z",
    });
    emptyDb.close();
    expect(sig).toBe("unregistered");
  });
});

describe("drainQueue — no rows", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    setupDb(db);
  });
  afterEach(() => { db.close(); });

  it("returns {pushed:0, rejected:0} when queue is empty", async () => {
    global.fetch = jest.fn();
    const result = await drainQueue(db);
    expect(result).toEqual({ pushed: 0, rejected: 0 });
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe("drainQueue — 2xx response", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    setupDb(db);
  });
  afterEach(() => { db.close(); });

  it("marks row synced + confirmed on 200", async () => {
    seedQueue(db);
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ transaction_id: 999, receipt_number: "R-001" }),
    } as unknown as Response);

    const result = await drainQueue(db);
    expect(result.pushed).toBe(1);
    expect(result.rejected).toBe(0);

    const row = db
      .prepare("SELECT status, confirmation, server_id FROM transactions_queue LIMIT 1")
      .get() as { status: string; confirmation: string; server_id: number };
    expect(row.status).toBe("synced");
    expect(row.confirmation).toBe("confirmed");
    expect(row.server_id).toBe(999);
  });

  it("treats 409 (idempotency replay) as synced", async () => {
    seedQueue(db);
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      text: async () => JSON.stringify({ transaction_id: 42 }),
    } as unknown as Response);

    const result = await drainQueue(db);
    expect(result.pushed).toBe(1);

    const row = db
      .prepare("SELECT status FROM transactions_queue LIMIT 1")
      .get() as { status: string };
    expect(row.status).toBe("synced");
  });
});

describe("drainQueue — 4xx rejection", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    setupDb(db);
  });
  afterEach(() => { db.close(); });

  it("marks row rejected on 422 (server business error)", async () => {
    seedQueue(db);
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: async () => JSON.stringify({ detail: "stock unavailable" }),
    } as unknown as Response);

    const result = await drainQueue(db);
    expect(result.rejected).toBe(1);
    expect(result.pushed).toBe(0);

    const row = db
      .prepare("SELECT status, last_error FROM transactions_queue LIMIT 1")
      .get() as { status: string; last_error: string };
    expect(row.status).toBe("rejected");
    expect(row.last_error).toContain("422");
  });
});

describe("drainQueue — 5xx backoff", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    setupDb(db);
  });
  afterEach(() => { db.close(); });

  it("returns row to pending with backoff on 500", async () => {
    seedQueue(db);
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => "Internal Server Error",
    } as unknown as Response);

    const result = await drainQueue(db);
    expect(result.pushed).toBe(0);
    expect(result.rejected).toBe(0);

    const row = db
      .prepare("SELECT status, retry_count, next_attempt_at FROM transactions_queue LIMIT 1")
      .get() as { status: string; retry_count: number; next_attempt_at: string };
    expect(row.status).toBe("pending");
    expect(row.retry_count).toBeGreaterThan(0);
    expect(row.next_attempt_at).toBeTruthy();
  });

  it("returns row to pending on network error", async () => {
    seedQueue(db);
    global.fetch = jest.fn().mockRejectedValue(new Error("ECONNREFUSED"));

    const result = await drainQueue(db);
    expect(result.pushed).toBe(0);

    const row = db
      .prepare("SELECT status FROM transactions_queue LIMIT 1")
      .get() as { status: string };
    expect(row.status).toBe("pending");
  });
});

describe("drainQueue — provisional TTL expired", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = openTestDb();
    setupDb(db);
  });
  afterEach(() => { db.close(); });

  it("marks row rejected with provisional_expired without making HTTP call", async () => {
    // Insert a row created 73 hours ago
    const old = new Date(Date.now() - 73 * 60 * 60 * 1000).toISOString();
    db.prepare(
      `INSERT INTO transactions_queue
         (local_id, client_txn_id, endpoint, payload, status, confirmation,
          signed_at, auth_mode, grant_id, device_signature,
          retry_count, next_attempt_at, created_at, updated_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
    ).run(
      "old-local", "old-idem", "POST /api/v1/pos/transactions/commit",
      "{}", "pending", "provisional",
      old, "bearer", null, "stub",
      0, old, old, old,
    );

    global.fetch = jest.fn();
    const result = await drainQueue(db);
    expect(result.rejected).toBe(1);
    expect(fetch).not.toHaveBeenCalled();

    const row = db
      .prepare("SELECT status, last_error FROM transactions_queue WHERE local_id='old-local'")
      .get() as { status: string; last_error: string };
    expect(row.status).toBe("rejected");
    expect(row.last_error).toBe("provisional_expired");
  });
});

describe("drainQueue — missing credentials", () => {
  let db: Database.Database;

  beforeEach(() => { db = openTestDb(); });
  afterEach(() => { db.close(); });

  it("skips push (backoff) when jwt not set", async () => {
    setSetting(db, "terminal_id", "1");
    // No jwt set
    seedQueue(db);
    global.fetch = jest.fn();

    const result = await drainQueue(db);
    expect(result.pushed).toBe(0);
    expect(fetch).not.toHaveBeenCalled();
  });
});
