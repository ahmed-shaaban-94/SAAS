import * as path from "path";
import type Database from "better-sqlite3";
import { openDb, closeDb } from "../../db/connection";
import { applySchema } from "../../db/migrate";
import { getSetting, setSetting } from "../../db/settings";

const SCHEMA = path.join(__dirname, "../../db/schema.sql");

function freshDb(): Database.Database {
  const db = openDb(":memory:");
  applySchema(db, SCHEMA);
  return db;
}

describe("settings operations", () => {
  let db: Database.Database;

  beforeEach(() => { db = freshDb(); });
  afterEach(() => closeDb());

  it("getSetting returns seeded default for hardware_mode", () => {
    expect(getSetting(db, "hardware_mode")).toBe("mock");
  });

  it("getSetting returns null for unknown key", () => {
    expect(getSetting(db, "nonexistent_key")).toBeNull();
  });

  it("setSetting inserts a new key-value pair", () => {
    setSetting(db, "custom_key", "custom_value");
    expect(getSetting(db, "custom_key")).toBe("custom_value");
  });

  it("setSetting updates an existing key", () => {
    setSetting(db, "hardware_mode", "real");
    expect(getSetting(db, "hardware_mode")).toBe("real");
  });

  it("setSetting is idempotent (upsert)", () => {
    setSetting(db, "theme", "dark");
    setSetting(db, "theme", "light");
    expect(getSetting(db, "theme")).toBe("light");
  });
});
