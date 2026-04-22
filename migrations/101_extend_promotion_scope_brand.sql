-- Migration: 101 — extend pos.promotions scope enum with 'brand'
-- Layer: POS operational (extension to migration 091).
-- Idempotent.
--
-- Adds a new `pos.promotion_brands` join table so admins can target
-- promotions by drug_brand. Mirrors the existing `pos.promotion_categories`
-- table (scope='category') verbatim — same keys, same indexes, same RLS
-- policy shape. The eligibility query joins against `dim_product.drug_brand`
-- on the cart's drug_codes at runtime (see promotion_repository.list_eligible).
--
-- Design: 'active_ingredient' is NOT part of this migration. Adding it
-- requires extending `dim_product` with an `active_ingredient` column
-- first, which is a separate catalog-side change tracked as a follow-up
-- ticket.

-- 1. Extend the scope CHECK constraint on pos.promotions.
--    PostgreSQL does not support ALTER CHECK in-place, so we drop and
--    re-add the named constraint. Idempotent: guarded by pg_constraint lookup.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'pos.promotions'::regclass
           AND conname  = 'promotions_scope_check'
    ) THEN
        ALTER TABLE pos.promotions DROP CONSTRAINT promotions_scope_check;
    END IF;
    ALTER TABLE pos.promotions
        ADD CONSTRAINT promotions_scope_check
        CHECK (scope IN ('all', 'items', 'category', 'brand'));
END $$;

-- 2. New join table for brand-scope promotions.
--    Same shape as pos.promotion_categories: (promotion_id, brand_name).
--    brand_name is the raw drug_brand value from dim_product — case
--    preserved; matching is case-insensitive at query time.

CREATE TABLE IF NOT EXISTS pos.promotion_brands (
    promotion_id    BIGINT NOT NULL REFERENCES pos.promotions(id) ON DELETE CASCADE,
    brand_name      TEXT NOT NULL,
    PRIMARY KEY (promotion_id, brand_name)
);

CREATE INDEX IF NOT EXISTS idx_pos_promotion_brands_brand
    ON pos.promotion_brands (brand_name);

-- 3. RLS — child row of pos.promotions, inherits tenant scope via the FK.
--    Mirror the permissive policy shape used by pos.promotion_categories.

ALTER TABLE pos.promotion_brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_brands FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.promotion_brands
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.promotion_brands
        FOR SELECT TO datapulse_reader USING (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 4. Grants — same pattern as the existing promotion_* tables.

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.promotion_brands TO datapulse;
GRANT SELECT                           ON TABLE pos.promotion_brands TO datapulse_reader;

COMMENT ON TABLE pos.promotion_brands IS
    'Brand-scope target rows for pos.promotions. Matched against '
    'public_marts.dim_product.drug_brand at eligibility time. Added in '
    'migration 101 as an extension of the original scope enum (091).';
