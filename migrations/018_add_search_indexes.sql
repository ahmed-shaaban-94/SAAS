-- Migration: 018 – Trigram search indexes for fuzzy matching
-- Layer: marts
-- Wrapped in schema check: public_marts is dbt-managed and may not exist in CI.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$ BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.schemata
    WHERE schema_name = 'public_marts'
) THEN
    CREATE INDEX IF NOT EXISTS idx_dim_product_name_trgm
        ON public_marts.dim_product USING gin (drug_name gin_trgm_ops);

    CREATE INDEX IF NOT EXISTS idx_dim_customer_name_trgm
        ON public_marts.dim_customer USING gin (customer_name gin_trgm_ops);

    CREATE INDEX IF NOT EXISTS idx_dim_staff_name_trgm
        ON public_marts.dim_staff USING gin (staff_name gin_trgm_ops);
ELSE
    RAISE NOTICE 'public_marts schema does not exist yet — skipping trigram indexes';
END IF;
END $$;
