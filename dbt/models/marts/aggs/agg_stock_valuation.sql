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
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_val_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_val_product ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_val_site ON {{ this }} (site_key)"
        ]
    )
}}

-- Stock valuation per product per site using weighted average cost (WAC)
-- Grain: one row per (tenant_id, product_key, site_key)
-- WAC = SUM(receipt_qty * unit_cost) / SUM(receipt_qty)
-- stock_value = current_quantity * WAC

-- CTE separates aggregation from alias reference (PostgreSQL cannot reference
-- a SELECT alias in the same SELECT clause)
WITH wac AS (
    SELECT
        m.tenant_id,
        m.product_key,
        m.site_key,
        SUM(
            CASE WHEN m.movement_type = 'receipt' AND m.unit_cost IS NOT NULL
                THEN m.quantity * m.unit_cost
                ELSE 0
            END
        ) / NULLIF(
            SUM(
                CASE WHEN m.movement_type = 'receipt' AND m.unit_cost IS NOT NULL
                    THEN m.quantity
                    ELSE 0
                END
            ), 0
        )                                   AS weighted_avg_cost
    FROM {{ ref('fct_stock_movements') }} m
    WHERE m.product_key != -1
      AND m.site_key    != -1
    GROUP BY
        m.tenant_id,
        m.product_key,
        m.site_key
)

SELECT
    w.tenant_id,
    w.product_key,
    w.site_key,
    p.drug_code,
    p.drug_name,
    s.site_code,
    ROUND(COALESCE(w.weighted_avg_cost, 0), 4)                              AS weighted_avg_cost,
    sl.current_quantity,
    ROUND(COALESCE(sl.current_quantity, 0) * COALESCE(w.weighted_avg_cost, 0), 2) AS stock_value

FROM wac w
INNER JOIN {{ ref('agg_stock_levels') }} sl
    ON w.product_key = sl.product_key
   AND w.site_key    = sl.site_key
   AND w.tenant_id   = sl.tenant_id
INNER JOIN {{ ref('dim_product') }} p ON w.product_key = p.product_key AND w.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }}    s ON w.site_key    = s.site_key    AND w.tenant_id = s.tenant_id
