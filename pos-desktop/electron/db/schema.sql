-- DataPulse POS Desktop — Local SQLite schema (v1)
--
-- Owned by the Electron main process. Stored at
-- `app.getPath('userData')/pos.db`. Pragmas (set in connection.ts):
--   journal_mode=WAL, foreign_keys=ON, synchronous=NORMAL.
--
-- Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.2.
--
-- All financial values stored as TEXT (decimal.js string) — never REAL.
-- All timestamps ISO-8601 UTC strings.
-- Unresolved predicate (§6.1): status IN ('pending','syncing','rejected').
--
-- Reserved pragmas / indices are set at connection open, not here, so this
-- file can be applied via node-sqlite3 / better-sqlite3 prepared statements
-- without any runtime branching.

-- ─────────────────────────────────────────────────────────────
-- Product catalog snapshot (pulled from /pos/catalog/products)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS products (
    drug_code            TEXT PRIMARY KEY,
    drug_name            TEXT NOT NULL,
    drug_brand           TEXT,
    drug_cluster         TEXT,
    is_controlled        INTEGER NOT NULL DEFAULT 0,
    requires_pharmacist  INTEGER NOT NULL DEFAULT 0,
    unit_price           TEXT NOT NULL,         -- decimal string
    updated_at           TEXT NOT NULL          -- ISO-8601
);

CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
    drug_name, drug_brand, drug_cluster,
    content='products',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);

-- ─────────────────────────────────────────────────────────────
-- Stock per batch per site (pulled from /pos/catalog/stock)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stock (
    drug_code     TEXT NOT NULL,
    site_code     TEXT NOT NULL,
    batch_number  TEXT NOT NULL,
    quantity      TEXT NOT NULL,                -- decimal string
    expiry_date   TEXT,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (drug_code, site_code, batch_number),
    FOREIGN KEY (drug_code) REFERENCES products(drug_code)
);

CREATE INDEX IF NOT EXISTS idx_stock_site ON stock (site_code);

-- ─────────────────────────────────────────────────────────────
-- Local mirror of an active shift (server-confirmed row lives in
-- pos.shift_records on the API; this is the client's view)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS shifts_local (
    id              INTEGER PRIMARY KEY,        -- server id after sync
    local_id        TEXT NOT NULL UNIQUE,       -- UUID before sync
    terminal_id     INTEGER NOT NULL,
    staff_id        TEXT NOT NULL,
    site_code       TEXT NOT NULL,
    shift_date      TEXT NOT NULL,
    opened_at       TEXT NOT NULL,
    closed_at       TEXT,
    opening_cash    TEXT NOT NULL,
    closing_cash    TEXT,
    expected_cash   TEXT,
    variance        TEXT,
    pending_close   INTEGER NOT NULL DEFAULT 0
);

-- ─────────────────────────────────────────────────────────────
-- Outbound transaction queue — canonical state machine (§6.1)
--   status ∈ {pending, syncing, synced, rejected, reconciled}
--   confirmation ∈ {provisional, confirmed, reconciled}
-- Unresolved predicate: status IN ('pending','syncing','rejected').
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS transactions_queue (
    local_id             TEXT PRIMARY KEY,                -- UUID
    client_txn_id        TEXT NOT NULL UNIQUE,            -- Idempotency-Key header
    endpoint             TEXT NOT NULL,
    payload              TEXT NOT NULL,                   -- JSON
    status               TEXT NOT NULL
        CHECK (status IN ('pending','syncing','synced','rejected','reconciled')),
    confirmation         TEXT NOT NULL DEFAULT 'provisional'
        CHECK (confirmation IN ('provisional','confirmed','reconciled')),
    reconciliation_kind  TEXT
        CHECK (
            reconciliation_kind IN ('retry_override','record_loss','corrective_void')
            OR reconciliation_kind IS NULL
        ),
    reconciliation_note  TEXT,
    reconciliation_by    TEXT,
    reconciled_at        TEXT,
    server_id            INTEGER,
    server_response      TEXT,                            -- JSON
    retry_count          INTEGER NOT NULL DEFAULT 0,
    last_error           TEXT,
    next_attempt_at      TEXT,
    -- §8.9 signed envelope fields (§13 known open item: persisted here so
    -- crash-recovery can resubmit the original signature verbatim instead
    -- of re-signing with a new timestamp).
    signed_at            TEXT NOT NULL,
    envelope_version     INTEGER NOT NULL DEFAULT 1,
    auth_mode            TEXT NOT NULL
        CHECK (auth_mode IN ('bearer','offline_grant')),
    grant_id             TEXT,
    device_signature     TEXT NOT NULL,                   -- base64-url Ed25519
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queue_status_attempt
    ON transactions_queue (status, next_attempt_at);

CREATE INDEX IF NOT EXISTS idx_queue_confirmation
    ON transactions_queue (confirmation);

CREATE INDEX IF NOT EXISTS idx_queue_unresolved
    ON transactions_queue (status)
    WHERE status IN ('pending','syncing','rejected');

-- ─────────────────────────────────────────────────────────────
-- Sync cursors per entity (§6.2)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sync_state (
    entity            TEXT PRIMARY KEY,
    last_synced_at    TEXT,
    last_cursor       TEXT
);

INSERT OR IGNORE INTO sync_state(entity) VALUES
    ('products'),
    ('prices'),
    ('stock');

-- ─────────────────────────────────────────────────────────────
-- Key/value settings (terminal_id, site_code, printer config, theme, …)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);

INSERT OR IGNORE INTO settings(key, value) VALUES
    ('schema_version',           '1'),
    ('min_compatible_app_version','1.0.0'),
    ('hardware_mode',            'mock'),
    ('printer_interface',        'tcp://192.168.1.100:9100'),
    ('printer_type',             'EPSON'),
    ('language',                 'ar-EG'),
    ('numeric_style',            'latin'),
    ('density',                  'compact');

-- ─────────────────────────────────────────────────────────────
-- Schema history (§4.5 — each applied migration appends here)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_history (
    version       INTEGER PRIMARY KEY,
    applied_at    TEXT NOT NULL,
    up_sql_sha    TEXT NOT NULL,
    down_sql_sha  TEXT,                       -- NULL for requires_queue_drained
    app_version   TEXT NOT NULL
);

-- ─────────────────────────────────────────────────────────────
-- Local-only audit trail (never leaves the machine)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event       TEXT NOT NULL,                -- 'drawer.nosale','scan.miss','grant.refresh','override.consumed', …
    payload     TEXT,                         -- JSON
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at DESC);

-- ─────────────────────────────────────────────────────────────
-- DPAPI-protected secret store (encrypted blobs; plaintext never
-- leaves the main process)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS secrets_dpapi (
    key         TEXT PRIMARY KEY,             -- 'device_private_key','offline_grant','jwt','refresh_token', …
    ciphertext  BLOB NOT NULL,
    updated_at  TEXT NOT NULL
);

-- ─────────────────────────────────────────────────────────────
-- Override-code ledger (prevents double-spend of scrypt codes)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS consumed_override_codes (
    grant_id    TEXT NOT NULL,
    code_id     TEXT NOT NULL,
    PRIMARY KEY (grant_id, code_id)
);
