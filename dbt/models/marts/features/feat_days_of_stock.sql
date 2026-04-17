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
            "CREATE INDEX IF NOT EXISTS idx_feat_days_of_stock_product ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_days_of_stock_site ON {{ this }} (tenant_id, site_key)"
        ]
    )
}}

-- Days of stock remaining = current_stock / avg_daily_dispense
-- Grain: one row per (tenant_id, product_key, site_key)

SELECT
    sl.tenant_id,
    sl.product_key,
    sl.site_key,
    sl.drug_code,
    sl.drug_name,
    sl.site_code,
    sl.site_name,
    sl.current_quantity,
    dr.avg_daily_dispense,
    CASE
        WHEN dr.avg_daily_dispense IS NULL OR dr.avg_daily_dispense = 0 THEN NULL
        ELSE ROUND(sl.current_quantity / dr.avg_daily_dispense, 1)
    END AS days_of_stock,
    dr.avg_weekly_dispense,
    dr.avg_monthly_dispense,
    dr.last_dispense_date_key
FROM {{ ref('agg_stock_levels') }} sl
LEFT JOIN {{ ref('feat_dispense_rate') }} dr
    ON sl.product_key = dr.product_key
    AND sl.site_key = dr.site_key
    AND sl.tenant_id = dr.tenant_id
