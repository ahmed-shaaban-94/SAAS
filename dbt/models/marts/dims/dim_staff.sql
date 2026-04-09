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
            "CREATE INDEX IF NOT EXISTS idx_dim_staff_staff_id_tenant ON {{ this }} (staff_id, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_dim_staff_staff_key ON {{ this }} (staff_key)"
        ]
    )
}}

-- Staff/personnel dimension
-- SCD Type 1: latest attribute wins
-- key = -1 reserved for Unknown/Unassigned

WITH ranked AS (
    SELECT
        tenant_id,
        staff_id,
        staff_name,
        staff_position,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, staff_id
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE staff_id IS NOT NULL
)

SELECT
    ABS(('x' || LEFT(MD5(tenant_id::text || '|' || staff_id), 8))::BIT(32)::INT) AS staff_key,
    tenant_id,
    staff_id,
    staff_name,
    staff_position
FROM ranked
WHERE rn = 1

UNION ALL

SELECT
    -1                 AS staff_key,
    t.tenant_id,
    '__UNKNOWN__'      AS staff_id,
    'Unknown'          AS staff_name,
    'Unknown'          AS staff_position
FROM (SELECT DISTINCT tenant_id FROM {{ ref('stg_sales') }}) t
