-- Migration 119 — Add cost_per_unit to pos.transaction_items
-- Required for per-basket margin computation (POS Legend Q1 row 4).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'pos' AND table_name = 'transaction_items'
    AND column_name = 'cost_per_unit'
  ) THEN
    ALTER TABLE pos.transaction_items
      ADD COLUMN cost_per_unit NUMERIC(18,4);
  END IF;
END
$$;
