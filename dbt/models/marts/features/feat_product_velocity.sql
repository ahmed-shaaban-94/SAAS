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
            "CREATE INDEX IF NOT EXISTS idx_feat_product_velocity_product ON {{ this }} (tenant_id, product_key)",
            "CREATE INDEX IF NOT EXISTS idx_feat_product_velocity_class ON {{ this }} (tenant_id, velocity_class)"
        ]
    )
}}

-- Extends feat_product_lifecycle with dispense velocity classification
-- fast/normal/slow/dead mover based on avg_daily_dispense relative to category average
-- Grain: one row per (tenant_id, product_key)

WITH category_avg AS (
    SELECT
        dr.tenant_id,
        p.drug_category,
        AVG(dr.avg_daily_dispense) AS category_avg_daily
    FROM {{ ref('feat_dispense_rate') }} dr
    INNER JOIN {{ ref('dim_product') }} p
        ON dr.product_key = p.product_key AND dr.tenant_id = p.tenant_id
    GROUP BY 1, 2
)

SELECT
    dr.tenant_id,
    dr.product_key,
    dr.drug_code,
    dr.drug_name,
    dr.drug_brand,
    p.drug_category,
    lc.lifecycle_phase,
    dr.avg_daily_dispense,
    ca.category_avg_daily,
    CASE
        WHEN dr.avg_daily_dispense >= ca.category_avg_daily * 1.5 THEN 'fast_mover'
        WHEN dr.avg_daily_dispense >= ca.category_avg_daily * 0.5 THEN 'normal_mover'
        WHEN dr.avg_daily_dispense > 0                            THEN 'slow_mover'
        ELSE 'dead_stock'
    END AS velocity_class
FROM {{ ref('feat_dispense_rate') }} dr
INNER JOIN {{ ref('dim_product') }} p
    ON dr.product_key = p.product_key AND dr.tenant_id = p.tenant_id
LEFT JOIN {{ ref('feat_product_lifecycle') }} lc
    ON dr.product_key = lc.product_key AND dr.tenant_id = lc.tenant_id
LEFT JOIN category_avg ca
    ON dr.tenant_id = ca.tenant_id AND p.drug_category = ca.drug_category
