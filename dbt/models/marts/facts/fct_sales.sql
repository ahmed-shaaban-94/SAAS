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
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_date_key ON {{ this }} (date_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_id ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_product_key ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_customer_key ON {{ this }} (customer_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_site_key ON {{ this }} (site_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_staff_key ON {{ this }} (staff_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_billing_key ON {{ this }} (billing_key)",
            "CREATE INDEX IF NOT EXISTS idx_fct_sales_is_return ON {{ this }} (is_return) WHERE is_return = TRUE"
        ]
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
    SELECT product_key, tenant_id, drug_code FROM {{ ref('dim_product') }}
),

dim_customer AS (
    SELECT customer_key, tenant_id, customer_id FROM {{ ref('dim_customer') }}
),

dim_site AS (
    SELECT site_key, tenant_id, site_code FROM {{ ref('dim_site') }}
),

dim_staff AS (
    SELECT staff_key, tenant_id, staff_id FROM {{ ref('dim_staff') }}
),

dim_billing AS (
    SELECT billing_key, billing_way FROM {{ ref('dim_billing') }}
)

SELECT
    -- Deterministic surrogate key: MD5 hash of natural key columns
    ('x' || LEFT(MD5(
        COALESCE(s.tenant_id::TEXT, '') || '|' ||
        COALESCE(s.invoice_id, '') || '|' ||
        COALESCE(s.invoice_date::TEXT, '') || '|' ||
        COALESCE(s.drug_code, '') || '|' ||
        COALESCE(s.customer_id, '') || '|' ||
        COALESCE(s.site_code, '') || '|' ||
        COALESCE(s.quantity::TEXT, '') || '|' ||
        COALESCE(s.billing_way, '')
    ), 16))::BIT(64)::BIGINT AS sales_key,

    -- Tenant
    s.tenant_id,

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
LEFT JOIN dim_product  p  ON s.drug_code   = p.drug_code   AND s.tenant_id = p.tenant_id
LEFT JOIN dim_customer c  ON s.customer_id = c.customer_id AND s.tenant_id = c.tenant_id
LEFT JOIN dim_site     si ON s.site_code   = si.site_code  AND s.tenant_id = si.tenant_id
LEFT JOIN dim_staff    st ON s.staff_id    = st.staff_id   AND s.tenant_id = st.tenant_id
LEFT JOIN dim_billing  b  ON s.billing_way = b.billing_way
