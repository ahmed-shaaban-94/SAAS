-- Migration 015: Fix anomaly_alerts owner_all policy to grant full access
-- Phase: Session 8 audit — Multi-Tenancy (Phase 13)
--
-- The original migration 013 created owner_all with a tenant filter:
--   USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
-- This is inconsistent with ALL other tables where the owner (datapulse) role
-- has USING (true) for full access. The tenant filter on the owner role blocks
-- admin operations like cross-tenant reporting and data management.

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('015_fix_anomaly_alerts_owner_policy.sql')
ON CONFLICT (filename) DO NOTHING;

-- Drop the incorrect owner policy and recreate with USING (true)
DROP POLICY IF EXISTS owner_all ON public.anomaly_alerts;

CREATE POLICY owner_all ON public.anomaly_alerts
    FOR ALL TO datapulse
    USING (true) WITH CHECK (true);

COMMIT;
