-- Migration: 077 — POS idempotency keys
-- Layer: POS operational
-- Idempotent.
--
-- Dedupes retried mutating POS requests by client-supplied Idempotency-Key.
-- Retention (168h) strictly exceeds provisional queue window (72h) so every
-- client retry falls inside the server dedupe horizon. See design spec
-- docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §6.4.

CREATE TABLE IF NOT EXISTS pos.idempotency_keys (
    key             TEXT PRIMARY KEY,
    tenant_id       INT NOT NULL,
    endpoint        TEXT NOT NULL,
    request_hash    TEXT NOT NULL,
    response_status INT,
    response_body   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pos_idemp_expires
    ON pos.idempotency_keys (expires_at);

ALTER TABLE pos.idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.idempotency_keys FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.idempotency_keys
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.idempotency_keys
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.idempotency_keys TO datapulse;
GRANT SELECT ON TABLE pos.idempotency_keys TO datapulse_reader;

COMMENT ON TABLE pos.idempotency_keys IS
  'Request dedupe for POS mutating endpoints. TTL = 168h (> provisional_ttl 72h + 96h safety margin). RLS-protected.';
