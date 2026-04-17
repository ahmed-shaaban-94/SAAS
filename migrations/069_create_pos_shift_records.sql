-- Migration: 069 — Create `pos.shift_records` table
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.shift_records (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    terminal_id   BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    tenant_id     INT NOT NULL,
    staff_id      TEXT NOT NULL,
    shift_date    DATE NOT NULL,
    opened_at     TIMESTAMPTZ NOT NULL,
    closed_at     TIMESTAMPTZ,
    opening_cash  NUMERIC(18,4) NOT NULL,
    closing_cash  NUMERIC(18,4),
    expected_cash NUMERIC(18,4),
    variance      NUMERIC(18,4),
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_shifts_terminal
    ON pos.shift_records (terminal_id, shift_date DESC);
CREATE INDEX IF NOT EXISTS idx_pos_shifts_tenant_date
    ON pos.shift_records (tenant_id, shift_date DESC);
CREATE INDEX IF NOT EXISTS idx_pos_shifts_staff
    ON pos.shift_records (tenant_id, staff_id, shift_date DESC);

ALTER TABLE pos.shift_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.shift_records FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.shift_records
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.shift_records
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.shift_records TO datapulse;
GRANT SELECT ON TABLE pos.shift_records TO datapulse_reader;

COMMENT ON TABLE pos.shift_records IS
    'Shift open/close records with cash reconciliation. variance = closing_cash - expected_cash. RLS-protected.';
