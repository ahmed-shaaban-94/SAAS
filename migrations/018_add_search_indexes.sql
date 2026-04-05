-- Migration: 018 – Trigram search indexes for fuzzy matching
-- Layer: marts

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_dim_product_name_trgm
    ON public_marts.dim_product USING gin (product_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dim_customer_name_trgm
    ON public_marts.dim_customer USING gin (customer_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dim_staff_name_trgm
    ON public_marts.dim_staff USING gin (staff_name gin_trgm_ops);
