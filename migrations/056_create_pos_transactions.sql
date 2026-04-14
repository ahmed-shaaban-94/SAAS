-- Migration: 056 — POS transaction records (design-only, empty until POS integration)
-- Layer: Bronze
-- Idempotent.

CREATE TABLE IF NOT EXISTS bronze.pos_transactions (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL,
    source_type      TEXT NOT NULL DEFAULT 'pos_api'
                     CHECK (source_type IN ('pos_api', 'manual', 'excel')),
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    transaction_id   TEXT NOT NULL,
    transaction_date TIMESTAMPTZ NOT NULL,
    site_code        TEXT NOT NULL,
    register_id      TEXT,
    cashier_id       TEXT,
    customer_id      TEXT,
    drug_code        TEXT NOT NULL,
    batch_number     TEXT,
    quantity         NUMERIC(18,4) NOT NULL,
    unit_price       NUMERIC(18,4) NOT NULL,
    discount         NUMERIC(18,4) DEFAULT 0,
    net_amount       NUMERIC(18,4) NOT NULL,
    payment_method   TEXT CHECK (payment_method IN ('cash', 'card', 'insurance', 'mixed')),
    insurance_no     TEXT,
    is_return        BOOLEAN NOT NULL DEFAULT false,
    pharmacist_id    TEXT,
    UNIQUE (tenant_id, transaction_id, drug_code)
);

CREATE INDEX IF NOT EXISTS idx_pos_transactions_tenant_date
    ON bronze.pos_transactions(tenant_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_pos_transactions_tenant_drug
    ON bronze.pos_transactions(tenant_id, drug_code);
CREATE INDEX IF NOT EXISTS idx_pos_transactions_tenant_site
    ON bronze.pos_transactions(tenant_id, site_code);

ALTER TABLE bronze.pos_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.pos_transactions FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.pos_transactions
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.pos_transactions
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.pos_transactions TO datapulse_reader;

COMMENT ON TABLE bronze.pos_transactions IS
    'POS transaction records — design-only table, populated when POS integration is configured. RLS-protected.';
