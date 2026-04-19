-- Migration: 092 — POS promotion permission slugs
-- Layer: rbac (public.permissions + public.role_permissions)
-- Idempotent.
--
-- Adds permission slugs for promotion management and cashier-side
-- application. Mirrors migration 090 for vouchers.

INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:promotion:manage', 'pos', 'Create, list, activate, and pause discount promotions (admin / supervisor)'),
    ('pos:promotion:apply',  'pos', 'Apply an eligible promotion to a transaction at checkout (cashier)')
ON CONFLICT (permission_key) DO NOTHING;

-- Supervisor + Manager roles get the manage permission.
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
  FROM public.roles r, public.permissions p
 WHERE r.role_key IN ('pos_supervisor', 'pos_manager')
   AND p.permission_key = 'pos:promotion:manage'
ON CONFLICT DO NOTHING;

-- All POS-facing roles can apply a promotion at checkout.
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
  FROM public.roles r, public.permissions p
 WHERE r.role_key IN ('pos_cashier', 'pos_pharmacist', 'pos_supervisor', 'pos_manager')
   AND p.permission_key = 'pos:promotion:apply'
ON CONFLICT DO NOTHING;
