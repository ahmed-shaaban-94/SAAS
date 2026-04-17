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
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_recon_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_recon_product ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_recon_date ON {{ this }} (count_date)"
        ]
    )
}}

-- Stock reconciliation: physical counts vs calculated stock levels
-- Grain: one row per (tenant_id, product_key, site_key, count_date)
-- variance = counted_quantity - calculated_quantity
-- variance_pct = variance / calculated_quantity (NULL if calculated = 0)

SELECT
    c.tenant_id,
    c.product_key,
    c.site_key,
    c.count_date,
    p.drug_code,
    p.drug_name,
    s.site_code,
    s.site_name,
    ROUND(c.counted_quantity, 4)                                                AS counted_quantity,
    ROUND(COALESCE(sl.current_quantity, 0), 4)                                  AS calculated_quantity,
    ROUND(c.counted_quantity - COALESCE(sl.current_quantity, 0), 4)             AS variance,
    ROUND(
        (c.counted_quantity - COALESCE(sl.current_quantity, 0))
        / NULLIF(COALESCE(sl.current_quantity, 0), 0),
        4
    )                                                                           AS variance_pct

FROM {{ ref('fct_inventory_counts') }} c
LEFT JOIN {{ ref('agg_stock_levels') }} sl
    ON c.product_key = sl.product_key
   AND c.site_key    = sl.site_key
   AND c.tenant_id   = sl.tenant_id
INNER JOIN {{ ref('dim_product') }} p ON c.product_key = p.product_key AND c.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }}    s ON c.site_key    = s.site_key    AND c.tenant_id = s.tenant_id
WHERE c.product_key != -1
  AND c.site_key    != -1
