-- Migration 121 — Backfill cost_per_unit on pos.transaction_items
--               + seed pos:cost:read permission and grant to supervisor role
-- Layer: POS / RBAC
-- Idempotent.
--
-- Backfill assumption (H10, audit 2026-04-26):
--   Historical rows that pre-date migration 119 had no cost captured at
--   point of sale, so we estimate cost as ``unit_price * 0.70`` — a 30%
--   gross margin proxy chosen as conservative for general OTC pharma
--   retail in EG. Real cost capture starts from migration 119 forward;
--   this constant never overwrites a captured value (the WHERE
--   ``cost_per_unit IS NULL`` clause guards that).
--
--   This single ratio assumes the tenant population is reasonably
--   uniform. If a future tenant onboards with a materially different
--   margin profile (high-cost specialty, generics-only, etc.), replace
--   this constant with a per-tenant override (``cost_proxy_pct`` on a
--   tenants config table or a new Settings field). Until that need is
--   real, keep the literal — adding a config knob for one tenant is
--   premature abstraction.
--
--   The DO $$ ... $$ block is implicitly transactional in Postgres, so
--   no explicit BEGIN/COMMIT is needed for atomicity.
--
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
