-- Migration: 065 — Create `pos` schema and `terminal_sessions` table
-- Layer: POS operational
-- Idempotent.

CREATE SCHEMA IF NOT EXISTS pos;

COMMENT ON SCHEMA pos IS 'Point-of-Sale operational tables — RLS-protected, tenant-scoped';

CREATE TABLE IF NOT EXISTS pos.terminal_sessions (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     INT NOT NULL,
    site_code     TEXT NOT NULL,
    staff_id      TEXT NOT NULL,
    terminal_name TEXT NOT NULL DEFAULT 'Terminal-1',
    status        TEXT NOT NULL DEFAULT 'open'
                  CHECK (status IN ('open', 'active', 'paused', 'closed')),
    opened_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at     TIMESTAMPTZ,
    opening_cash  NUMERIC(18,4) NOT NULL DEFAULT 0,
    closing_cash  NUMERIC(18,4),
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Prevent duplicate active/paused sessions on the same terminal name within a tenant.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_terminal_active
    ON pos.terminal_sessions (tenant_id, terminal_name)
    WHERE status IN ('open', 'active', 'paused');

CREATE INDEX IF NOT EXISTS idx_pos_terminals_tenant_status
    ON pos.terminal_sessions (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_pos_terminals_tenant_site
    ON pos.terminal_sessions (tenant_id, site_code);

ALTER TABLE pos.terminal_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.terminal_sessions FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.terminal_sessions
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.terminal_sessions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.terminal_sessions TO datapulse;
GRANT SELECT ON TABLE pos.terminal_sessions TO datapulse_reader;

COMMENT ON TABLE pos.terminal_sessions IS
    'POS terminal sessions — one row per open/closed shift on a register. RLS-protected.';
