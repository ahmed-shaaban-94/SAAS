-- Migration: 085 — POS M1 permission slugs
-- Layer: rbac (public.permissions + public.role_permissions)
-- Idempotent.
--
-- Adds permission slugs for the new M1 endpoints (device registration,
-- grant refresh, override reconciliation). Follows the convention
-- established in migration 072 (public.permissions.permission_key).

INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:device:register',    'pos', 'Register a new POS terminal device (admin / supervisor)'),
    ('pos:device:revoke',      'pos', 'Revoke a POS terminal device binding (admin / supervisor)'),
    ('pos:grant:refresh',      'pos', 'Refresh offline grant for an active shift'),
    ('pos:override:reconcile', 'pos', 'Use supervisor override to reconcile a rejected provisional sale')
ON CONFLICT (permission_key) DO NOTHING;

-- Supervisor gets every pos-category permission (including the new four).
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
  FROM public.roles r, public.permissions p
 WHERE r.role_key = 'pos_supervisor'
   AND p.permission_key IN (
       'pos:device:register',
       'pos:device:revoke',
       'pos:grant:refresh',
       'pos:override:reconcile'
   )
ON CONFLICT DO NOTHING;

-- Pharmacist gets override:reconcile so they can resolve rejected provisional sales.
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
  FROM public.roles r, public.permissions p
 WHERE r.role_key = 'pos_pharmacist'
   AND p.permission_key = 'pos:override:reconcile'
ON CONFLICT DO NOTHING;
