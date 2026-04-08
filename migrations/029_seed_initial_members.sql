-- Migration: Seed initial tenant members
-- Run order: after 028_create_resellers.sql
-- Idempotent: ON CONFLICT DO UPDATE — safe to re-run

-- admin@rahmaqanater.org  → owner  (full access + billing)
-- dr.engy@saas.com        → admin  (all except billing:manage)

-- Remove any auto-registered viewer record with no email (created before seed on first login)
DELETE FROM public.tenant_members WHERE email = '' AND tenant_id = 1;

INSERT INTO public.tenant_members (tenant_id, user_id, email, display_name, role_id, is_active)
VALUES
    (
        1,
        'auth0|69cda0f07f8bd755b439b92c',
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
        user_id    = EXCLUDED.user_id,
        is_active  = EXCLUDED.is_active;
