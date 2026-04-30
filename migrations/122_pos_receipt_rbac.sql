-- Migration: 122 - POS receipt RBAC permissions
-- Layer: POS operational / RBAC
-- Idempotent.

-- Receipt PDF/thermal views expose customer transaction artifacts, and
-- receipt email/WhatsApp sends are customer-facing side effects. Gate them
-- explicitly instead of relying only on authenticated POS plan access.
INSERT INTO public.permissions (permission_key, category, description)
VALUES
    ('pos:receipt:read', 'pos', 'View POS receipt PDF and thermal artifacts'),
    ('pos:receipt:send', 'pos', 'Send POS receipts by email or WhatsApp')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key IN ('pos_cashier', 'pos_pharmacist', 'pos_supervisor', 'admin', 'owner')
  AND p.permission_key IN ('pos:receipt:read', 'pos:receipt:send')
ON CONFLICT DO NOTHING;
