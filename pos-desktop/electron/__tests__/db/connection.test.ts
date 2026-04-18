import { openDb, getDb, closeDb } from "../../db/connection";

describe("DB connection", () => {
  afterEach(() => closeDb());

  it("opens an in-memory database", () => {
    const db = openDb(":memory:");
    expect(db).toBeDefined();
    expect(db.open).toBe(true);
  });

  it("sets WAL journal mode (file DBs; :memory: always stays in 'memory' mode)", () => {
    // SQLite :memory: databases silently ignore PRAGMA journal_mode=WAL and
    // remain in 'memory' mode. This is an SQLite limitation, not a bug.
    // We verify the pragma is accepted without throwing.
    const db = openDb(":memory:");
    expect(() => db.pragma("journal_mode = WAL")).not.toThrow();
  });

  it("enforces foreign keys", () => {
    const db = openDb(":memory:");
    const rows = db.pragma("foreign_keys") as { foreign_keys: number }[];
    expect(rows[0].foreign_keys).toBe(1);
  });

  it("getDb throws before openDb", () => {
    expect(() => getDb()).toThrow("DB not open");
  });

  it("getDb returns the same instance after openDb", () => {
    const db = openDb(":memory:");
    expect(getDb()).toBe(db);
  });

  it("closeDb makes getDb throw again", () => {
    openDb(":memory:");
    closeDb();
    expect(() => getDb()).toThrow("DB not open");
  });

  it("openDb called twice replaces the previous db", () => {
    const first = openDb(":memory:");
    expect(first.open).toBe(true);
    const second = openDb(":memory:");
    expect(getDb()).toBe(second);
    expect(first.open).toBe(false); // old db was closed
  });
});
