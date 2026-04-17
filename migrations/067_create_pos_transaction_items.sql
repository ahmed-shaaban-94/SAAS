-- Migration: 067 — Create `pos.transaction_items` table
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.transaction_items (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES pos.transactions(id) ON DELETE CASCADE,
    tenant_id      INT NOT NULL,
    drug_code      TEXT NOT NULL,
    drug_name      TEXT NOT NULL,
    batch_number   TEXT,
    expiry_date    DATE,
    quantity       NUMERIC(18,4) NOT NULL,
    unit_price     NUMERIC(18,4) NOT NULL,
    discount       NUMERIC(18,4) NOT NULL DEFAULT 0,
    line_total     NUMERIC(18,4) NOT NULL,
    is_controlled  BOOLEAN NOT NULL DEFAULT false,
    pharmacist_id  TEXT,
    loaded_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_items_txn
    ON pos.transaction_items (transaction_id);
CREATE INDEX IF NOT EXISTS idx_pos_items_drug
    ON pos.transaction_items (tenant_id, drug_code);
CREATE INDEX IF NOT EXISTS idx_pos_items_tenant_expiry
    ON pos.transaction_items (tenant_id, expiry_date)
    WHERE expiry_date IS NOT NULL;

ALTER TABLE pos.transaction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.transaction_items FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.transaction_items
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.transaction_items
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.transaction_items TO datapulse;
GRANT SELECT ON TABLE pos.transaction_items TO datapulse_reader;

COMMENT ON TABLE pos.transaction_items IS
    'Line items for each POS transaction. Cascades on transaction delete. RLS-protected.';
