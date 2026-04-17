-- Migration: 072 — POS RBAC roles and permissions
-- Layer: RBAC / POS
-- Idempotent.
-- Note: Full middleware wiring (PosRoleKey type expansion in Python) is deferred to B7.
--       This migration seeds the roles/permissions data that B7 middleware will reference.
--
-- Schema reference (from migration 024):
--   public.roles       (role_id PK, role_key UNIQUE, role_name, description, is_system)
--   public.permissions (permission_id PK, permission_key UNIQUE, category, description)
--   public.role_permissions (role_id FK, permission_id FK) PK(role_id, permission_id)

-- Insert POS-specific roles
INSERT INTO public.roles (role_key, role_name, description, is_system)
VALUES
    ('pos_cashier',    'POS Cashier',    'Can open terminal, scan items, process checkout', FALSE),
    ('pos_pharmacist', 'POS Pharmacist', 'Can verify controlled substances and approve dispensing', FALSE),
    ('pos_supervisor', 'POS Supervisor', 'Can void transactions, approve returns, view shift summaries', FALSE)
ON CONFLICT (role_key) DO NOTHING;

-- Insert POS-specific permissions
INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:terminal:open',        'pos', 'Start a POS terminal session'),
    ('pos:terminal:close',       'pos', 'Close a POS terminal session'),
    ('pos:transaction:create',   'pos', 'Start a new sales transaction'),
    ('pos:transaction:checkout', 'pos', 'Complete payment and finalize transaction'),
    ('pos:transaction:void',     'pos', 'Cancel a completed transaction'),
    ('pos:return:create',        'pos', 'Accept a drug return and issue refund'),
    ('pos:controlled:verify',    'pos', 'Approve dispensing of a controlled substance'),
    ('pos:shift:view',           'pos', 'View shift cash reconciliation report'),
    ('pos:shift:reconcile',      'pos', 'Approve shift closing variance')
ON CONFLICT (permission_key) DO NOTHING;

-- Map roles to permissions (join by key to get IDs — idempotent via ON CONFLICT DO NOTHING)

-- Cashier permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'pos_cashier'
  AND p.permission_key IN (
      'pos:terminal:open',
      'pos:terminal:close',
      'pos:transaction:create',
      'pos:transaction:checkout'
  )
ON CONFLICT DO NOTHING;

-- Pharmacist permissions (cashier actions + controlled verification)
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'pos_pharmacist'
  AND p.permission_key IN (
      'pos:terminal:open',
      'pos:terminal:close',
      'pos:transaction:create',
      'pos:transaction:checkout',
      'pos:controlled:verify'
  )
ON CONFLICT DO NOTHING;

-- Supervisor permissions (full POS authority)
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'pos_supervisor'
  AND p.category = 'pos'
ON CONFLICT DO NOTHING;
