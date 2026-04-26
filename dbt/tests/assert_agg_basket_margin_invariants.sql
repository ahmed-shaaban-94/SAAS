{{ config(tags=['quality_gate', 'marts']) }}

-- M11 (audit 2026-04-26): margin invariants on agg_basket_margin.
--
-- Two contracts that the gold model must hold:
--   (1) gross_margin = revenue - COALESCE(cost, 0)
--   (2) margin_pct ∈ [-1, 1] (or NULL when revenue = 0)
--
-- The test fails if any row violates either contract.
-- ``cost`` is allowed to be NULL when every item in the basket lacks
-- cost data — that case is observable via ``cart_cost_price_missing``
-- structlog events (H4) and is not a contract violation here.

WITH violations AS (
    SELECT
        tenant_id,
        transaction_id,
        revenue,
        cost,
        gross_margin,
        margin_pct,
        CASE
            WHEN gross_margin IS DISTINCT FROM (revenue - COALESCE(cost, 0))
                THEN 'gross_margin != revenue - COALESCE(cost, 0)'
            WHEN margin_pct IS NOT NULL AND (margin_pct < -1 OR margin_pct > 1)
                THEN 'margin_pct out of [-1, 1]'
        END AS violation
    FROM {{ ref('agg_basket_margin') }}
)

SELECT *
FROM violations
WHERE violation IS NOT NULL
