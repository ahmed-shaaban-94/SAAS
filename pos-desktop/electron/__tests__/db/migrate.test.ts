import * as path from "path";
import { openDb, closeDb } from "../../db/connection";
import { applySchema } from "../../db/migrate";

const SCHEMA = path.join(__dirname, "../../db/schema.sql");

function freshDb() {
  const db = openDb(":memory:");
  applySchema(db, SCHEMA);
  return db;
}

describe("applySchema", () => {
  afterEach(() => closeDb());

  it("runs without throwing", () => {
    const db = openDb(":memory:");
    expect(() => applySchema(db, SCHEMA)).not.toThrow();
  });

  it("creates all required tables", () => {
    const db = freshDb();
    const tables = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
      )
      .all() as { name: string }[];
    const names = new Set(tables.map((t) => t.name));
    for (const t of [
      "products",
      "stock",
      "shifts_local",
      "transactions_queue",
      "sync_state",
      "settings",
      "schema_history",
      "audit_log",
      "secrets_dpapi",
    ]) {
      expect(names).toContain(t);
    }
  });

  it("creates the products_fts virtual table", () => {
    const db = freshDb();
    const row = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='products_fts'",
      )
      .get() as { name: string } | undefined;
    expect(row?.name).toBe("products_fts");
  });

  it("seeds hardware_mode default setting", () => {
    const db = freshDb();
    const row = db
      .prepare("SELECT value FROM settings WHERE key=?")
      .get("hardware_mode") as { value: string } | undefined;
    expect(row?.value).toBe("mock");
  });

  it("seeds schema_version default setting", () => {
    const db = freshDb();
    const row = db
      .prepare("SELECT value FROM settings WHERE key=?")
      .get("schema_version") as { value: string } | undefined;
    expect(row?.value).toBe("1");
  });

  it("seeds sync_state with 3 entities", () => {
    const db = freshDb();
    const rows = db
      .prepare("SELECT entity FROM sync_state ORDER BY entity")
      .all() as { entity: string }[];
    expect(rows.map((r) => r.entity)).toEqual(["prices", "products", "stock"]);
  });

  it("is idempotent — can be applied twice without error", () => {
    const db = openDb(":memory:");
    applySchema(db, SCHEMA);
    expect(() => applySchema(db, SCHEMA)).not.toThrow();
  });

  it("enforces status CHECK on transactions_queue", () => {
    const db = freshDb();
    expect(() =>
      db
        .prepare(
          `INSERT INTO transactions_queue
           (local_id, client_txn_id, endpoint, payload, status, confirmation,
            signed_at, auth_mode, device_signature, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
        )
        .run(
          "id1", "ctxn1", "/api", "{}", "invalid_status", "provisional",
          "2026-01-01T00:00:00Z", "bearer", "sig", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
        ),
    ).toThrow();
  });
});
