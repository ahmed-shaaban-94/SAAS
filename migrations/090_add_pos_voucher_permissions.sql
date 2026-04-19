-- Migration: 090 — POS voucher permission slugs
-- Layer: rbac (public.permissions + public.role_permissions)
-- Idempotent.
--
-- Adds permission slugs for voucher management and validation.
-- Follows the convention from migration 085 and 072.

INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:voucher:manage',   'pos', 'Create, list, and manage discount vouchers (admin / supervisor)'),
    ('pos:voucher:validate', 'pos', 'Validate a voucher code at checkout (cashier)')
ON CONFLICT (permission_key) DO NOTHING;

-- Supervisor + Manager roles get the manage permission.
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
  FROM public.roles r, public.permissions p
 WHERE r.role_key IN ('pos_supervisor', 'pos_manager')
   AND p.permission_key = 'pos:voucher:manage'
ON CONFLICT DO NOTHING;

-- All POS-facing roles can validate a voucher at checkout.
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
  FROM public.roles r, public.permissions p
 WHERE r.role_key IN ('pos_cashier', 'pos_pharmacist', 'pos_supervisor', 'pos_manager')
   AND p.permission_key = 'pos:voucher:validate'
ON CONFLICT DO NOTHING;
