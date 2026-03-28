-- Migration: Create dedicated schema for n8n workflow engine
-- Layer: Infrastructure / Orchestration
-- Phase: 2.1 (n8n Infrastructure & Connectivity)
--
-- Run order: after 003_add_tenant_id.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- What this does:
--   1. Creates the n8n schema for workflow engine tables
--   2. Comments the schema for documentation
--   3. Grants full DDL/DML rights to datapulse user
--   4. Sets default privileges so future tables/sequences are accessible
--
-- The datapulse user is the main DB user that n8n connects as.
-- n8n needs full rights to create and manage its own tables within this schema.

-- ============================================================
-- 1. Create n8n schema
-- ============================================================
CREATE SCHEMA IF NOT EXISTS n8n;

COMMENT ON SCHEMA n8n IS 'Schema for n8n workflow engine — stores workflow definitions, executions, credentials, and webhook data';

-- ============================================================
-- 2. Grant schema-level privileges to datapulse
-- ============================================================
GRANT ALL ON SCHEMA n8n TO datapulse;

-- ============================================================
-- 3. Default privileges for future objects in n8n schema
-- ============================================================
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n
    GRANT ALL ON TABLES TO datapulse;

ALTER DEFAULT PRIVILEGES IN SCHEMA n8n
    GRANT ALL ON SEQUENCES TO datapulse;
