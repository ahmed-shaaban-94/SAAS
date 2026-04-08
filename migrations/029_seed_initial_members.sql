-- Migration: Seed initial tenant members
-- Run order: after 028_create_resellers.sql
-- Idempotent: ON CONFLICT DO UPDATE — safe to re-run

-- admin@rahmaqanater.org  → owner  (full access + billing)
-- dr.engy@saas.com        → admin  (all except billing:manage)

INSERT INTO public.tenant_members (tenant_id, user_id, email, display_name, role_id, is_active)
VALUES
    (
        1,
        'admin@rahmaqanater.org',
        'admin@rahmaqanater.org',
        'Admin Rahmaqanater',
        (SELECT role_id FROM public.roles WHERE role_key = 'owner'),
        TRUE
    ),
    (
        1,
        'dr.engy@saas.com',
        'dr.engy@saas.com',
        'Dr. Engy',
        (SELECT role_id FROM public.roles WHERE role_key = 'admin'),
        TRUE
    )
ON CONFLICT (tenant_id, email) DO UPDATE
    SET role_id    = EXCLUDED.role_id,
        is_active  = EXCLUDED.is_active;
