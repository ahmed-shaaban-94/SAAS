-- Migration: 087 – Lead capture table
-- Layer: application (public schema, no RLS — admin-owned, no tenant scoping)
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS public.leads (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    name        TEXT,
    company     TEXT,
    use_case    TEXT,
    team_size   TEXT,
    tier        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_email
    ON public.leads(email);

CREATE INDEX IF NOT EXISTS idx_leads_created_at
    ON public.leads(created_at DESC);

COMMENT ON TABLE public.leads IS 'Pilot access / waitlist lead capture — one row per email';
