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

-- Staff/personnel dimension
-- SCD Type 1: latest attribute wins

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
    ROW_NUMBER() OVER (ORDER BY tenant_id, staff_id)::INT AS staff_key,
    tenant_id,
    staff_id,
    staff_name,
    staff_position
FROM ranked
WHERE rn = 1
