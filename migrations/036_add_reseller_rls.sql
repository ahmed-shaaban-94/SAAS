-- Migration: Add RLS to reseller tables
-- Phase: Gap Remediation (C1 — financial data exposure)
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
-- Run order: after 035_rls_audit.sql

-- ============================================================
-- 1. Add tenant_id to reseller_payouts
--    Payouts are per-tenant; a reseller can have payouts to many tenants.
--    Backfill from reseller_commissions, then enforce NOT NULL.
-- ============================================================
ALTER TABLE public.reseller_payouts ADD COLUMN IF NOT EXISTS tenant_id INT;

-- Backfill tenant_id from reseller_commissions.
-- Safety: only backfill when a reseller has commissions for exactly ONE tenant.
-- Multi-tenant resellers are left NULL (must be resolved manually before NOT NULL is enforced).
UPDATE public.reseller_payouts rp
SET tenant_id = sub.tenant_id
FROM (
    SELECT rc.reseller_id, MIN(rc.tenant_id) AS tenant_id
    FROM public.reseller_commissions rc
    GROUP BY rc.reseller_id
    HAVING COUNT(DISTINCT rc.tenant_id) = 1
) sub
WHERE sub.reseller_id = rp.reseller_id
  AND rp.tenant_id IS NULL;

-- Enforce NOT NULL now that backfill is done
-- Allow NULL only if no commissions exist yet (edge case for brand-new resellers)
DO $$
BEGIN
    -- Only enforce NOT NULL if all rows have been backfilled
    IF NOT EXISTS (
        SELECT 1 FROM public.reseller_payouts WHERE tenant_id IS NULL
    ) THEN
        ALTER TABLE public.reseller_payouts ALTER COLUMN tenant_id SET NOT NULL;
    END IF;
END $$;

-- ============================================================
-- 2. Enable and force RLS on all 3 reseller tables
-- ============================================================
ALTER TABLE public.resellers           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resellers           FORCE ROW LEVEL SECURITY;

ALTER TABLE public.reseller_commissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reseller_commissions FORCE ROW LEVEL SECURITY;

ALTER TABLE public.reseller_payouts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reseller_payouts    FORCE ROW LEVEL SECURITY;

-- ============================================================
-- 3. Policies for resellers
--    A reseller is a shared entity (serves multiple tenants).
--    Scope via subquery: visible if this tenant has a commission row
--    for this reseller.
-- ============================================================
DROP POLICY IF EXISTS owner_all       ON public.resellers;
DROP POLICY IF EXISTS reader_tenant   ON public.resellers;

CREATE POLICY owner_all ON public.resellers
    FOR ALL TO datapulse
    USING (true)
    WITH CHECK (true);

CREATE POLICY reader_tenant ON public.resellers
    FOR SELECT TO datapulse_reader
    USING (
        reseller_id IN (
            SELECT DISTINCT rc.reseller_id
            FROM public.reseller_commissions rc
            WHERE rc.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT
        )
    );

-- ============================================================
-- 4. Policies for reseller_commissions (direct tenant_id column)
-- ============================================================
DROP POLICY IF EXISTS owner_all       ON public.reseller_commissions;
DROP POLICY IF EXISTS reader_tenant   ON public.reseller_commissions;

CREATE POLICY owner_all ON public.reseller_commissions
    FOR ALL TO datapulse
    USING (true)
    WITH CHECK (true);

CREATE POLICY reader_tenant ON public.reseller_commissions
    FOR SELECT TO datapulse_reader
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT
    );

-- ============================================================
-- 5. Policies for reseller_payouts (direct tenant_id after backfill)
-- ============================================================
DROP POLICY IF EXISTS owner_all       ON public.reseller_payouts;
DROP POLICY IF EXISTS reader_tenant   ON public.reseller_payouts;

CREATE POLICY owner_all ON public.reseller_payouts
    FOR ALL TO datapulse
    USING (true)
    WITH CHECK (true);

CREATE POLICY reader_tenant ON public.reseller_payouts
    FOR SELECT TO datapulse_reader
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT
    );

-- ============================================================
-- 6. Grants (idempotent)
-- ============================================================
GRANT SELECT ON TABLE public.resellers           TO datapulse_reader;
GRANT SELECT ON TABLE public.reseller_commissions TO datapulse_reader;
GRANT SELECT ON TABLE public.reseller_payouts    TO datapulse_reader;
