-- Migration: 103 — Commission rate + daily sales target (#627 Phase D4)
-- Layer: POS operational
-- Idempotent.
--
-- Context
-- -------
-- Phase D4's TopStatusStrip renders a gold commission pill and a daily-target
-- trophy bar (§1.1). Two new storage locations close the data gap:
--
-- 1. ``pos.product_catalog_meta.commission_rate`` — per-drug commission rate
--    (0 ≤ rate ≤ 1, NUMERIC(5,4) gives four decimals of precision). Drugs
--    without a row return 0 via LEFT JOIN so the default is "no commission".
--
-- 2. ``pos.terminal_config`` — persistent per-terminal configuration keyed
--    by ``(tenant_id, terminal_name)``. Holds the daily_sales_target_egp.
--    We deliberately avoid ``pos.terminal_sessions`` because that table
--    stores one row per open/close cycle (new row every morning), so the
--    target would silently reset to NULL on every re-open. We also avoid
--    per-shift storage because the store manager sets a target per register,
--    not per cashier. ``terminal_name`` is the stable identifier.
--
-- Commission earned is NOT stored — it's derived at query time by summing
-- ``line_total × commission_rate`` over completed transactions in the shift
-- window. Keeping it derived means back-office corrections to commission_rate
-- reflow through every live shift's pill automatically. The UI gets
-- live updates by polling GET /pos/shifts/current after each sale
-- rather than by a server-emitted event (simpler, same latency).

-- ---------------------------------------------------------------------------
-- 1. Per-drug commission rate
-- ---------------------------------------------------------------------------

ALTER TABLE pos.product_catalog_meta
    ADD COLUMN IF NOT EXISTS commission_rate NUMERIC(5,4) NOT NULL DEFAULT 0
        CHECK (commission_rate >= 0 AND commission_rate <= 1);

COMMENT ON COLUMN pos.product_catalog_meta.commission_rate IS
    'Per-drug commission rate applied to line_total at shift-summary time. 0.0000-1.0000 (i.e. 0%-100%). LEFT JOIN on catalog_meta defaults absent drugs to 0. (#627)';

-- ---------------------------------------------------------------------------
-- 2. Per-terminal persistent config (survives session open/close)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pos.terminal_config (
    tenant_id               INT  NOT NULL,
    terminal_name           TEXT NOT NULL,
    daily_sales_target_egp  NUMERIC(18,4)
        CHECK (daily_sales_target_egp IS NULL OR daily_sales_target_egp >= 0),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, terminal_name)
);

ALTER TABLE pos.terminal_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos.terminal_config FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON pos.terminal_config
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON pos.terminal_config
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE pos.terminal_config TO datapulse;
GRANT SELECT ON TABLE pos.terminal_config TO datapulse_reader;

COMMENT ON TABLE pos.terminal_config IS
    'Persistent per-terminal configuration. Keyed by (tenant_id, terminal_name) which is stable across pos.terminal_sessions open/close cycles. Holds the daily sales target and any future per-register settings (default tax rate, printer ID, etc.). RLS-scoped. (#627)';
COMMENT ON COLUMN pos.terminal_config.daily_sales_target_egp IS
    'Optional daily sales target in EGP for the trophy bar. NULL = no target set; UI hides the bar. (#627)';
