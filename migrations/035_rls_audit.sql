-- Migration 035: RLS audit — warn on tables without Row Level Security
-- Idempotent: safe to run multiple times (read-only audit, no schema changes)
-- Runs at startup via prestart.sh; failures surface in CI logs.

DO $$
DECLARE
    rec     RECORD;
    count   INT := 0;
    summary TEXT := '';
BEGIN
    -- Check all user-managed schemas for tables that lack RLS
    FOR rec IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname IN ('bronze', 'public_staging', 'public_marts', 'public')
          AND tablename NOT LIKE 'pg_%'
          AND tablename NOT IN (
              -- System / migration tracking tables that intentionally have no RLS
              'schema_migrations',
              'n8n_jobs',
              'n8n_workflows'
          )
          AND rowsecurity = false
        ORDER BY schemaname, tablename
    LOOP
        count  := count + 1;
        summary := summary || format('  - %I.%I', rec.schemaname, rec.tablename) || E'\n';
    END LOOP;

    IF count > 0 THEN
        RAISE WARNING
            'RLS_AUDIT: % table(s) found WITHOUT Row Level Security:%s'
            'Run: ALTER TABLE <schema>.<table> ENABLE ROW LEVEL SECURITY; FORCE ROW LEVEL SECURITY;',
            count, E'\n' || summary;
    ELSE
        RAISE NOTICE 'RLS_AUDIT: All tables in monitored schemas have RLS enabled. OK';
    END IF;
END $$;
