-- Migration: 068 — Create `pos.receipts` table
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.receipts (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES pos.transactions(id),
    tenant_id      INT NOT NULL,
    format         TEXT NOT NULL CHECK (format IN ('thermal', 'pdf', 'email')),
    content        BYTEA,
    file_path      TEXT,
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_receipts_txn
    ON pos.receipts (transaction_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipts_tenant_format
    ON pos.receipts (tenant_id, format);

ALTER TABLE pos.receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.receipts FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.receipts
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.receipts
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT ON TABLE pos.receipts TO datapulse;
GRANT SELECT ON TABLE pos.receipts TO datapulse_reader;

COMMENT ON TABLE pos.receipts IS
    'Generated receipt artifacts — thermal (BYTEA), PDF (BYTEA), or email metadata. RLS-protected.';
