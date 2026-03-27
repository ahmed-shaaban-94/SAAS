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
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)"
        ]
    )
}}

-- Site/location dimension
-- SCD Type 1: latest attribute wins
-- Includes area_manager (site-level geographic grouping)

WITH ranked AS (
    SELECT
        tenant_id,
        site_code,
        site_name,
        area_manager,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, site_code
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE site_code IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY tenant_id, site_code)::INT AS site_key,
    tenant_id,
    site_code,
    site_name,
    area_manager
FROM ranked
WHERE rn = 1
