-- Migration: 076 — POS manager role + pharmacist PIN hash column
-- Layer: RBAC / POS
-- Idempotent: safe to run multiple times.
--
-- Context (B7):
--   Migration 072 seeded 3 POS roles (cashier, pharmacist, supervisor).
--   B7 wires RBAC guards into the POS routes and requires a 4th role:
--   `pos_manager` — full authority over POS operations + reporting.
--
--   This migration also adds `pharmacist_pin_hash` to `tenant_members`
--   to support the pharmacist PIN verification flow for controlled substances.
--   The column is nullable: only pharmacist members need a PIN hash set.
--   PIN hashes use SHA-256 (hex digest). Setting the PIN is handled via the
--   admin API; this column is NEVER returned in API responses.

-- ── 1. pos_manager role ──────────────────────────────────────────────────────

INSERT INTO public.roles (role_key, role_name, description, is_system)
VALUES (
    'pos_manager',
    'POS Manager',
    'Full POS authority: terminals, transactions, void, returns, shifts, and reconciliation reporting',
    FALSE
)
ON CONFLICT (role_key) DO NOTHING;

-- pos_manager gets ALL pos:* permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'pos_manager'
  AND p.category  = 'pos'
ON CONFLICT DO NOTHING;

-- ── 2. pharmacist_pin_hash column ────────────────────────────────────────────

ALTER TABLE public.tenant_members
    ADD COLUMN IF NOT EXISTS pharmacist_pin_hash TEXT DEFAULT NULL;

COMMENT ON COLUMN public.tenant_members.pharmacist_pin_hash IS
    'SHA-256 hex digest of the pharmacist PIN used for controlled-substance '
    'dispensing verification at the POS terminal. NULL for non-pharmacist members. '
    'Never returned in API responses.';
