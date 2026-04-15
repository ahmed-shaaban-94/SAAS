-- Migration: 060 — Add notes column to bronze.batches
-- Layer: Bronze
-- Idempotent.

ALTER TABLE bronze.batches
    ADD COLUMN IF NOT EXISTS notes TEXT;

COMMENT ON COLUMN bronze.batches.notes IS
    'Optional free-text notes captured during batch import or lifecycle updates.';
