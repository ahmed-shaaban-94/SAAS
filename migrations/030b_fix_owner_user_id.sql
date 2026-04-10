-- Migration: Fix owner user_id to match Auth0 sub
-- Run order: after 029_seed_initial_members.sql
-- Idempotent: safe to re-run

-- Problem: migration 029 seeded the owner row with user_id = email
-- (admin@rahmaqanater.org) instead of the real Auth0 subject claim.
-- When the owner logs in, RBAC looks up by user_id (Auth0 sub), finds
-- nothing, and auto-registers them as a viewer. This migration corrects
-- the user_id to the real Auth0 sub so the owner role is resolved correctly.

-- Step 1: Remove any orphan auto-registered viewer record for the owner
-- (created by ensure_member_exists when user_id lookup failed on first login)
DELETE FROM public.tenant_members
WHERE tenant_id = 1
  AND user_id = 'auth0|69cda0f07f8bd755b439b92c'
  AND role_id = (SELECT role_id FROM public.roles WHERE role_key = 'viewer');

-- Step 2: Update the seeded owner record to use the real Auth0 sub
UPDATE public.tenant_members
SET user_id = 'auth0|69cda0f07f8bd755b439b92c'
WHERE tenant_id = 1
  AND email = 'admin@rahmaqanater.org'
  AND user_id != 'auth0|69cda0f07f8bd755b439b92c';  -- no-op if already correct
