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
            "CREATE INDEX IF NOT EXISTS idx_dim_site_site_code_tenant ON {{ this }} (site_code, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_dim_site_site_key ON {{ this }} (site_key)"
        ]
    )
}}

-- Site/location dimension
-- SCD Type 1: latest attribute wins
-- Includes area_manager (site-level geographic grouping)
-- Includes governorate / governorate_ar for Egypt shape map in Power BI
-- key = -1 reserved for Unknown/Unassigned

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
),

sites AS (
    SELECT
        ABS(('x' || LEFT(MD5(tenant_id::text || '|' || site_code), 8))::BIT(32)::INT) AS site_key,
        tenant_id,
        site_code,
        site_name,
        area_manager
    FROM ranked
    WHERE rn = 1
)

SELECT
    site_key,
    tenant_id,
    site_code,
    site_name,
    area_manager,
    -- Governorate mapping for Egypt shape map (Power BI)
    -- Uses governorate_map macro to avoid duplicating ~150-line CASE blocks
    {{ governorate_map('site_name', 'area_manager', 'en') }} AS governorate,
    {{ governorate_map('site_name', 'area_manager', 'ar') }} AS governorate_ar
FROM sites

UNION ALL

SELECT
    -1                 AS site_key,
    1                  AS tenant_id,
    '__UNKNOWN__'      AS site_code,
    'Unknown'          AS site_name,
    'Unknown'          AS area_manager,
    'Unknown'          AS governorate,
    'Unknown'          AS governorate_ar
