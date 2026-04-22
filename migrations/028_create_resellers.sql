-- Migration: Reseller Management — reseller accounts, commissions, payouts
-- Phase: 7.4 (White-Label / Reseller Mode)
-- Run order: after 027_create_branding.sql
-- Idempotent: safe to run multiple times (IF NOT EXISTS / DO $$ guards)

-- ============================================================
-- 1. Resellers — partner organizations that resell DataPulse
-- ============================================================
CREATE TABLE IF NOT EXISTS public.resellers (
    reseller_id         SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    contact_email       TEXT NOT NULL,
    contact_name        TEXT,
    commission_pct      NUMERIC(5, 2) NOT NULL DEFAULT 20.00,
    stripe_connect_id   TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. Link tenants to resellers
-- ============================================================
ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS reseller_id INT REFERENCES public.resellers(reseller_id);

-- ============================================================
-- 3. Commissions — track earned commissions per reseller
-- ============================================================
CREATE TABLE IF NOT EXISTS public.reseller_commissions (
    id                  SERIAL PRIMARY KEY,
    reseller_id         INT NOT NULL REFERENCES public.resellers(reseller_id),
    tenant_id           INT NOT NULL,
    period              TEXT NOT NULL,
    mrr_amount          NUMERIC(18, 4) NOT NULL DEFAULT 0,
    commission_amount   NUMERIC(18, 4) NOT NULL DEFAULT 0,
    commission_pct      NUMERIC(5, 2) NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'paid')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reseller_id, tenant_id, period)
);

-- ============================================================
-- 4. Payouts — payout history for resellers
-- ============================================================
CREATE TABLE IF NOT EXISTS public.reseller_payouts (
    id                  SERIAL PRIMARY KEY,
    reseller_id         INT NOT NULL REFERENCES public.resellers(reseller_id),
    amount              NUMERIC(18, 4) NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'USD',
    stripe_transfer_id  TEXT,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    period_from         TEXT NOT NULL,
    period_to           TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 5. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_reseller_commissions_reseller
    ON public.reseller_commissions (reseller_id, period);

CREATE INDEX IF NOT EXISTS idx_reseller_payouts_reseller
    ON public.reseller_payouts (reseller_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tenants_reseller
    ON bronze.tenants (reseller_id)
    WHERE reseller_id IS NOT NULL;

-- ============================================================
-- 6. Grants
-- ============================================================
GRANT SELECT ON TABLE public.resellers TO datapulse_reader;
GRANT SELECT ON TABLE public.reseller_commissions TO datapulse_reader;
GRANT SELECT ON TABLE public.reseller_payouts TO datapulse_reader;
