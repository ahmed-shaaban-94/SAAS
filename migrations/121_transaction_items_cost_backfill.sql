-- Migration 121 — Backfill cost_per_unit on pos.transaction_items
--               + seed pos:cost:read permission and grant to supervisor role
-- Layer: POS / RBAC
-- Idempotent.
--
-- Backfill: Uses unit_price × 0.70 as a conservative cost proxy for
-- historical rows where cost was not captured at point of sale.
-- Real cost capture starts from migration 119 forward.
-- Only touches NULL rows — safe to run multiple times.
--
-- Permission: pos:cost:read gates exposure of cost_per_unit on the
-- GET /transactions/{id} API response. Granted to pos_supervisor and
-- admin roles only.

DO $$
BEGIN
  UPDATE pos.transaction_items
  SET cost_per_unit = ROUND(unit_price * 0.70, 4)
  WHERE cost_per_unit IS NULL;
END
$$;

-- Seed pos:cost:read permission (idempotent)
INSERT INTO public.permissions (permission_key, category, description)
VALUES ('pos:cost:read', 'pos', 'View cost_per_unit on POS transaction line items')
ON CONFLICT (permission_key) DO NOTHING;

-- Grant to pos_supervisor role
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'pos_supervisor'
  AND p.permission_key = 'pos:cost:read'
ON CONFLICT DO NOTHING;

-- Grant to admin role (admin has full POS authority)
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'admin'
  AND p.permission_key = 'pos:cost:read'
ON CONFLICT DO NOTHING;
