-- Migration 120: Add observability permissions for the Prometheus metrics endpoint (#734)
--
-- The GET /api/v1/_metrics endpoint requires the `admin:metrics:read` permission.
-- Grant it to owner and admin roles only (operators/SREs — not end users).

-- 1. Register the new permission
INSERT INTO public.permissions (permission_key, category, description) VALUES
    ('admin:metrics:read', 'admin', 'Read Prometheus latency metrics from /_metrics')
ON CONFLICT (permission_key) DO NOTHING;

-- 2. Grant to owner (all permissions)
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'owner'
  AND p.permission_key = 'admin:metrics:read'
ON CONFLICT DO NOTHING;

-- 3. Grant to admin
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM public.roles r, public.permissions p
WHERE r.role_key = 'admin'
  AND p.permission_key = 'admin:metrics:read'
ON CONFLICT DO NOTHING;
