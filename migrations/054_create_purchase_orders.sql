-- Migration: 054 — Purchase order headers
-- Layer: Bronze
-- Idempotent.

CREATE TABLE IF NOT EXISTS bronze.purchase_orders (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id      INT NOT NULL,
    source_file    TEXT NOT NULL DEFAULT 'manual',
    loaded_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    po_number      TEXT NOT NULL,
    po_date        DATE NOT NULL,
    supplier_code  TEXT NOT NULL,
    site_code      TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'draft'
                   CHECK (status IN ('draft', 'submitted', 'partial', 'received', 'cancelled')),
    expected_date  DATE,
    total_amount   NUMERIC(18,4),
    notes          TEXT,
    created_by     TEXT,
    UNIQUE (tenant_id, po_number)
);

CREATE INDEX IF NOT EXISTS idx_purchase_orders_tenant_po
    ON bronze.purchase_orders(tenant_id, po_number);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_tenant_status
    ON bronze.purchase_orders(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_tenant_supplier
    ON bronze.purchase_orders(tenant_id, supplier_code);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_tenant_date
    ON bronze.purchase_orders(tenant_id, po_date DESC);

ALTER TABLE bronze.purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.purchase_orders FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.purchase_orders
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.purchase_orders
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.purchase_orders TO datapulse_reader;

COMMENT ON TABLE bronze.purchase_orders IS
    'Purchase order headers with status lifecycle (draft→received). RLS-protected.';
