-- Migration: 086 – Onboarding cross-device sync columns
-- Layer: application
--
-- Run order: after 085_*.sql
-- Idempotent: safe to run multiple times (ADD COLUMN IF NOT EXISTS)
--
-- Adds two columns to public.onboarding to support backend-persisted
-- state for the OnboardingStrip (golden-path TTFI progress) and the
-- FirstInsightCard (dismissal timestamp), enabling cross-device/cross-
-- browser sync. Phase 2 Follow-up #6.

ALTER TABLE public.onboarding
    ADD COLUMN IF NOT EXISTS golden_path_progress       JSONB        NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS first_insight_dismissed_at TIMESTAMPTZ;

COMMENT ON COLUMN public.onboarding.golden_path_progress IS
    'OnboardingStrip TTFI milestone state — mirrors ttfi_onboarding_strip_v1 localStorage shape';

COMMENT ON COLUMN public.onboarding.first_insight_dismissed_at IS
    'Timestamp when the FirstInsightCard was dismissed; NULL = not yet dismissed';
