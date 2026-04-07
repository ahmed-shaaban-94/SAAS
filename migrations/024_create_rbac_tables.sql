-- Migration: RBAC — roles, permissions, tenant_members, sectors, sector_access
-- Phase: 5 (Multi-tenancy & User Management)
--
-- Run order: after 023_add_expression_indexes.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)
--
-- What this does:
--   1. Creates roles table with default roles (owner/admin/editor/viewer)
--   2. Creates permissions table (granular permissions)
--   3. Creates role_permissions mapping
--   4. Creates tenant_members (users within a tenant + role assignment)
--   5. Creates sectors table (business departments / divisions)
--   6. Creates member_sector_access (which member sees which sector)
--   7. RLS policies for all tables

-- ============================================================
-- 1. Roles — application-level roles within a tenant
-- ============================================================

CREATE TABLE IF NOT EXISTS public.roles (
    role_id     SERIAL      PRIMARY KEY,
    role_key    TEXT        NOT NULL UNIQUE,
    role_name   TEXT        NOT NULL,
    description TEXT        NOT NULL DEFAULT '',
    is_system   BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed default roles
INSERT INTO public.roles (role_key, role_name, description, is_system) VALUES
    ('owner',  'Owner',  'Full access — can manage billing, members, and all data', TRUE),
    ('admin',  'Admin',  'Can manage members, sectors, and all analytics', TRUE),
    ('editor', 'Editor', 'Can run pipelines, create reports, and edit data', TRUE),
    ('viewer', 'Viewer', 'Read-only access to assigned sectors', TRUE)
ON CONFLICT (role_key) DO NOTHING;

GRANT SELECT ON TABLE public.roles TO datapulse_reader;

-- ============================================================
-- 2. Permissions — granular permission definitions
-- ============================================================

CREATE TABLE IF NOT EXISTS public.permissions (
    permission_id   SERIAL  PRIMARY KEY,
    permission_key  TEXT    NOT NULL UNIQUE,
    category        TEXT    NOT NULL DEFAULT 'general',
    description     TEXT    NOT NULL DEFAULT ''
);

-- Seed permissions
INSERT INTO public.permissions (permission_key, category, description) VALUES
    -- Analytics
    ('analytics:view',         'analytics', 'View dashboards and analytics'),
    ('analytics:export',       'analytics', 'Export data to CSV/Excel'),
    ('analytics:custom_query', 'analytics', 'Run custom SQL queries via explore'),
    -- Pipeline
    ('pipeline:view',    'pipeline', 'View pipeline status and history'),
    ('pipeline:run',     'pipeline', 'Trigger pipeline runs'),
    ('pipeline:rollback','pipeline', 'Rollback pipeline runs'),
    -- Reports
    ('reports:view',   'reports', 'View reports'),
    ('reports:create', 'reports', 'Create and edit custom reports'),
    -- Targets & Alerts
    ('targets:view',   'targets', 'View goals and targets'),
    ('targets:manage', 'targets', 'Create, edit, delete targets'),
    ('alerts:view',    'alerts',  'View alerts'),
    ('alerts:manage',  'alerts',  'Configure alert rules'),
    -- AI & Insights
    ('insights:view', 'insights', 'View AI insights and anomalies'),
    -- Members & Settings
    ('members:view',   'admin', 'View tenant members'),
    ('members:manage', 'admin', 'Invite, remove, change roles of members'),
    ('sectors:manage', 'admin', 'Create and manage sectors'),
    -- Billing
    ('billing:view',   'billing', 'View billing status'),
    ('billing:manage', 'billing', 'Manage subscription and checkout')
ON CONFLICT (permission_key) DO NOTHING;

GRANT SELECT ON TABLE public.permissions TO datapulse_reader;

-- ============================================================
-- 3. Role-Permission mapping
-- ============================================================

CREATE TABLE IF NOT EXISTS public.role_permissions (
    role_id       INT NOT NULL REFERENCES public.roles(role_id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES public.permissions(permission_id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Owner: all permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'owner'
ON CONFLICT DO NOTHING;

-- Admin: all except billing:manage
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'admin' AND p.permission_key != 'billing:manage'
ON CONFLICT DO NOTHING;

-- Editor: analytics, pipeline, reports, targets, alerts, insights (no admin/billing)
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'editor'
  AND p.category IN ('analytics', 'pipeline', 'reports', 'targets', 'alerts', 'insights')
ON CONFLICT DO NOTHING;

-- Viewer: view-only permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'viewer'
  AND p.permission_key LIKE '%:view'
ON CONFLICT DO NOTHING;

GRANT SELECT ON TABLE public.role_permissions TO datapulse_reader;

-- ============================================================
-- 4. Tenant Members — users belonging to a tenant
-- ============================================================

CREATE TABLE IF NOT EXISTS public.tenant_members (
    member_id   SERIAL      PRIMARY KEY,
    tenant_id   INT         NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    user_id     TEXT        NOT NULL,
    email       TEXT        NOT NULL,
    display_name TEXT       NOT NULL DEFAULT '',
    role_id     INT         NOT NULL REFERENCES public.roles(role_id),
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    invited_by  TEXT,
    invited_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id),
    UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_tenant_members_tenant
    ON public.tenant_members (tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_members_user
    ON public.tenant_members (user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_members_email
    ON public.tenant_members (email);

-- RLS
ALTER TABLE public.tenant_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_members FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS owner_all_tenant_members ON public.tenant_members;
CREATE POLICY owner_all_tenant_members ON public.tenant_members
    FOR ALL TO datapulse USING (true);

DROP POLICY IF EXISTS reader_select_tenant_members ON public.tenant_members;
CREATE POLICY reader_select_tenant_members ON public.tenant_members
    FOR SELECT TO datapulse_reader
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.tenant_members TO datapulse_reader;
GRANT USAGE, SELECT ON SEQUENCE public.tenant_members_member_id_seq TO datapulse_reader;

-- ============================================================
-- 5. Sectors — business divisions within a tenant
-- ============================================================

CREATE TABLE IF NOT EXISTS public.sectors (
    sector_id   SERIAL      PRIMARY KEY,
    tenant_id   INT         NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    sector_key  TEXT        NOT NULL,
    sector_name TEXT        NOT NULL,
    description TEXT        NOT NULL DEFAULT '',
    site_codes  TEXT[]      NOT NULL DEFAULT '{}',
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, sector_key)
);

CREATE INDEX IF NOT EXISTS idx_sectors_tenant
    ON public.sectors (tenant_id);

COMMENT ON TABLE public.sectors IS
    'Business sectors/divisions within a tenant. '
    'site_codes maps to dim_site.site_code for data filtering.';

-- RLS
ALTER TABLE public.sectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sectors FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS owner_all_sectors ON public.sectors;
CREATE POLICY owner_all_sectors ON public.sectors
    FOR ALL TO datapulse USING (true);

DROP POLICY IF EXISTS reader_select_sectors ON public.sectors;
CREATE POLICY reader_select_sectors ON public.sectors
    FOR SELECT TO datapulse_reader
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.sectors TO datapulse_reader;
GRANT USAGE, SELECT ON SEQUENCE public.sectors_sector_id_seq TO datapulse_reader;

-- ============================================================
-- 6. Member-Sector Access — which member can see which sectors
-- ============================================================

CREATE TABLE IF NOT EXISTS public.member_sector_access (
    member_id   INT NOT NULL REFERENCES public.tenant_members(member_id) ON DELETE CASCADE,
    sector_id   INT NOT NULL REFERENCES public.sectors(sector_id) ON DELETE CASCADE,
    granted_by  TEXT,
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (member_id, sector_id)
);

CREATE INDEX IF NOT EXISTS idx_member_sector_member
    ON public.member_sector_access (member_id);
CREATE INDEX IF NOT EXISTS idx_member_sector_sector
    ON public.member_sector_access (sector_id);

COMMENT ON TABLE public.member_sector_access IS
    'Maps members to sectors they can access. '
    'Owners and admins bypass sector filtering (see all data). '
    'Editors and viewers are restricted to assigned sectors.';

-- RLS — uses tenant_members join for tenant scoping
ALTER TABLE public.member_sector_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_sector_access FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS owner_all_member_sector ON public.member_sector_access;
CREATE POLICY owner_all_member_sector ON public.member_sector_access
    FOR ALL TO datapulse USING (true);

DROP POLICY IF EXISTS reader_select_member_sector ON public.member_sector_access;
CREATE POLICY reader_select_member_sector ON public.member_sector_access
    FOR SELECT TO datapulse_reader
    USING (
        member_id IN (
            SELECT m.member_id FROM public.tenant_members m
            WHERE m.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT
        )
    );

GRANT SELECT, INSERT, DELETE ON TABLE public.member_sector_access TO datapulse_reader;

-- ============================================================
-- 7. Update tenants table comment
-- ============================================================
COMMENT ON TABLE bronze.tenants IS
    'Tenant registry. Each tenant has members (tenant_members), '
    'sectors (sectors), and billing (subscriptions). '
    'RLS uses SET LOCAL app.tenant_id to scope all queries.';
