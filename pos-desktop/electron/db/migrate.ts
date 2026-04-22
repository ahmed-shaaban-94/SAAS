import * as crypto from "crypto";
import * as fs from "fs";
import * as path from "path";
import type Database from "better-sqlite3";

// Schema version — increment when schema.sql changes meaningfully.
// This is a monotonic integer stored in schema_history to track what has
// been applied. The schema itself uses `IF NOT EXISTS` so re-running is safe;
// the history row prevents redundant re-runs on fast startup paths.
const SCHEMA_VERSION = 1;

/**
 * Apply the SQLite schema to the given database and record it in
 * schema_history so startup can skip re-running on subsequent boots.
 *
 * Safe to call multiple times — all DDL statements use `IF NOT EXISTS` and
 * the history table guards against double-recording the same version.
 *
 * In production, `sqlPath` defaults to the sibling schema.sql file that is
 * copied into dist/electron/db/ by scripts/copy-assets.js.
 * In tests, pass the absolute path to the source file directly.
 */
export function applySchema(
  db: Database.Database,
  sqlPath: string = path.join(__dirname, "schema.sql"),
  appVersion: string = "0.0.0",
): void {
  const sql = fs.readFileSync(sqlPath, "utf8");
  const sha = crypto.createHash("sha256").update(sql).digest("hex");

  // Run the DDL — idempotent via IF NOT EXISTS
  db.exec(sql);

  // Record in schema_history if this version hasn't been applied yet
  const existing = db
    .prepare("SELECT version FROM schema_history WHERE version = ?")
    .get(SCHEMA_VERSION);

  if (!existing) {
    db.prepare(
      `INSERT INTO schema_history (version, applied_at, up_sql_sha, app_version)
       VALUES (?, ?, ?, ?)`,
    ).run(SCHEMA_VERSION, new Date().toISOString(), sha, appVersion);
  }
}
