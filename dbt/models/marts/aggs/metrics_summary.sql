{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'date_key'],
        on_schema_change='sync_all_columns',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_summary_date_key ON {{ this }} (date_key)"
        ]
    )
}}

-- Daily metrics summary with MTD and YTD running totals
-- Grain: one row per day (aggregated across all sites and billing ways)

-- Pre-aggregate unique customers per (tenant_id, date_key) to avoid correlated subquery
WITH daily_customers AS (
    SELECT
        f.tenant_id,
        f.date_key,
        COUNT(DISTINCT f.customer_key)::INT AS daily_unique_customers
    FROM {{ ref('fct_sales') }} f
    GROUP BY f.tenant_id, f.date_key
),

daily_totals AS (
    SELECT
        a.tenant_id,
        a.date_key,
        d.full_date,
        d.year,
        d.month,
        ROUND(SUM(a.total_sales), 2)             AS daily_gross_amount,
        ROUND(SUM(a.total_net_amount), 2)        AS daily_net_amount,
        ROUND(SUM(a.total_discount), 2)          AS daily_discount,
        SUM(a.total_quantity)::NUMERIC(18,4)     AS daily_quantity,
        SUM(a.transaction_count)::INT            AS daily_transactions,  -- includes returns
        SUM(a.return_count)::INT                 AS daily_returns,
        COALESCE(dc.daily_unique_customers, 0)   AS daily_unique_customers
    FROM {{ ref('agg_sales_daily') }} a
    INNER JOIN {{ ref('dim_date') }} d ON a.date_key = d.date_key
    LEFT JOIN daily_customers dc ON a.date_key = dc.date_key AND a.tenant_id = dc.tenant_id
    GROUP BY a.tenant_id, a.date_key, d.full_date, d.year, d.month, dc.daily_unique_customers
)

SELECT
    t.tenant_id,
    t.date_key,
    t.full_date,
    t.year,
    t.month,
    -- Daily values
    t.daily_gross_amount,
    t.daily_net_amount,
    t.daily_discount,
    t.daily_quantity,
    t.daily_transactions,
    t.daily_returns,
    t.daily_unique_customers,
    -- MTD running totals
    ROUND(
        SUM(t.daily_gross_amount) OVER (
            PARTITION BY t.tenant_id, t.year, t.month
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS mtd_gross_amount,
    ROUND(
        SUM(t.daily_net_amount) OVER (
            PARTITION BY t.tenant_id, t.year, t.month
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS mtd_net_amount,
    SUM(t.daily_transactions) OVER (
        PARTITION BY t.tenant_id, t.year, t.month
        ORDER BY t.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::INT AS mtd_transactions,
    -- YTD running totals
    ROUND(
        SUM(t.daily_gross_amount) OVER (
            PARTITION BY t.tenant_id, t.year
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS ytd_gross_amount,
    ROUND(
        SUM(t.daily_net_amount) OVER (
            PARTITION BY t.tenant_id, t.year
            ORDER BY t.full_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ),
        2
    ) AS ytd_net_amount,
    SUM(t.daily_transactions) OVER (
        PARTITION BY t.tenant_id, t.year
        ORDER BY t.full_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::INT AS ytd_transactions
FROM daily_totals t
{% if is_incremental() %}
WHERE t.full_date >= CURRENT_DATE - INTERVAL '7 days'
{% endif %}
