{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'supplier_key'],
        incremental_strategy='merge',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_supplier_perf_supplier_key ON {{ this }} (supplier_key, tenant_id)"
        ]
    )
}}

-- Supplier Performance aggregation
-- Grain: one row per (tenant_id, supplier_key)
-- Metrics: avg lead time, fill rate, order count, total spend, cancellation rate

WITH po_stats AS (
    SELECT
        po.tenant_id,
        po.supplier_key,
        COUNT(*)                                                    AS total_orders,
        COUNT(*) FILTER (WHERE po.status = 'received')             AS completed_orders,
        COUNT(*) FILTER (WHERE po.status = 'cancelled')            AS cancelled_orders,
        AVG(po.actual_lead_days) FILTER (WHERE po.actual_lead_days IS NOT NULL)
                                                                   AS avg_lead_days,
        ROUND(
            SUM(po.total_received_value)
            / NULLIF(SUM(po.total_ordered_value), 0),
            4
        )                                                           AS fill_rate,
        SUM(po.total_ordered_value)::NUMERIC(18, 4)                AS total_spend,
        SUM(po.total_received_value)::NUMERIC(18, 4)               AS total_received
    FROM {{ ref('fct_purchase_orders') }} po
    GROUP BY po.tenant_id, po.supplier_key
)

SELECT
    ps.tenant_id,
    ps.supplier_key,
    sup.supplier_code,
    sup.supplier_name,
    sup.lead_time_days                                              AS contracted_lead_days,
    ps.total_orders,
    ps.completed_orders,
    ps.cancelled_orders,
    ROUND(ps.avg_lead_days, 1)                                     AS avg_lead_days,
    COALESCE(ps.fill_rate, 0)                                      AS fill_rate,
    ps.total_spend,
    ps.total_received,
    ROUND(
        ps.cancelled_orders::NUMERIC / NULLIF(ps.total_orders, 0),
        4
    )                                                               AS cancellation_rate
FROM po_stats ps
INNER JOIN {{ ref('dim_supplier') }} sup
    ON ps.supplier_key = sup.supplier_key AND ps.tenant_id = sup.tenant_id
WHERE ps.supplier_key != -1  -- exclude Unknown row
