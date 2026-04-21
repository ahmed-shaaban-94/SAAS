-- Migration 094: DB hardening — role timeouts + audit_log append-only trigger
--
-- Purpose:
--   1. Set statement/idle/lock timeouts as role defaults on datapulse and
--      datapulse_reader. This is a safety net — deps.py SET LOCAL overrides
--      these per-transaction — but catches any code path that forgets to
--      set them, or any direct psql connection.
--   2. Make public.audit_log append-only via a BEFORE UPDATE OR DELETE
--      trigger. REVOKE cannot strip UPDATE/DELETE from the owner role
--      (datapulse owns the table); triggers fire regardless of ownership.
--
-- Run order: after 093_add_pos_device_fingerprint_v2.sql
-- Idempotent: safe to run multiple times (DO ... EXCEPTION guards,
-- CREATE OR REPLACE, DROP TRIGGER IF EXISTS, ON CONFLICT DO NOTHING).
-- Requires: migrations 002 (roles) and 014 (audit_log with RLS).

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('094_harden_db_roles_and_audit.sql')
ON CONFLICT (filename) DO NOTHING;

-- ============================================================
-- Section A — Role-level timeout defaults
-- ============================================================
-- These apply to NEW sessions only; existing sessions keep their current
-- settings until reconnect. deps.py SET LOCAL statement_timeout = '30s'
-- still wins inside an application transaction (tighter than the 15s reader
-- floor and the 2min app ceiling).

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datapulse_reader') THEN
        ALTER ROLE datapulse_reader SET statement_timeout = '15s';
        ALTER ROLE datapulse_reader SET idle_in_transaction_session_timeout = '30s';
        ALTER ROLE datapulse_reader SET lock_timeout = '5s';
    ELSE
        RAISE NOTICE 'Role datapulse_reader not present — skipping reader timeouts';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datapulse') THEN
        ALTER ROLE datapulse SET statement_timeout = '2min';
        ALTER ROLE datapulse SET idle_in_transaction_session_timeout = '5min';
        ALTER ROLE datapulse SET lock_timeout = '10s';
    ELSE
        RAISE NOTICE 'Role datapulse not present — skipping app timeouts';
    END IF;
END $$;

-- ============================================================
-- Section B — audit_log append-only trigger
-- ============================================================
-- Triggers fire against all roles, including the table owner. This is the
-- canonical Postgres pattern for append-only enforcement: REVOKE UPDATE on
-- an owned table is a no-op. Bypass only via superuser +
-- SET session_replication_role = 'replica' (reserved for future retention
-- jobs — never the app).

CREATE OR REPLACE FUNCTION public.audit_log_immutable()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $fn$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only (% blocked)', TG_OP
        USING ERRCODE = 'insufficient_privilege',
              HINT    = 'Use SET session_replication_role = ''replica'' '
                        'from a superuser retention job to bypass.';
END;
$fn$;

DROP TRIGGER IF EXISTS tg_audit_log_immutable ON public.audit_log;
CREATE TRIGGER tg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON public.audit_log
    FOR EACH ROW
    EXECUTE FUNCTION public.audit_log_immutable();

COMMENT ON TRIGGER tg_audit_log_immutable ON public.audit_log IS
    'Enforces append-only on audit_log. UPDATE/DELETE raise '
    'insufficient_privilege regardless of role, including the owner. '
    'Bypass via SET session_replication_role = ''replica'' (superuser only).';

COMMIT;
