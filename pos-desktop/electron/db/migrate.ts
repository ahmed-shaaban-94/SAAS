import * as fs from "fs";
import * as path from "path";
import type Database from "better-sqlite3";

/**
 * Apply the SQLite schema to the given database.
 *
 * Safe to call multiple times — all DDL statements use `IF NOT EXISTS`.
 * In production, `sqlPath` defaults to the sibling schema.sql file that is
 * copied into dist/electron/db/ by scripts/copy-assets.js.
 * In tests, pass the absolute path to the source file directly.
 */
export function applySchema(
  db: Database.Database,
  sqlPath: string = path.join(__dirname, "schema.sql"),
): void {
  const sql = fs.readFileSync(sqlPath, "utf8");
  db.exec(sql);
}
