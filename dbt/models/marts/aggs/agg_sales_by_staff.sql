{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'staff_key', 'year', 'month'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_staff_year_month ON {{ this }} (year, month)",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_by_staff_staff_key ON {{ this }} (staff_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_staff_tenant_key ON {{ this }} (tenant_id, staff_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_staff_tenant_ym ON {{ this }} (tenant_id, (year * 100 + month))"
        ]
    )
}}

-- Staff performance aggregation
-- Grain: one row per (staff_key, year, month)
-- Includes volume, revenue, diversity, returns, and avg transaction value

WITH staff_monthly AS (
    SELECT
        f.tenant_id,
        f.staff_key,
        d.year,
        d.month,

        -- Volume
        SUM(f.quantity)::NUMERIC(18,4)                    AS total_quantity,
        ROUND(SUM(f.sales)::NUMERIC, 2)                 AS total_sales,
        ROUND(SUM(f.net_amount)::NUMERIC, 2)            AS total_net_amount,
        ROUND(SUM(f.discount)::NUMERIC, 2)              AS total_discount,
        COUNT(*)                                         AS transaction_count,

        -- Diversity
        COUNT(DISTINCT f.customer_key)                   AS unique_customers,
        COUNT(DISTINCT f.product_key)                    AS unique_products,

        -- Returns
        SUM(CASE WHEN f.is_return THEN 1 ELSE 0 END)    AS return_count,

        -- Avg transaction value: gross amount per distinct invoice (basket-level)
        ROUND(
            SUM(f.sales)::NUMERIC
            / NULLIF(COUNT(DISTINCT f.invoice_id), 0),
            2
        )                                                AS avg_transaction_value

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
    GROUP BY f.tenant_id, f.staff_key, d.year, d.month
)

SELECT
    s.tenant_id,
    s.staff_key,
    st.staff_id,
    st.staff_name,
    st.staff_position,
    s.year,
    s.month,
    s.total_quantity,
    s.total_sales,
    s.total_net_amount,
    s.total_discount,
    s.transaction_count,
    s.unique_customers,
    s.unique_products,
    s.return_count,
    s.avg_transaction_value
FROM staff_monthly s
INNER JOIN {{ ref('dim_staff') }} st ON s.staff_key = st.staff_key AND s.tenant_id = st.tenant_id
