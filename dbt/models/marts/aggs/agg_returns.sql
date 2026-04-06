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
            "CREATE INDEX IF NOT EXISTS idx_agg_returns_product_key ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_returns_customer_key ON {{ this }} (customer_key)"
        ]
    )
}}

-- Returns analysis aggregation
-- Grain: one row per (product_key, customer_key, year, month)
-- Only return transactions (is_return = TRUE)
-- Quantities and amounts stored as absolute values

WITH returns_monthly AS (
    SELECT
        f.tenant_id,
        f.product_key,
        f.customer_key,
        d.year,
        d.month,
        f.billing_way,

        -- Measures (absolute values for returns)
        ABS(ROUND(SUM(f.quantity)::NUMERIC, 2))         AS return_quantity,
        ABS(ROUND(SUM(f.sales)::NUMERIC, 2))              AS return_amount,
        COUNT(*)                                         AS return_count

    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    WHERE f.is_return = TRUE
    GROUP BY f.tenant_id, f.product_key, f.customer_key, d.year, d.month, f.billing_way
)

SELECT
    r.tenant_id,
    r.product_key,
    p.drug_name,
    p.drug_brand,
    r.customer_key,
    c.customer_name,
    r.year,
    r.month,
    r.billing_way,
    r.return_quantity,
    r.return_amount,
    r.return_count
FROM returns_monthly r
INNER JOIN {{ ref('dim_product') }}  p ON r.product_key  = p.product_key  AND r.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_customer') }} c ON r.customer_key = c.customer_key AND r.tenant_id = c.tenant_id
