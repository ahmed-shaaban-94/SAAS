-- Migration: 052 — Batch/lot master with expiry tracking
-- Layer: Bronze
-- Idempotent.

CREATE TABLE IF NOT EXISTS bronze.batches (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id        INT NOT NULL,
    source_file      TEXT NOT NULL DEFAULT 'manual',
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    drug_code        TEXT NOT NULL,
    site_code        TEXT NOT NULL,
    batch_number     TEXT NOT NULL,
    expiry_date      DATE NOT NULL,
    initial_quantity NUMERIC(18,4) NOT NULL,
    current_quantity NUMERIC(18,4) NOT NULL,
    unit_cost        NUMERIC(18,4),
    status           TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active', 'near_expiry', 'expired', 'quarantined', 'written_off')),
    quarantine_date  DATE,
    write_off_date   DATE,
    write_off_reason TEXT,
    UNIQUE (tenant_id, drug_code, site_code, batch_number)
);

CREATE INDEX IF NOT EXISTS idx_batches_tenant_expiry
    ON bronze.batches(tenant_id, expiry_date);
CREATE INDEX IF NOT EXISTS idx_batches_tenant_status
    ON bronze.batches(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_batches_tenant_drug_site
    ON bronze.batches(tenant_id, drug_code, site_code);

ALTER TABLE bronze.batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE bronze.batches FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON bronze.batches
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON bronze.batches
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT ON TABLE bronze.batches TO datapulse_reader;

COMMENT ON TABLE bronze.batches IS
    'Batch/lot master with expiry dates, quantities, and lifecycle status. RLS-protected.';
