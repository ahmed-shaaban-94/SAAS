-- Migration: 106 — extend pos.promotions scope with 'active_ingredient'
-- Layer: POS operational (extension to migrations 091 + 104).
-- Idempotent.
--
-- Adds:
--   1. 'active_ingredient' to the scope CHECK constraint on pos.promotions.
--   2. pos.promotion_active_ingredients join table.
--
-- Eligibility matching uses pos.product_catalog_meta.active_ingredient
-- (added in migration 101) for the JOIN at query time.
-- The column is case-insensitive (LOWER both sides).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Extend scope CHECK constraint (idempotent: drop-if-exists + re-add)
-- ─────────────────────────────────────────────────────────────────────────────

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
        CHECK (scope IN ('all', 'items', 'category', 'brand', 'active_ingredient'));
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. pos.promotion_active_ingredients
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pos.promotion_active_ingredients (
    promotion_id        BIGINT NOT NULL REFERENCES pos.promotions(id) ON DELETE CASCADE,
    active_ingredient   TEXT   NOT NULL,
    PRIMARY KEY (promotion_id, active_ingredient)
);

CREATE INDEX IF NOT EXISTS idx_pos_promo_active_ingredient
    ON pos.promotion_active_ingredients (active_ingredient);

ALTER TABLE pos.promotion_active_ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.promotion_active_ingredients FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.promotion_active_ingredients
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.promotion_active_ingredients
        FOR SELECT TO datapulse_reader USING (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.promotion_active_ingredients TO datapulse;
GRANT SELECT                           ON TABLE pos.promotion_active_ingredients TO datapulse_reader;

COMMENT ON TABLE pos.promotion_active_ingredients IS
    'Active-ingredient scope targets for pos.promotions. Matched against '
    'pos.product_catalog_meta.active_ingredient (case-insensitive) at '
    'eligibility time. Added in migration 106.';
