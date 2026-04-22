-- Migration: 110 — extend pos.cross_sell_rules for MBA-learned rules
-- Idempotent.
--
-- Adds three columns so the Market Basket Analysis job can write
-- data-driven rules alongside the existing manual ones:
--   source        — 'manual' (human-entered) | 'learned' (MBA job)
--   confidence    — P(B|A): fraction of A-baskets that also contain B
--   support_count — absolute count of baskets containing both A and B
--   updated_at    — when this row was last written (learning job uses this)

ALTER TABLE pos.cross_sell_rules
    ADD COLUMN IF NOT EXISTS source        TEXT         NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS confidence    NUMERIC(6,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS support_count INT          NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now();

COMMENT ON COLUMN pos.cross_sell_rules.source IS
    '''manual'' = entered by a pharmacist/admin; ''learned'' = written by the MBA background job.';
COMMENT ON COLUMN pos.cross_sell_rules.confidence IS
    'P(suggested | primary): fraction of completed baskets containing primary that also contain suggested.';
COMMENT ON COLUMN pos.cross_sell_rules.support_count IS
    'Absolute number of completed baskets where both drugs appeared together.';
COMMENT ON COLUMN pos.cross_sell_rules.updated_at IS
    'Last time this row was written. The MBA job uses this to detect stale learned rules.';
