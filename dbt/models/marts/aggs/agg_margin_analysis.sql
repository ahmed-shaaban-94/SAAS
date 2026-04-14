{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'product_key', 'year', 'month'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_margin_product_key ON {{ this }} (product_key, tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_agg_margin_year_month ON {{ this }} (year, month)"
        ]
    )
}}

-- Margin Analysis aggregation
-- Grain: one row per (tenant_id, product_key, year, month)
-- Revenue from fct_sales; COGS from weighted average PO unit cost
-- Margin = Revenue - COGS; margin_pct = Margin / Revenue

WITH sales AS (
    SELECT
        f.tenant_id,
        f.product_key,
        d.year,
        d.month,
        d.month_name,
        SUM(f.sales)::NUMERIC(18, 4)    AS revenue,
        SUM(f.quantity)::NUMERIC(18, 4) AS units_sold
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
    GROUP BY f.tenant_id, f.product_key, d.year, d.month, d.month_name
),

-- Weighted average cost from received PO lines (overall, not per period)
weighted_costs AS (
    SELECT
        tenant_id,
        drug_code,
        (
            SUM(unit_price * received_quantity)
            / NULLIF(SUM(received_quantity), 0)
        )::NUMERIC(18, 4) AS weighted_unit_cost
    FROM {{ ref('fct_po_lines') }}
    WHERE received_quantity > 0
    GROUP BY tenant_id, drug_code
),

with_product AS (
    SELECT
        s.tenant_id,
        s.product_key,
        p.drug_code,
        p.drug_name,
        p.drug_brand,
        p.drug_category,
        s.year,
        s.month,
        s.month_name,
        s.revenue,
        s.units_sold,
        COALESCE(wc.weighted_unit_cost, 0) AS weighted_unit_cost
    FROM sales s
    INNER JOIN {{ ref('dim_product') }} p
        ON s.product_key = p.product_key AND s.tenant_id = p.tenant_id
    LEFT JOIN weighted_costs wc
        ON p.drug_code = wc.drug_code AND s.tenant_id = wc.tenant_id
)

SELECT
    tenant_id,
    product_key,
    drug_code,
    drug_name,
    drug_brand,
    drug_category,
    year,
    month,
    month_name,
    ROUND(revenue, 2)                                                        AS revenue,
    units_sold,
    weighted_unit_cost,
    ROUND(units_sold * weighted_unit_cost, 2)                                AS cogs,
    ROUND(revenue - (units_sold * weighted_unit_cost), 2)                   AS gross_margin,
    ROUND(
        (revenue - (units_sold * weighted_unit_cost))
        / NULLIF(revenue, 0),
        4
    )                                                                        AS margin_pct
FROM with_product
