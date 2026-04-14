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
            "CREATE INDEX IF NOT EXISTS idx_agg_expiry_summary_tenant_site ON {{ this }} (tenant_id, site_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_expiry_summary_bucket ON {{ this }} (expiry_bucket)"
        ]
    )
}}

-- Grain: one row per (tenant_id, site_key, expiry_bucket)
-- Counts batches by expiry status per site

SELECT
    b.tenant_id,
    s.site_key,
    s.site_code,
    s.site_name,
    b.computed_status AS expiry_bucket,
    COUNT(*) AS batch_count,
    SUM(b.current_quantity) AS total_quantity,
    SUM(b.current_quantity * COALESCE(b.unit_cost, 0)) AS total_value
FROM {{ ref('dim_batch') }} b
INNER JOIN {{ ref('dim_site') }} s
    ON b.site_code = s.site_code
   AND b.tenant_id = s.tenant_id
WHERE b.batch_key != -1
GROUP BY 1, 2, 3, 4, 5
