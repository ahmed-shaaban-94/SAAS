-- Migration: 053 — Supplier directory
-- Layer: Bronze
-- Idempotent.

CREATE TABLE IF NOT EXISTS bronze.suppliers (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           INT NOT NULL,
    source_file         TEXT NOT NULL DEFAULT 'manual',
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    supplier_code       TEXT NOT NULL,
    supplier_name       TEXT NOT NULL,
    contact_name        TEXT,
    contact_phone       TEXT,
    contact_email       TEXT,
    address             TEXT,
    payment_terms_days  INT DEFAULT 30,
    lead_time_days      INT DEFAULT 7,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    notes               TEXT,
    UNIQUE (tenant_id, supplier_code)
);

CREATE INDEX IF NOT EXISTS idx_suppliers_tenant_code
    ON bronze.suppliers(tenant_id, supplier_code);
CREATE INDEX IF NOT EXISTS idx_suppliers_tenant_active
    ON bronze.suppliers(tenant_id, is_active);

ALTER TABLE bronze.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.suppliers FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.suppliers
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.suppliers
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.suppliers TO datapulse_reader;

COMMENT ON TABLE bronze.suppliers IS
    'Supplier directory with contact info and payment terms. RLS-protected.';
