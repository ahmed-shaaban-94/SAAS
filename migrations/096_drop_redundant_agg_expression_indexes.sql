-- Migration 096: Drop redundant single-column expression indexes on aggs
-- Layer: Analytics / dbt marts
-- Idempotent: DROP INDEX IF EXISTS on each target.
--
-- Why:
--   Migration 023 created single-column expression indexes on
--   agg_sales_by_{product,customer,staff} and agg_sales_monthly:
--       idx_agg_*_ym  ((year * 100 + month))
--
--   Migration 033 later added tenant-scoped composites that are a strict
--   super-key of the above for all real query patterns (every query
--   includes tenant_id = :tid in this multi-tenant system):
--       idx_agg_*_tenant_ym  (tenant_id, (year * 100 + month))
--
--   The single-column indexes are therefore dead weight — they pay for
--   themselves on every incremental load but are never chosen by the
--   planner over the composite.
--
--   Additionally, these tables are dbt-incremental: normal runs keep the
--   indexes alive, but --full-refresh drops and re-creates the table.
--   Migrations 023/033 are one-shot, so after a --full-refresh those
--   indexes are gone until re-applied manually. The sibling commit on
--   this PR moves the *composites* into each model's dbt post_hook so
--   they always exist after a build. The single-col (023) indexes are
--   not being moved — they are being dropped outright.
--
-- Rollback:
--   Re-run migration 023.

DO $$ BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.schemata
    WHERE schema_name = 'public_marts'
) THEN
    DROP INDEX IF EXISTS public_marts.idx_agg_product_ym;
    DROP INDEX IF EXISTS public_marts.idx_agg_customer_ym;
    DROP INDEX IF EXISTS public_marts.idx_agg_staff_ym;
    DROP INDEX IF EXISTS public_marts.idx_agg_monthly_ym;
ELSE
    RAISE NOTICE 'public_marts schema does not exist — nothing to drop';
END IF;
END $$;
