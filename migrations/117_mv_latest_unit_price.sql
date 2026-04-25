-- Migration 117 — Materialized view: latest unit price per product per tenant
-- Provides a fast, predictable-latency price lookup for the POS catalog
-- after the correlated subquery was removed in #719.
-- Date: 2026-04-26

DO $$
BEGIN
  -- Skip when public_marts.fct_sales doesn't exist yet (dbt not yet run).
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public_marts' AND table_name = 'fct_sales'
  ) THEN
    RAISE NOTICE 'public_marts.fct_sales does not exist yet — skipping mv_latest_unit_price creation';
    RETURN;
  END IF;

  -- Create the MV only if it doesn't already exist (idempotent)
  IF NOT EXISTS (
    SELECT 1 FROM pg_matviews
    WHERE schemaname = 'public_marts'
      AND matviewname = 'mv_latest_unit_price'
  ) THEN
    EXECUTE $mv$
      CREATE MATERIALIZED VIEW public_marts.mv_latest_unit_price AS
      SELECT DISTINCT ON (tenant_id, product_key)
          tenant_id,
          product_key,
          (sales / NULLIF(quantity, 0)) AS unit_price,
          date_key
      FROM public_marts.fct_sales
      WHERE quantity > 0
      ORDER BY tenant_id, product_key, date_key DESC
    $mv$;

    -- Unique index enables REFRESH CONCURRENTLY for zero-downtime daily refreshes
    EXECUTE $idx$
      CREATE UNIQUE INDEX mv_latest_unit_price_pkey
        ON public_marts.mv_latest_unit_price (tenant_id, product_key)
    $idx$;
  END IF;
END
$$;
