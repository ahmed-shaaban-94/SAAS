{{
  config(
    materialized='table',
    schema='gold',
    post_hook=[
      "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
      "DROP POLICY IF EXISTS owner_all ON {{ this }}",
      "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
      "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
      "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
      "CREATE INDEX IF NOT EXISTS idx_agg_basket_margin_tenant_staff ON {{ this }} (tenant_id, staff_id)",
      "CREATE INDEX IF NOT EXISTS idx_agg_basket_margin_tenant_shift ON {{ this }} (tenant_id, shift_id)",
      "CREATE INDEX IF NOT EXISTS idx_agg_basket_margin_txn_date ON {{ this }} (txn_date)"
    ],
  )
}}

-- Per-cashier × per-shift × per-basket gross margin
-- Grain: one row per completed pos.transaction (basket)
-- Enables the POS Legend Q1 north-star metric: cashier margin contribution

SELECT
    t.tenant_id,
    t.shift_id,
    t.staff_id,
    t.id                                                          AS transaction_id,
    DATE_TRUNC('day', t.created_at)                              AS txn_date,
    SUM(ti.unit_price * ti.quantity)::NUMERIC(18, 4)             AS revenue,
    SUM(ti.cost_per_unit * ti.quantity)::NUMERIC(18, 4)          AS cost,
    SUM(
        (ti.unit_price - COALESCE(ti.cost_per_unit, 0)) * ti.quantity
    )::NUMERIC(18, 4)                                            AS gross_margin,
    CASE
        WHEN SUM(ti.unit_price * ti.quantity) > 0
        THEN ROUND(
            SUM(
                (ti.unit_price - COALESCE(ti.cost_per_unit, 0)) * ti.quantity
            ) / SUM(ti.unit_price * ti.quantity),
            4
        )
        ELSE NULL
    END                                                          AS margin_pct
FROM pos.transactions t
JOIN pos.transaction_items ti ON ti.transaction_id = t.id
WHERE t.status = 'completed'
GROUP BY 1, 2, 3, 4, 5
