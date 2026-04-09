-- Migration 030: Enable pg_stat_statements for query performance monitoring
--
-- pg_stat_statements tracks execution statistics for all SQL statements.
-- Requires: shared_preload_libraries = 'pg_stat_statements' in postgresql.conf
--           (already configured in postgres/postgresql.conf)
--
-- Usage:
--   SELECT query, calls, mean_exec_time, total_exec_time, rows
--   FROM pg_stat_statements
--   ORDER BY total_exec_time DESC LIMIT 20;
--
-- Reset stats (e.g. after a deploy):
--   SELECT pg_stat_statements_reset();
--
-- Rollback: DROP EXTENSION IF EXISTS pg_stat_statements;

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Grant datapulse_reader access to view query stats
GRANT SELECT ON pg_stat_statements TO datapulse_reader;

COMMIT;
