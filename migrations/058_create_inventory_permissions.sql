-- Migration: 058 — RBAC permissions for pharmaceutical platform domains
-- Layer: Application
-- Idempotent: safe to run multiple times (ON CONFLICT DO NOTHING)
--
-- Permission matrix:
--   | Permission              | owner | admin | editor | viewer |
--   | inventory:read          |   Y   |   Y   |   Y    |   Y    |
--   | inventory:write         |   Y   |   Y   |   Y    |   -    |
--   | inventory:adjust        |   Y   |   Y   |   Y    |   -    |
--   | dispensing:read         |   Y   |   Y   |   Y    |   Y    |
--   | expiry:read             |   Y   |   Y   |   Y    |   Y    |
--   | expiry:write            |   Y   |   Y   |   Y    |   -    |
--   | purchase_orders:read    |   Y   |   Y   |   Y    |   Y    |
--   | purchase_orders:write   |   Y   |   Y   |   Y    |   -    |
--   | suppliers:read          |   Y   |   Y   |   Y    |   Y    |
--   | suppliers:write         |   Y   |   Y   |   -    |   -    |

-- ============================================================
-- 1. Seed permissions
-- ============================================================
INSERT INTO public.permissions (permission_key, category, description) VALUES
    ('inventory:read',         'inventory', 'View stock levels, receipts, and adjustments'),
    ('inventory:write',        'inventory', 'Create and edit stock receipts and adjustments'),
    ('inventory:adjust',       'inventory', 'Post manual stock adjustments'),
    ('dispensing:read',        'dispensing', 'View dispensing and POS transaction records'),
    ('expiry:read',            'expiry', 'View batch expiry dates and near-expiry alerts'),
    ('expiry:write',           'expiry', 'Update batch status and quarantine records'),
    ('purchase_orders:read',   'purchase_orders', 'View purchase orders and line items'),
    ('purchase_orders:write',  'purchase_orders', 'Create and manage purchase orders'),
    ('suppliers:read',         'suppliers', 'View supplier directory'),
    ('suppliers:write',        'suppliers', 'Create and edit supplier records')
ON CONFLICT (permission_key) DO NOTHING;

-- ============================================================
-- 2. Grant to owner (all inventory permissions)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'owner'
  AND p.category IN ('inventory', 'dispensing', 'expiry', 'purchase_orders', 'suppliers')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 3. Grant to admin (all inventory permissions)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'admin'
  AND p.category IN ('inventory', 'dispensing', 'expiry', 'purchase_orders', 'suppliers')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 4. Grant to editor (all except suppliers:write)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'editor'
  AND p.permission_key IN (
    'inventory:read',
    'inventory:write',
    'inventory:adjust',
    'dispensing:read',
    'expiry:read',
    'expiry:write',
    'purchase_orders:read',
    'purchase_orders:write',
    'suppliers:read'
  )
ON CONFLICT DO NOTHING;

-- ============================================================
-- 5. Grant to viewer (read-only permissions)
-- ============================================================
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'viewer'
  AND p.permission_key IN (
    'inventory:read',
    'dispensing:read',
    'expiry:read',
    'purchase_orders:read',
    'suppliers:read'
  )
ON CONFLICT DO NOTHING;
