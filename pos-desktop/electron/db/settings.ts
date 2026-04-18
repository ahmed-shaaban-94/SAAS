import type Database from "better-sqlite3";

/** Get a setting value by key. Returns null if the key does not exist. */
export function getSetting(db: Database.Database, key: string): string | null {
  const row = db
    .prepare("SELECT value FROM settings WHERE key=?")
    .get(key) as { value: string } | undefined;
  return row?.value ?? null;
}

/** Upsert a setting (insert or replace). */
export function setSetting(db: Database.Database, key: string, value: string): void {
  db.prepare(
    "INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
  ).run(key, value);
}
