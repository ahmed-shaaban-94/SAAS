{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Product dimension from drug_code
-- SCD Type 1: latest attribute wins (by most recent invoice_date)
-- Includes buyer (business owner of the product relationship)
-- key = -1 reserved for Unknown/Unassigned

WITH ranked AS (
    SELECT
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
            PARTITION BY drug_code
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE drug_code IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY drug_code)::INT            AS product_key,
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

UNION ALL

SELECT
    -1                  AS product_key,
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
    'Unknown'           AS buyer
