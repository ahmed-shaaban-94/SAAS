-- Migration: 070 — Create `pos.cash_drawer_events` table
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.cash_drawer_events (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    terminal_id  BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    tenant_id    INT NOT NULL,
    event_type   TEXT NOT NULL CHECK (event_type IN ('sale', 'refund', 'float', 'pickup')),
    amount       NUMERIC(18,4) NOT NULL,
    reference_id TEXT,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_cash_events_terminal
    ON pos.cash_drawer_events (terminal_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_pos_cash_events_tenant_type
    ON pos.cash_drawer_events (tenant_id, event_type, timestamp DESC);

ALTER TABLE pos.cash_drawer_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.cash_drawer_events FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.cash_drawer_events
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.cash_drawer_events
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.cash_drawer_events TO datapulse;
GRANT SELECT ON TABLE pos.cash_drawer_events TO datapulse_reader;

COMMENT ON TABLE pos.cash_drawer_events IS
    'Immutable log of all cash drawer movements: sales, refunds, float additions, and pickups. RLS-protected.';
