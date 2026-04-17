-- Migration: 046 — Control Center: RBAC permissions
-- Layer: application / control_center
-- Phase: Control Center Phase 1a (Foundation)
--
-- Run order: after 045_control_center_sync_jobs.sql
-- Idempotent: safe to run multiple times (ON CONFLICT DO NOTHING)
--
-- What this does:
--   1. Seeds 9 new permissions under category 'control_center' in the
--      existing public.permissions table (created by migration 024).
--   2. Maps permissions to owner/admin/editor/viewer roles per the plan's
--      RBAC matrix (§6).
--
-- Permission matrix (plan §6):
--   | Permission                          | owner | admin | editor | viewer |
--   | connections:view                    |   Y   |   Y   |   Y    |   Y    |
--   | connections:manage                  |   Y   |   Y   |   -    |   -    |
--   | profiles:view                       |   Y   |   Y   |   Y    |   Y    |
--   | profiles:manage                     |   Y   |   Y   |   -    |   -    |
--   | mappings:manage                     |   Y   |   Y   |   Y    |   -    |
--   | pipeline:preview                    |   Y   |   Y   |   Y    |   -    |
--   | pipeline:publish                    |   Y   |   Y   |   -    |   -    |
--   | pipeline:rollback                   |   Y   |   -   |   -    |   -    |
--   | sync:run                            |   Y   |   Y   |   -    |   -    |

-- ============================================================
-- 1. Seed permissions
-- ============================================================
INSERT INTO public.permissions (permission_key, category, description) VALUES
    ('control_center:connections:view',   'control_center', 'View Control Center source connections'),
    ('control_center:connections:manage', 'control_center', 'Create, edit, delete source connections'),
    ('control_center:profiles:view',      'control_center', 'View Control Center pipeline profiles'),
    ('control_center:profiles:manage',    'control_center', 'Create, edit, delete pipeline profiles'),
    ('control_center:mappings:manage',    'control_center', 'Create, edit mapping templates'),
    ('control_center:pipeline:preview',   'control_center', 'Run preview/validation on drafts'),
    ('control_center:pipeline:publish',   'control_center', 'Publish draft to release'),
    ('control_center:pipeline:rollback',  'control_center', 'Roll back to a previous release'),
    ('control_center:sync:run',           'control_center', 'Trigger a manual sync job')
ON CONFLICT (permission_key) DO NOTHING;

-- ============================================================
-- 2. Grant to owner (all)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'owner' AND p.category = 'control_center'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 3. Grant to admin (all except rollback)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'admin'
  AND p.category = 'control_center'
  AND p.permission_key != 'control_center:pipeline:rollback'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 4. Grant to editor (view + mappings + preview)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'editor'
  AND p.permission_key IN (
    'control_center:connections:view',
    'control_center:profiles:view',
    'control_center:mappings:manage',
    'control_center:pipeline:preview'
  )
ON CONFLICT DO NOTHING;

-- ============================================================
-- 5. Grant to viewer (view-only)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'viewer'
  AND p.permission_key IN (
    'control_center:connections:view',
    'control_center:profiles:view'
  )
ON CONFLICT DO NOTHING;
