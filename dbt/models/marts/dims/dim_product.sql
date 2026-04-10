{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'product_key'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_dim_product_drug_code_tenant ON {{ this }} (drug_code, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_dim_product_product_key ON {{ this }} (product_key)"
        ]
    )
}}

-- Product dimension from drug_code
-- SCD Type 1: latest attribute wins (by most recent invoice_date)
-- Includes buyer (business owner of the product relationship)
-- key = -1 reserved for Unknown/Unassigned

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
    {% if is_incremental() %}
      AND loaded_at >= (SELECT MAX(loaded_at) - INTERVAL '7 days' FROM {{ ref('stg_sales') }})
    {% endif %}
)

SELECT
    ABS(('x' || LEFT(MD5(r.tenant_id::text || '|' || r.drug_code), 8))::BIT(32)::INT) AS product_key,
    r.tenant_id,
    r.drug_code,
    r.drug_name,
    r.drug_brand,
    r.drug_cluster,
    r.drug_status,
    r.is_temporary,
    r.drug_category,
    r.drug_subcategory,
    r.drug_division,
    r.drug_segment,
    r.buyer,
    COALESCE(o.origin, 'Other') AS origin
FROM ranked r
LEFT JOIN {{ ref('seed_division_origin') }} o ON r.drug_division = o.division
WHERE r.rn = 1

{% if not is_incremental() %}
UNION ALL

SELECT
    -1                  AS product_key,
    t.tenant_id,
    '__UNKNOWN__'       AS drug_code,
    'Unknown'           AS drug_name,
    'Unknown'           AS drug_brand,
    'Unknown'           AS drug_cluster,
    'Unknown'           AS drug_status,
    FALSE               AS is_temporary,
    'Unknown'           AS drug_category,
    'Unknown'           AS drug_subcategory,
    'Unknown'           AS drug_division,
    'Unknown'           AS drug_segment,
    'Unknown'           AS buyer,
    'Other'             AS origin
FROM (SELECT DISTINCT tenant_id FROM {{ ref('stg_sales') }}) t
{% endif %}
