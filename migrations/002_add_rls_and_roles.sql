-- Migration: RLS preparation and read-only role for future web frontend
-- Layer: Security / Access Control
-- Phase: Preparation for Phase 1.5 (Next.js frontend)
--
-- Run order: after 001_create_bronze_schema.sql
-- Idempotent: safe to run multiple times (uses IF NOT EXISTS / DO $$ guards)
-- Requires: PostgreSQL 16+ (CREATE POLICY IF NOT EXISTS is PG 15+)
--
-- Roles created:
--   datapulse        — owner role (full access), created by Docker Compose
--   datapulse_reader — read-only role for the web frontend (created here)

-- ============================================================
-- 1. Create read-only role for web frontend (Phase 1.5)
-- ============================================================
-- This role will be used by the Next.js API layer to query
-- gold/silver data. It has no INSERT, UPDATE, or DELETE rights.
-- Change the password before Phase 1.5 deployment.

-- Password MUST be set via DB_READER_PASSWORD environment variable.
-- Example: DB_READER_PASSWORD=$(openssl rand -hex 32) psql -f 002_add_rls_and_roles.sql
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_reader') THEN
        IF current_setting('app.db_reader_password', true) IS NULL THEN
            RAISE EXCEPTION 'app.db_reader_password GUC must be set. Run: SET app.db_reader_password = ''<password>''; before this migration.';
        END IF;
        EXECUTE format(
            'CREATE ROLE datapulse_reader LOGIN PASSWORD %L',
            current_setting('app.db_reader_password', true)
        );
    END IF;
END $$;

-- ============================================================
-- 2. Grant schema usage and SELECT access
-- ============================================================
-- bronze schema — raw data (read-only for the frontend)
GRANT USAGE ON SCHEMA bronze TO datapulse_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA bronze TO datapulse_reader;

-- Ensure future tables added to bronze are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze
    GRANT SELECT ON TABLES TO datapulse_reader;

-- public schema — default schema, may contain utility views
GRANT USAGE ON SCHEMA public TO datapulse_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datapulse_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO datapulse_reader;

-- public_staging schema — silver layer (created by dbt, may not exist yet)
-- Guarded with an existence check so this migration is safe to run
-- before dbt has created the schema.
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.schemata
        WHERE schema_name = 'public_staging'
    ) THEN
        GRANT USAGE ON SCHEMA public_staging TO datapulse_reader;
        GRANT SELECT ON ALL TABLES IN SCHEMA public_staging TO datapulse_reader;
    END IF;
END $$;

-- marts schema — gold layer (created by dbt, may not exist yet)
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.schemata
        WHERE schema_name = 'marts'
    ) THEN
        GRANT USAGE ON SCHEMA marts TO datapulse_reader;
        GRANT SELECT ON ALL TABLES IN SCHEMA marts TO datapulse_reader;
    END IF;
END $$;

-- ============================================================
-- 3. Revoke public schema CREATE from PUBLIC (security hardening)
-- ============================================================
-- PostgreSQL <= 14 grants CREATE on public to PUBLIC by default.
-- PG 15+ revokes it by default, but we make this explicit for
-- clarity and forward compatibility.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- ============================================================
-- 4. Enable Row Level Security on bronze.sales
-- ============================================================
-- RLS is enabled but the policies below keep behaviour identical
-- to the pre-RLS state (all rows visible to the owner role).
-- Add tenant/user-scoped policies in a later migration when the
-- multi-tenant model is defined.

ALTER TABLE bronze.sales ENABLE ROW LEVEL SECURITY;

-- Owner policy: the datapulse application role retains full access.
-- USING (true) means every row passes the visibility check.
-- WITH CHECK (true) means every row passes the write check.
CREATE POLICY IF NOT EXISTS owner_all_access ON bronze.sales
    FOR ALL
    TO datapulse
    USING (true)
    WITH CHECK (true);

-- Reader policy: datapulse_reader may SELECT all rows.
-- No WITH CHECK clause needed because FOR SELECT never modifies data.
CREATE POLICY IF NOT EXISTS reader_select_access ON bronze.sales
    FOR SELECT
    TO datapulse_reader
    USING (true);

-- ============================================================
-- 5. Update table comment to document RLS state
-- ============================================================
-- Replaces the comment set in migration 001.
COMMENT ON TABLE bronze.sales IS
    'Raw sales data with RLS enabled. '
    'Owner role (datapulse) has full access via owner_all_access policy. '
    'Reader role (datapulse_reader) has SELECT-only access via reader_select_access policy. '
    'Add tenant/user-filtering USING clauses to both policies before Phase 1.5 frontend launch.';
