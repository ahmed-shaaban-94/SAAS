-- Migration: 071 — Create `pos.void_log` table
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.void_log (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES pos.transactions(id),
    tenant_id      INT NOT NULL,
    voided_by      TEXT NOT NULL,
    reason         TEXT NOT NULL,
    voided_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_void_txn
    ON pos.void_log (transaction_id);
CREATE INDEX IF NOT EXISTS idx_pos_void_tenant_date
    ON pos.void_log (tenant_id, voided_at DESC);

ALTER TABLE pos.void_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.void_log FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.void_log
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.void_log
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.void_log TO datapulse;
GRANT SELECT ON TABLE pos.void_log TO datapulse_reader;

COMMENT ON TABLE pos.void_log IS
    'Audit trail for voided transactions. Append-only — records are never deleted. RLS-protected.';
