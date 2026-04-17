-- Migration: 074 — Verify and idempotently re-apply RLS on all pos.* tables
-- Layer: POS operational
-- Idempotent. Safety-net verification pass — RLS was applied inline in 065-071b.
-- (MEDIUM-1 fix from adversarial review: closes the window between table creation and RLS.)

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM   pg_tables
        WHERE  schemaname = 'pos'
        ORDER  BY tablename
    LOOP
        EXECUTE format('ALTER TABLE pos.%I ENABLE ROW LEVEL SECURITY', tbl);
        EXECUTE format('ALTER TABLE pos.%I FORCE  ROW LEVEL SECURITY',  tbl);
        RAISE NOTICE 'RLS verified on pos.%', tbl;
    END LOOP;
END $$;

-- Sanity check: assert no pos.* tables are missing RLS.
-- This DO block raises an exception (failing the migration) if any table lacks RLS.
DO $$
DECLARE
    missing_count INT;
BEGIN
    SELECT COUNT(*)
    INTO   missing_count
    FROM   pg_tables t
    JOIN   pg_class  c ON c.relname = t.tablename
                      AND c.relnamespace = (
                              SELECT oid FROM pg_namespace WHERE nspname = 'pos'
                          )
    WHERE  t.schemaname    = 'pos'
    AND    c.relrowsecurity = false;

    IF missing_count > 0 THEN
        RAISE EXCEPTION 'BUG: % pos.* table(s) are missing RLS', missing_count;
    END IF;
END $$;
