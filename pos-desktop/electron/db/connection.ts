import Database from "better-sqlite3";

let _db: Database.Database | null = null;

/**
 * Open (or replace) the SQLite database at the given path.
 * Pass `:memory:` for in-process tests.
 * Applies WAL mode, FK enforcement, and NORMAL synchronous pragma — §4.2.
 */
export function openDb(filePath: string): Database.Database {
  if (_db) {
    _db.close();
  }
  _db = new Database(filePath);
  _db.pragma("journal_mode = WAL");
  _db.pragma("foreign_keys = ON");
  _db.pragma("synchronous = NORMAL");
  // 32 MB page cache — reduces I/O on hot paths (product search, queue drain)
  _db.pragma("cache_size = -32000");
  _db.pragma("temp_store = MEMORY");
  return _db;
}

/** Returns the open DB instance. Throws if openDb() has not been called. */
export function getDb(): Database.Database {
  if (!_db) throw new Error("DB not open — call openDb() first");
  return _db;
}

/** Close the current DB connection and reset the singleton. */
export function closeDb(): void {
  if (_db) {
    _db.close();
    _db = null;
  }
}
