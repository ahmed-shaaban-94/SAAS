-- Migration: 050 — Pharmaceutical inventory bronze tables
-- Layer: Bronze
-- Idempotent.

-- ============================================================
-- Table: bronze.stock_receipts
-- Raw stock receipt records from Excel import or manual entry
-- ============================================================
CREATE TABLE IF NOT EXISTS bronze.stock_receipts (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL,
    source_file      TEXT NOT NULL,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    receipt_date     DATE,
    receipt_reference TEXT,          -- supplier delivery note / GRN number
    drug_code        TEXT,           -- joins to dim_product
    site_code        TEXT,           -- joins to dim_site
    batch_number     TEXT,
    expiry_date      DATE,
    quantity         NUMERIC(18,4),
    unit_cost        NUMERIC(18,4),
    supplier_code    TEXT,
    po_reference     TEXT,
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_stock_receipts_tenant
    ON bronze.stock_receipts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stock_receipts_tenant_drug_site
    ON bronze.stock_receipts(tenant_id, drug_code, site_code);
CREATE INDEX IF NOT EXISTS idx_stock_receipts_loaded
    ON bronze.stock_receipts(loaded_at DESC);

ALTER TABLE bronze.stock_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.stock_receipts FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.stock_receipts
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.stock_receipts
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.stock_receipts TO datapulse_reader;

COMMENT ON TABLE bronze.stock_receipts IS
    'Raw stock receipt records from Excel import or manual entry. RLS-protected.';

-- ============================================================
-- Table: bronze.stock_adjustments
-- Manual stock adjustments (damage, shrinkage, transfers, corrections)
-- ============================================================
CREATE TABLE IF NOT EXISTS bronze.stock_adjustments (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL,
    source_file      TEXT NOT NULL,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    adjustment_date  DATE,
    adjustment_type  TEXT CHECK (adjustment_type IN (
                         'damage', 'shrinkage', 'transfer_in',
                         'transfer_out', 'correction', 'write_off'
                     )),
    drug_code        TEXT,
    site_code        TEXT,
    batch_number     TEXT,
    quantity         NUMERIC(18,4),  -- positive = add, negative = remove
    reason           TEXT,
    authorized_by    TEXT,
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_stock_adjustments_tenant
    ON bronze.stock_adjustments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_stock_adjustments_tenant_drug_site
    ON bronze.stock_adjustments(tenant_id, drug_code, site_code);
CREATE INDEX IF NOT EXISTS idx_stock_adjustments_loaded
    ON bronze.stock_adjustments(loaded_at DESC);

ALTER TABLE bronze.stock_adjustments ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.stock_adjustments FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.stock_adjustments
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.stock_adjustments
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.stock_adjustments TO datapulse_reader;

COMMENT ON TABLE bronze.stock_adjustments IS
    'Manual stock adjustment records (damage, shrinkage, transfers, corrections). RLS-protected.';

-- ============================================================
-- Table: bronze.inventory_counts
-- Physical stock count records for reconciliation
-- ============================================================
CREATE TABLE IF NOT EXISTS bronze.inventory_counts (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL,
    source_file      TEXT NOT NULL,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    count_date       DATE,
    drug_code        TEXT,
    site_code        TEXT,
    batch_number     TEXT,
    counted_quantity NUMERIC(18,4),
    counted_by       TEXT,
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_inventory_counts_tenant
    ON bronze.inventory_counts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inventory_counts_tenant_drug_site
    ON bronze.inventory_counts(tenant_id, drug_code, site_code);
CREATE INDEX IF NOT EXISTS idx_inventory_counts_loaded
    ON bronze.inventory_counts(loaded_at DESC);

ALTER TABLE bronze.inventory_counts ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.inventory_counts FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.inventory_counts
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.inventory_counts
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.inventory_counts TO datapulse_reader;

COMMENT ON TABLE bronze.inventory_counts IS
    'Physical stock count records for inventory reconciliation. RLS-protected.';
