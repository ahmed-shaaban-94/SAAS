-- Migration 037: Fix RLS owner policies — enforce tenant scoping for API sessions
--
-- SECURITY FIX (P0): All owner_all policies had USING (true), which means the
-- datapulse role (used by the API) could read/write ANY tenant's data regardless
-- of the SET LOCAL app.tenant_id session variable.
--
-- New policy logic:
--   - When app.tenant_id IS set (API sessions): only matching tenant rows
--   - When app.tenant_id is NOT set or empty (pipeline/admin): all rows
--
-- This preserves backward compatibility for pipeline scripts that don't set
-- app.tenant_id while enforcing tenant isolation for all API requests.
--
-- Idempotent: DROP POLICY IF EXISTS + CREATE POLICY.
-- Rollback: Re-create policies with USING (true).

-- Helper expression used in all policies:
--   current_setting('app.tenant_id', true) returns NULL if not set (true = missing_ok)
--   NULLIF(..., '') converts empty string to NULL
--   When NULL → no filtering (pipeline/admin mode)
--   When set → filter by tenant_id

-- ============================================================
-- bronze.sales
-- ============================================================
DROP POLICY IF EXISTS owner_all_access ON bronze.sales;
CREATE POLICY owner_all_access ON bronze.sales
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.pipeline_runs
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.pipeline_runs;
CREATE POLICY owner_all ON public.pipeline_runs
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.quality_checks
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.quality_checks;
CREATE POLICY owner_all ON public.quality_checks
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.forecast_results
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.forecast_results;
CREATE POLICY owner_all ON public.forecast_results
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.sales_targets
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.sales_targets;
CREATE POLICY owner_all ON public.sales_targets
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.alerts_config
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.alerts_config;
CREATE POLICY owner_all ON public.alerts_config
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.alerts_log
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.alerts_log;
CREATE POLICY owner_all ON public.alerts_log
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.subscriptions
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.subscriptions;
CREATE POLICY owner_all ON public.subscriptions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.usage_metrics
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.usage_metrics;
CREATE POLICY owner_all ON public.usage_metrics
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.anomaly_alerts
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.anomaly_alerts;
CREATE POLICY owner_all ON public.anomaly_alerts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.audit_log
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.audit_log;
CREATE POLICY owner_all ON public.audit_log
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.onboarding
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.onboarding;
CREATE POLICY owner_all ON public.onboarding
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.report_schedules
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.report_schedules;
CREATE POLICY owner_all ON public.report_schedules
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.resellers — NO tenant_id column (cross-tenant lookup table)
-- Keep USING (true) — resellers are managed at platform level, not per-tenant.
-- ============================================================

-- ============================================================
-- public.reseller_commissions
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.reseller_commissions;
CREATE POLICY owner_all ON public.reseller_commissions
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- public.reseller_payouts
-- ============================================================
DROP POLICY IF EXISTS owner_all ON public.reseller_payouts;
CREATE POLICY owner_all ON public.reseller_payouts
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- ============================================================
-- RBAC tables (tenant_members, sectors, member_sector_access)
-- ============================================================
DROP POLICY IF EXISTS owner_all_tenant_members ON public.tenant_members;
CREATE POLICY owner_all_tenant_members ON public.tenant_members
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

DROP POLICY IF EXISTS owner_all_sectors ON public.sectors;
CREATE POLICY owner_all_sectors ON public.sectors
    FOR ALL TO datapulse
    USING (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    )
    WITH CHECK (
        NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::INT
    );

-- member_sector_access joins via member_id, not tenant_id directly.
-- Keep USING (true) — access is scoped via the member lookup which is tenant-scoped.
-- (No tenant_id column on this table.)

COMMENT ON TABLE bronze.sales IS
    'Raw sales data with tenant-scoped RLS. '
    'Owner role (datapulse) scoped by SET LOCAL app.tenant_id (migration 037). '
    'Pipeline sessions without app.tenant_id retain full access.';
