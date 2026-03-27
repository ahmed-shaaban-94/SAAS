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

-- Product dimension from drug_code
-- SCD Type 1: latest attribute wins (by most recent invoice_date)
-- Includes buyer (business owner of the product relationship)

WITH ranked AS (
    SELECT
        tenant_id,
        drug_code,
        drug_name,
        drug_brand,
        drug_cluster,
        drug_status,
        is_temporary,
        drug_category,
        drug_subcategory,
        drug_division,
        drug_segment,
        buyer,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, drug_code
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE drug_code IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY tenant_id, drug_code)::INT AS product_key,
    tenant_id,
    drug_code,
    drug_name,
    drug_brand,
    drug_cluster,
    drug_status,
    is_temporary,
    drug_category,
    drug_subcategory,
    drug_division,
    drug_segment,
    buyer
FROM ranked
WHERE rn = 1
