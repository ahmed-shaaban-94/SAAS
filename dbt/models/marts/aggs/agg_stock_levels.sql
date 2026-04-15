{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_product ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_site ON {{ this }} (site_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_drug_code ON {{ this }} (drug_code)"
        ]
    )
}}

-- Current stock levels per product per site
-- Grain: one row per (tenant_id, product_key, site_key)
-- current_quantity = SUM of all movement quantities (receipts+, dispenses-, adjustments+/-, returns+)

SELECT
    m.tenant_id,
    m.product_key,
    m.site_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    s.site_code,
    s.site_name,
    SUM(m.quantity)                                                                             AS current_quantity,
    SUM(CASE WHEN m.movement_type = 'receipt'
        THEN m.quantity ELSE 0 END)                                                             AS total_received,
    SUM(CASE WHEN m.movement_type = 'dispense'
        THEN ABS(m.quantity) ELSE 0 END)                                                        AS total_dispensed,
    SUM(CASE WHEN m.movement_type IN ('damage', 'shrinkage', 'write_off')
        THEN ABS(m.quantity) ELSE 0 END)                                                        AS total_wastage,
    MAX(m.movement_date)                                                                        AS last_movement_date

FROM {{ ref('fct_stock_movements') }} m
INNER JOIN {{ ref('dim_product') }} p ON m.product_key = p.product_key AND m.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }}    s ON m.site_key    = s.site_key    AND m.tenant_id = s.tenant_id
WHERE m.product_key != -1
  AND m.site_key    != -1

GROUP BY
    m.tenant_id,
    m.product_key,
    m.site_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    s.site_code,
    s.site_name
