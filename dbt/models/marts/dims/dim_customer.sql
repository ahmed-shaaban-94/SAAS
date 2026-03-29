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

-- Customer dimension
-- SCD Type 1: latest attribute wins
-- Partitioned by (tenant_id, customer_id) for multi-tenant correctness
-- key = -1 reserved for Unknown/Unassigned

WITH ranked AS (
    SELECT
        tenant_id,
        customer_id,
        customer_name,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, customer_id
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE customer_id IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY tenant_id, customer_id)::INT AS customer_key,
    tenant_id,
    customer_id,
    customer_name
FROM ranked
WHERE rn = 1

UNION ALL

SELECT
    -1                 AS customer_key,
    NULL::INT          AS tenant_id,
    '__UNKNOWN__'      AS customer_id,
    'Unknown'          AS customer_name
