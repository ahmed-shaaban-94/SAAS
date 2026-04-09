-- Migration: Add FK constraints from gamification tables to bronze.tenants
-- Phase: H3.9 — Data integrity hardening
-- Run order: after 026_create_gamification.sql
-- Idempotent: safe to run multiple times (constraint name checks)

DO $$ BEGIN
    ALTER TABLE public.badges
        ADD CONSTRAINT fk_badges_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.staff_badges
        ADD CONSTRAINT fk_staff_badges_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.streaks
        ADD CONSTRAINT fk_streaks_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.competitions
        ADD CONSTRAINT fk_competitions_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.competition_entries
        ADD CONSTRAINT fk_competition_entries_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.xp_ledger
        ADD CONSTRAINT fk_xp_ledger_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.staff_levels
        ADD CONSTRAINT fk_staff_levels_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.gamification_feed
        ADD CONSTRAINT fk_gamification_feed_tenant
        FOREIGN KEY (tenant_id) REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
