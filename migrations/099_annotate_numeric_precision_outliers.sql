-- Migration: Annotate NUMERIC precision outliers (#547-1)
-- Layer: Schema documentation
--
-- Run order: after 098_current_tenant_id_helper.sql
-- Idempotent: COMMENT ON COLUMN is unconditional overwrite.
--
-- Context:
-- The primary financial precision standard is ``NUMERIC(18,4)`` (66 uses
-- across migrations/). The audit for #547-1 found a handful of deviations.
-- All were reviewed and are kept intentionally for the reasons below; this
-- migration records each rationale as a COMMENT so the drift-detection test
-- in ``tests/test_numeric_precision_drift.py`` can tell "intentional
-- exception" from "accidental drift" without grepping migration history.
--
-- Marker convention:
--   The literal token ``#precision-exception`` appears in every intentional
--   comment, so the test can filter by ``obj_description LIKE '%#precision-exception%'``.

-- ---- Financial-named deviation (matches /(price|amount|cost|revenue|total)/) ----

-- cost_cents is denominated in USD cents, not dollars. NUMERIC(10,4) gives
-- up to 999_999.9999 cents ≈ $10k per invocation, with 4-decimal headroom
-- for fractional-cent provider pricing (OpenRouter/Anthropic bill per 1M
-- tokens). The column name encodes the unit, so the standard dollar-centric
-- (18,4) would mislead readers.
COMMENT ON COLUMN public.ai_invocations.cost_cents IS
    '#precision-exception: denominated in cents, NUMERIC(10,4) covers '
    'fractional-cent per-token provider pricing with $10k headroom (#547-1).';

-- ---- Non-financial deviations (do not match the drift regex, annotated for audit trail) ----

COMMENT ON COLUMN public.pipeline_runs.duration_seconds IS
    '#precision-exception: time in seconds, not currency. '
    'NUMERIC(10,2) covers runs up to ~115 days with 10 ms precision (#547-1).';

COMMENT ON COLUMN public.forecast_results.point_forecast IS
    '#precision-exception: forecast aggregate over sales quantities; (18,2) '
    'keeps the forecast result tidy for display. Upstream fct_sales net_sales '
    'is (18,4) and aggregation rounds to 2 decimals by design (#547-1).';

COMMENT ON COLUMN public.forecast_results.lower_bound IS
    '#precision-exception: see point_forecast — matching precision (#547-1).';

COMMENT ON COLUMN public.forecast_results.upper_bound IS
    '#precision-exception: see point_forecast — matching precision (#547-1).';

COMMENT ON COLUMN public.forecast_results.mae IS
    '#precision-exception: error metric over a (18,2) forecast; '
    'MAE is in the same units as the forecast itself (#547-1).';

COMMENT ON COLUMN public.forecast_results.rmse IS
    '#precision-exception: error metric over a (18,2) forecast; '
    'RMSE is in the same units as the forecast itself (#547-1).';

COMMENT ON COLUMN public.forecast_results.mape IS
    '#precision-exception: MAPE is a dimensionless ratio in [0,1]; '
    'NUMERIC(8,4) gives 0.0001 resolution up to 9999.9999 (#547-1).';

COMMENT ON COLUMN public.anomaly_alerts.z_score IS
    '#precision-exception: statistical z-score, typically |z| < 10 in practice; '
    'NUMERIC(8,4) gives 4-decimal resolution (#547-1).';

COMMENT ON COLUMN public.resellers.commission_pct IS
    '#precision-exception: percentage with 2 decimals (e.g. 20.00 = 20%); '
    'NUMERIC(5,2) bounds to 999.99 which is far above any plausible '
    'commission rate (#547-1).';

COMMENT ON COLUMN public.reseller_commissions.commission_pct IS
    '#precision-exception: see resellers.commission_pct — matching (5,2) (#547-1).';
