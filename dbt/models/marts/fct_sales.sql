{{
    config(
        materialized='table',
        schema='marts'
    )
}}

-- Sales fact table
-- Grain: one line-item per invoice
-- Integer surrogate keys via JOINs to dimensions (incl. billing_key)
-- COALESCE all dimension FKs to -1 for unknown/unmatched members
-- Financials rounded to 2 decimals

WITH stg AS (
    SELECT * FROM {{ ref('stg_sales') }}
),

dim_product AS (
    SELECT product_key, drug_code FROM {{ ref('dim_product') }}
),

dim_customer AS (
    SELECT customer_key, customer_id FROM {{ ref('dim_customer') }}
),

dim_site AS (
    SELECT site_key, site_code FROM {{ ref('dim_site') }}
),

dim_staff AS (
    SELECT staff_key, staff_id FROM {{ ref('dim_staff') }}
),

dim_billing AS (
    SELECT billing_key, billing_way FROM {{ ref('dim_billing') }}
)

SELECT
    ROW_NUMBER() OVER (ORDER BY s.invoice_date, s.invoice_id, s.drug_code)::INT AS sales_key,

    -- Foreign keys (clean integers, -1 = Unknown)
    TO_CHAR(s.invoice_date, 'YYYYMMDD')::INT    AS date_key,
    COALESCE(p.product_key, -1)                 AS product_key,
    COALESCE(c.customer_key, -1)                AS customer_key,
    COALESCE(si.site_key, -1)                   AS site_key,
    COALESCE(st.staff_key, -1)                  AS staff_key,
    COALESCE(b.billing_key, -1)                 AS billing_key,

    -- Degenerate dimensions
    s.invoice_id,
    s.billing_way,

    -- Measures (rounded to 2 decimals)
    ROUND(s.quantity::NUMERIC, 2)               AS quantity,
    ROUND(s.sales::NUMERIC, 2)                  AS sales,
    ROUND(s.discount::NUMERIC, 2)               AS discount,
    ROUND(s.net_amount::NUMERIC, 2)             AS net_amount,

    -- Flags
    s.is_return,
    s.is_walk_in,
    s.has_insurance

FROM stg s
LEFT JOIN dim_product  p  ON s.drug_code   = p.drug_code
LEFT JOIN dim_customer c  ON s.customer_id = c.customer_id
LEFT JOIN dim_site     si ON s.site_code   = si.site_code
LEFT JOIN dim_staff    st ON s.staff_id    = st.staff_id
LEFT JOIN dim_billing  b  ON s.billing_way = b.billing_way
