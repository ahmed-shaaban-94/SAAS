-- Migration: 101 — POS-owned product catalog metadata (#623 Phase D2 ClinicalPanel)
-- Layer: POS operational
-- Idempotent.
--
-- Context
-- -------
-- `public_marts.dim_product` is dbt-materialized from `stg_sales` and gets
-- rebuilt on every dbt run; any column we add directly to it would be wiped.
-- POS needs mutable product-level metadata (counseling text for the clinical
-- panel, active_ingredient for generic-alternative lookup, and — in a later
-- migration — commission_rate for #627). We keep that metadata here in a
-- POS-owned sidecar table keyed by (tenant_id, drug_code) and LEFT JOIN it
-- into drug-detail reads.
--
-- Additional table `pos.cross_sell_rules` provides the static rules that
-- drive the "suggest a probiotic with this antibiotic" UX until the AI-driven
-- version lands (#623 "Initial implementation can be a static rules table").

CREATE TABLE IF NOT EXISTS pos.product_catalog_meta (
    tenant_id         INT  NOT NULL,
    drug_code         TEXT NOT NULL,
    counseling_text   TEXT,
    active_ingredient TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, drug_code)
);

CREATE INDEX IF NOT EXISTS idx_pos_product_meta_active_ingredient
    ON pos.product_catalog_meta (tenant_id, active_ingredient)
    WHERE active_ingredient IS NOT NULL;

ALTER TABLE pos.product_catalog_meta ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.product_catalog_meta FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.product_catalog_meta
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.product_catalog_meta
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.product_catalog_meta TO datapulse;
GRANT SELECT ON TABLE pos.product_catalog_meta TO datapulse_reader;

COMMENT ON TABLE pos.product_catalog_meta IS
    'POS-owned per-drug metadata (counseling text, active ingredient, commission rate). Survives dbt rebuilds of dim_product. RLS-scoped per tenant. (#623, #627)';
COMMENT ON COLUMN pos.product_catalog_meta.counseling_text IS
    'Free-text counseling tip shown in the POS clinical panel. Nullable — drugs without guidance return null (frontend hides the card). (#623)';
COMMENT ON COLUMN pos.product_catalog_meta.active_ingredient IS
    'Canonical active-ingredient name used for generic-alternatives lookup. Two drugs with matching tenant_id + active_ingredient are treated as substitutes. (#623)';


-- ---------------------------------------------------------------------------
-- Cross-sell rules — static "if antibiotic then suggest probiotic" pairings
-- until the AI-driven recommender lands.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pos.cross_sell_rules (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id           INT  NOT NULL,
    primary_drug_code   TEXT NOT NULL,
    suggested_drug_code TEXT NOT NULL,
    reason              TEXT NOT NULL,
    reason_tag          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cross_sell_pair UNIQUE (tenant_id, primary_drug_code, suggested_drug_code)
);

CREATE INDEX IF NOT EXISTS idx_cross_sell_primary
    ON pos.cross_sell_rules (tenant_id, primary_drug_code);

ALTER TABLE pos.cross_sell_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.cross_sell_rules FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.cross_sell_rules
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.cross_sell_rules
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.cross_sell_rules TO datapulse;
GRANT SELECT ON TABLE pos.cross_sell_rules TO datapulse_reader;

COMMENT ON TABLE pos.cross_sell_rules IS
    'Static cross-sell pairings for the POS clinical panel. One row = "when drug A is in the cart, suggest drug B with this reason". AI-driven version is a later iteration. (#623)';
COMMENT ON COLUMN pos.cross_sell_rules.reason_tag IS
    'Short tag used for UI colour-coding (e.g. ROUTE, PROTECT). Free-text — the frontend has a fallback style for unrecognised tags. (#623)';
