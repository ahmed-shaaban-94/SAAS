-- Migration: Canonical public.current_tenant_id() RLS helper
-- Layer: Security / Multi-tenancy
-- Issue: #547-3
--
-- Run order: after 097_pos_autovacuum_tuning.sql
-- Idempotent: CREATE OR REPLACE FUNCTION is idempotent by definition.
--
-- What this does:
--   Defines a single SQL function that every RLS policy can use instead of
--   open-coding ``NULLIF(current_setting('app.tenant_id', true), '')::INT``
--   (53 callsites across migrations/) or the older broken pattern
--   ``tenant_id::text = current_setting('app.tenant_id', true)`` (fixed for
--   saved_views/notifications/dashboard_layouts/annotations in 030c).
--
-- Semantics:
--   - Returns the session's tenant_id as an INT.
--   - Returns NULL when ``app.tenant_id`` is unset or the empty string
--     → ``tenant_id = current_tenant_id()`` evaluates to NULL, i.e. the
--     policy fails closed (RLS denies rows).
--   - Raises ``22P02 invalid_text_representation`` when the session var is
--     non-numeric — refuses to silently fail closed on a typo or injection
--     attempt that sets the var to something like "1 OR 1=1".
--
-- Why STABLE:
--   - The result depends only on the current session's settings (no DB
--     reads), so STABLE is the tightest safe volatility category. This
--     lets the planner cache the function's result within a single query,
--     matching the cost profile of inline ``current_setting(...)``.
--
-- Why PARALLEL SAFE:
--   - Reads only a session GUC; no side effects, no DB state touched.
--
-- Why SECURITY INVOKER (default):
--   - The caller's role identity must still be visible to the query planner
--     so RLS ``TO <role>`` clauses continue to discriminate between
--     ``datapulse`` (owner, bypass) and ``datapulse_reader`` (tenant-scoped).

CREATE OR REPLACE FUNCTION public.current_tenant_id()
RETURNS INT
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    -- NULLIF turns '' into NULL so the ::INT cast doesn't trip on empty
    -- string. An unset GUC (with `true` = missing_ok) already yields NULL
    -- from current_setting, so both paths return NULL fail-closed.
    SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT;
$$;

COMMENT ON FUNCTION public.current_tenant_id() IS
    'Canonical RLS tenant resolver — returns the session''s app.tenant_id '
    'as INT, NULL when unset or empty (fail-closed), and raises on non-numeric '
    'values. Prefer this over open-coded NULLIF+cast in new RLS policies (#547).';

-- Smoke test: the function must exist and be callable. Any SQL client that
-- applies this migration should see ``current_tenant_id()`` return NULL in
-- a fresh session (no app.tenant_id set).
-- Postgres >= 16 supports ``DO`` blocks with EXCEPTION, so wrap the self-
-- check defensively. A NOTICE on failure is louder than a silent skip.
DO $$
DECLARE
    result INT;
BEGIN
    -- Explicitly clear the GUC so the check is self-contained.
    PERFORM set_config('app.tenant_id', '', true);
    result := public.current_tenant_id();
    IF result IS NOT NULL THEN
        RAISE EXCEPTION 'current_tenant_id() self-check failed: expected NULL when unset, got %', result;
    END IF;

    PERFORM set_config('app.tenant_id', '42', true);
    result := public.current_tenant_id();
    IF result IS DISTINCT FROM 42 THEN
        RAISE EXCEPTION 'current_tenant_id() self-check failed: expected 42, got %', result;
    END IF;
END $$;

-- Reset the session GUC so the migration leaves no state.
SELECT set_config('app.tenant_id', '', true);
