-- Migration: Tenant Branding & White-Label Configuration
-- Phase: 7.1 (White-Label / Reseller Mode)
-- Run order: after 026_create_gamification.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)

-- ============================================================
-- 1. Tenant Branding — per-tenant visual customization
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tenant_branding (
    tenant_id           INT PRIMARY KEY REFERENCES bronze.tenants(tenant_id),
    -- Identity
    company_name        TEXT NOT NULL DEFAULT 'DataPulse',
    logo_url            TEXT,
    favicon_url         TEXT,
    -- Colors
    primary_color       TEXT NOT NULL DEFAULT '#4F46E5',
    accent_color        TEXT NOT NULL DEFAULT '#D97706',
    sidebar_bg          TEXT,
    -- Typography
    font_family         TEXT NOT NULL DEFAULT 'Inter',
    -- Domain
    custom_domain       TEXT UNIQUE,
    subdomain           TEXT UNIQUE,
    -- Email branding
    email_from_name     TEXT,
    email_logo_url      TEXT,
    -- Footer & support
    footer_text         TEXT,
    support_email       TEXT,
    support_url         TEXT,
    -- White-label flags
    hide_datapulse_branding BOOLEAN NOT NULL DEFAULT FALSE,
    custom_login_bg     TEXT,
    -- Metadata
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. Row-Level Security
-- ============================================================
DO $$ BEGIN
    ALTER TABLE public.tenant_branding ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.tenant_branding FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY branding_owner ON public.tenant_branding FOR ALL TO datapulse
        USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY branding_reader ON public.tenant_branding FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 3. Grants
-- ============================================================
GRANT SELECT ON TABLE public.tenant_branding TO datapulse_reader;

-- ============================================================
-- 4. Seed default branding for tenant 1
-- ============================================================
INSERT INTO public.tenant_branding (tenant_id, company_name)
VALUES (1, 'DataPulse')
ON CONFLICT (tenant_id) DO NOTHING;

-- ============================================================
-- 5. Domain lookup index
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_branding_custom_domain
    ON public.tenant_branding (custom_domain)
    WHERE custom_domain IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_branding_subdomain
    ON public.tenant_branding (subdomain)
    WHERE subdomain IS NOT NULL;
