-- Migration: Add tenant_id to bronze.sales and enforce tenant-scoped RLS
-- Layer: Security / Multi-tenancy
-- Phase: Preparation for Phase 1.5 (Next.js frontend)
--
-- Run order: after 002_add_rls_and_roles.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
-- Requires: PostgreSQL 15+ (security_invoker view option)
--
-- What this does:
--   1. Creates bronze.tenants reference table (single tenant seeded)
--   2. Adds tenant_id to bronze.sales with DEFAULT 1
--   3. Replaces permissive reader RLS policy with tenant-scoped filter
--
-- Session variable pattern (used by Next.js API in Phase 1.5):
--   SET LOCAL app.tenant_id = '1';
--   SELECT * FROM public_marts.fct_sales;  -- automatically filtered

-- ============================================================
-- 1. Create tenants reference table
-- ============================================================

CREATE TABLE IF NOT EXISTS bronze.tenants (
    tenant_id   INT         PRIMARY KEY,
    tenant_name TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed default tenant (single-tenant for now)
INSERT INTO bronze.tenants (tenant_id, tenant_name)
VALUES (1, 'Default')
ON CONFLICT DO NOTHING;

-- Grant reader access to tenants table
GRANT SELECT ON TABLE bronze.tenants TO datapulse_reader;

-- ============================================================
-- 2. Add tenant_id column to bronze.sales
-- ============================================================
-- DEFAULT 1 backfills all existing 1.1M rows automatically.
-- No UPDATE needed — all data belongs to the single default tenant.

ALTER TABLE bronze.sales
    ADD COLUMN IF NOT EXISTS tenant_id INT NOT NULL DEFAULT 1
    REFERENCES bronze.tenants (tenant_id);

-- Index for RLS filter performance (evaluated on every row access)
CREATE INDEX IF NOT EXISTS idx_bronze_sales_tenant_id
    ON bronze.sales (tenant_id);

-- ============================================================
-- 3. Update reader RLS policy — tenant-scoped filter
-- ============================================================
-- Old policy used USING (true) — all rows visible.
-- New policy uses session variable app.tenant_id set by the API layer.
--
-- NULLIF(..., '') handles unset session variable gracefully:
--   current_setting('app.tenant_id', true) returns NULL if not set
--   NULLIF(NULL, '') is NULL → ::INT cast returns NULL
--   NULL = 1 is FALSE → no rows returned (fail-closed)
--
-- The owner policy is unchanged (datapulse role bypasses tenant filter).

DROP POLICY IF EXISTS reader_select_access ON bronze.sales;

CREATE POLICY reader_select_access ON bronze.sales
    FOR SELECT
    TO datapulse_reader
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT
    );

-- Force RLS to apply even for the table owner (datapulse role).
-- The owner_all policy USING (true) still grants full access,
-- but this prevents silent RLS bypass if role assignments change.
ALTER TABLE bronze.sales FORCE ROW LEVEL SECURITY;

-- ============================================================
-- 4. Update table comment
-- ============================================================
COMMENT ON TABLE bronze.sales IS
    'Raw sales data with tenant-scoped RLS. '
    'Owner role (datapulse) has full access via owner_all_access policy. '
    'Reader role (datapulse_reader) sees only rows matching SET LOCAL app.tenant_id. '
    'All existing rows assigned to tenant_id = 1 (Default). '
    'Silver view (stg_sales) inherits this filter via security_invoker = on.';
