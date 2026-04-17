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
            "CREATE INDEX IF NOT EXISTS idx_feat_stockout_risk_product ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_stockout_risk_level ON {{ this }} (tenant_id, risk_level)"
        ]
    )
}}

-- Products where days_of_stock < reorder_lead_time or current_quantity <= reorder_point
-- Uses reorder_config (application table, not dbt-managed) as a dbt source
-- Grain: one row per (tenant_id, product_key, site_key) at risk

SELECT
    dos.tenant_id,
    dos.product_key,
    dos.site_key,
    dos.drug_code,
    dos.drug_name,
    dos.site_code,
    dos.site_name,
    dos.current_quantity,
    dos.days_of_stock,
    dos.avg_daily_dispense,
    rc.reorder_point,
    rc.reorder_lead_days,
    rc.min_stock,
    CASE
        WHEN dos.current_quantity <= 0
            THEN 'stockout'
        WHEN dos.days_of_stock IS NOT NULL AND dos.days_of_stock < rc.reorder_lead_days
            THEN 'critical'
        WHEN dos.current_quantity <= rc.reorder_point
            THEN 'at_risk'
        ELSE 'safe'
    END AS risk_level,
    GREATEST(rc.reorder_point - dos.current_quantity, 0) AS suggested_reorder_qty
FROM {{ ref('feat_days_of_stock') }} dos
INNER JOIN {{ source('public', 'reorder_config') }} rc
    ON dos.drug_code = rc.drug_code
    AND dos.site_code = rc.site_code
    AND dos.tenant_id = rc.tenant_id
    AND rc.is_active = true
WHERE
    dos.current_quantity <= rc.reorder_point
    OR (dos.days_of_stock IS NOT NULL AND dos.days_of_stock < rc.reorder_lead_days)
