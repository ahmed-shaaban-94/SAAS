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
            "CREATE INDEX IF NOT EXISTS idx_feat_expiry_alerts_tenant_level ON {{ this }} (tenant_id, alert_level)",
            "CREATE INDEX IF NOT EXISTS idx_feat_expiry_alerts_expiry ON {{ this }} (expiry_date)"
        ]
    )
}}

-- Batches expiring within 30, 60, 90 days
-- Grain: one row per batch with alert level

SELECT
    b.tenant_id,
    b.batch_key,
    b.drug_code,
    p.drug_name,
    p.drug_brand,
    b.site_code,
    b.batch_number,
    b.expiry_date,
    b.current_quantity,
    b.days_to_expiry,
    CASE
        WHEN b.days_to_expiry <= 0 THEN 'expired'
        WHEN b.days_to_expiry <= 30 THEN 'critical'
        WHEN b.days_to_expiry <= 60 THEN 'warning'
        WHEN b.days_to_expiry <= 90 THEN 'caution'
        ELSE 'safe'
    END AS alert_level
FROM {{ ref('dim_batch') }} b
INNER JOIN {{ ref('dim_product') }} p
    ON b.drug_code = p.drug_code
   AND b.tenant_id = p.tenant_id
WHERE b.batch_key != -1
  AND b.current_quantity > 0
