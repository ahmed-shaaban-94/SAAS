{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'customer_key', 'year', 'month'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_customer_year_month ON {{ this }} (year, month)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_customer_customer_key ON {{ this }} (customer_key)"
        ]
    )
}}

-- Customer sales aggregation with denormalized customer attributes
-- Grain: one row per (customer_key, year, month)

WITH customer_monthly AS (
    SELECT
        f.tenant_id,
        f.customer_key,
        d.year,
        d.month,
        d.month_name,
        SUM(f.quantity)::NUMERIC(18,4)                    AS total_quantity,
        ROUND(SUM(f.sales), 2)                            AS total_sales,
        ROUND(SUM(f.discount), 2)                         AS total_discount,
        ROUND(SUM(f.net_amount), 2)                       AS total_net_amount,
        COUNT(*)::INT                                     AS transaction_count,
        COUNT(*) FILTER (WHERE f.is_return)::INT          AS return_count,
        COUNT(DISTINCT f.product_key)::INT                AS unique_products,
        COUNT(*) FILTER (WHERE f.is_walk_in)::INT         AS walk_in_count,
        COUNT(*) FILTER (WHERE f.has_insurance)::INT      AS insurance_count,
        ROUND(
            SUM(f.sales) / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                 AS avg_basket_size
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    {% if is_incremental() %}
    WHERE f.date_key >= (
        SELECT TO_CHAR(
            MAKE_DATE(MAX(year), MAX(month), 1) - INTERVAL '90 days',
            'YYYYMMDD'
        )::INT
        FROM {{ this }}
    )
    {% endif %}
    GROUP BY f.tenant_id, f.customer_key, d.year, d.month, d.month_name
)

SELECT
    cm.tenant_id,
    cm.customer_key,
    c.customer_id,
    c.customer_name,
    cm.year,
    cm.month,
    cm.month_name,
    cm.total_quantity,
    cm.total_sales,
    cm.total_discount,
    cm.total_net_amount,
    cm.transaction_count,
    cm.return_count,
    cm.unique_products,
    cm.walk_in_count,
    cm.insurance_count,
    cm.avg_basket_size
FROM customer_monthly cm
INNER JOIN {{ ref('dim_customer') }} c ON cm.customer_key = c.customer_key AND cm.tenant_id = c.tenant_id
