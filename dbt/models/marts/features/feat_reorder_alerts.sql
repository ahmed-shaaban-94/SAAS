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
            "CREATE INDEX IF NOT EXISTS idx_feat_reorder_alerts_product ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_reorder_alerts_level ON {{ this }} (tenant_id, risk_level)"
        ]
    )
}}

-- Active reorder alerts for dashboard display
-- Products below reorder_point that need ordering
-- Grain: one row per (tenant_id, product_key, site_key) with active alert

SELECT
    sr.tenant_id,
    sr.product_key,
    sr.site_key,
    sr.drug_code,
    sr.drug_name,
    sr.site_code,
    sr.site_name,
    sr.current_quantity,
    sr.reorder_point,
    sr.min_stock,
    sr.risk_level,
    sr.suggested_reorder_qty,
    sr.days_of_stock,
    sr.avg_daily_dispense
FROM {{ ref('feat_stockout_risk') }} sr
WHERE sr.risk_level IN ('stockout', 'critical', 'at_risk')
ORDER BY
    CASE sr.risk_level
        WHEN 'stockout' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'at_risk'  THEN 3
    END,
    sr.current_quantity ASC
