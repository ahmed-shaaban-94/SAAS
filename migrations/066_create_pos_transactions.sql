-- Migration: 066 — Create `pos.transactions` table
-- Layer: POS operational
-- Idempotent.

CREATE TABLE IF NOT EXISTS pos.transactions (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id      INT NOT NULL,
    terminal_id    BIGINT NOT NULL REFERENCES pos.terminal_sessions(id),
    staff_id       TEXT NOT NULL,
    pharmacist_id  TEXT,
    customer_id    TEXT,
    site_code      TEXT NOT NULL,
    subtotal       NUMERIC(18,4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(18,4) NOT NULL DEFAULT 0,
    tax_total      NUMERIC(18,4) NOT NULL DEFAULT 0,
    grand_total    NUMERIC(18,4) NOT NULL DEFAULT 0,
    payment_method TEXT CHECK (payment_method IN ('cash', 'card', 'insurance', 'mixed')),
    status         TEXT NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft', 'completed', 'voided', 'returned')),
    receipt_number TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    loaded_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pos_txn_terminal_date
    ON pos.transactions (terminal_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pos_txn_tenant_status
    ON pos.transactions (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_pos_txn_tenant_date
    ON pos.transactions (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pos_txn_receipt
    ON pos.transactions (tenant_id, receipt_number)
    WHERE receipt_number IS NOT NULL;

ALTER TABLE pos.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.transactions FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.transactions
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.transactions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE ON TABLE pos.transactions TO datapulse;
GRANT SELECT ON TABLE pos.transactions TO datapulse_reader;

COMMENT ON TABLE pos.transactions IS
    'POS transaction headers — one row per checkout attempt. Financial totals in NUMERIC(18,4). RLS-protected.';
