-- Migration: 055 — Purchase order line items
-- Layer: Bronze
-- Idempotent.

CREATE TABLE IF NOT EXISTS bronze.po_lines (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id         INT NOT NULL,
    loaded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    po_number         TEXT NOT NULL,
    line_number       INT NOT NULL,
    drug_code         TEXT NOT NULL,
    ordered_quantity  NUMERIC(18,4) NOT NULL,
    unit_price        NUMERIC(18,4) NOT NULL,
    received_quantity NUMERIC(18,4) NOT NULL DEFAULT 0,
    line_total        NUMERIC(18,4) GENERATED ALWAYS AS (ordered_quantity * unit_price) STORED,
    UNIQUE (tenant_id, po_number, line_number)
);

CREATE INDEX IF NOT EXISTS idx_po_lines_tenant_po
    ON bronze.po_lines(tenant_id, po_number);
CREATE INDEX IF NOT EXISTS idx_po_lines_tenant_drug
    ON bronze.po_lines(tenant_id, drug_code);

ALTER TABLE bronze.po_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.po_lines FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.po_lines
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.po_lines
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.po_lines TO datapulse_reader;

COMMENT ON TABLE bronze.po_lines IS
    'Purchase order line items with generated line_total (ordered_quantity * unit_price). RLS-protected.';
