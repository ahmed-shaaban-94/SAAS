-- Migration: 112 — pharma.drug_catalog (SAP material master)
-- Layer: pharma
-- Idempotent.
--
-- Captures the schema drift from scripts/upload_drug_catalog.py which
-- created this table directly in production on 2026-04-25.
--
-- Purpose: stores SAP-keyed drug catalog (material_code, NOT EAN-13).
--          Distinct from pharma.drug_master which is EAN-13 keyed.
--          Future migration will add pharma.drug_alias to crosswalk
--          (tenant_id, source_code) -> drug_master.ean13.

CREATE SCHEMA IF NOT EXISTS pharma;

-- ─────────────────────────────────────────────────────────────────────────────
-- pharma.drug_catalog
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pharma.drug_catalog (
    material_code     TEXT          PRIMARY KEY,
    name_en           TEXT,
    price_egp         NUMERIC(18,4),
    active_ingredient TEXT,
    vendor_name       TEXT,
    division          TEXT,
    category          TEXT,
    subcategory       TEXT,
    segment           TEXT,
    container_form    TEXT,
    imported_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Widen pre-existing column from NUMERIC(10,2) -> NUMERIC(18,4) to satisfy
-- the project hard rule (financial cols = NUMERIC(18,4)). Idempotent: ALTER
-- on the same target type is a no-op.
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'pharma'
          AND table_name   = 'drug_catalog'
          AND column_name  = 'price_egp'
          AND numeric_precision = 10
    ) THEN
        ALTER TABLE pharma.drug_catalog
            ALTER COLUMN price_egp TYPE NUMERIC(18,4);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_drug_catalog_name_en -- migration-safety: ok
    ON pharma.drug_catalog (name_en);

CREATE INDEX IF NOT EXISTS idx_drug_catalog_ingredient -- migration-safety: ok
    ON pharma.drug_catalog (active_ingredient)
    WHERE active_ingredient IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_drug_catalog_category -- migration-safety: ok
    ON pharma.drug_catalog (category, subcategory);

-- Trigram index for ILIKE/% search (pg_trgm enabled in migration 018).
-- Catalog has 58k+ rows; without this, every search is a sequential scan.
CREATE INDEX IF NOT EXISTS idx_drug_catalog_name_trgm -- migration-safety: ok
    ON pharma.drug_catalog USING GIN (name_en gin_trgm_ops);

COMMENT ON TABLE pharma.drug_catalog IS
    'SAP material master export — pharma drug catalog. '
    'Keyed on SAP material_code (not EAN-13). '
    'Links to pharma.drug_master via drug_alias once barcodes are mapped. '
    'No RLS — shared catalog readable by all tenants. Added in migration 112.';

-- ─────────────────────────────────────────────────────────────────────────────
-- Grants
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_api') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pharma.drug_catalog TO datapulse_api;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_reader') THEN
        GRANT SELECT ON TABLE pharma.drug_catalog TO datapulse_reader;
    END IF;
END $$;
