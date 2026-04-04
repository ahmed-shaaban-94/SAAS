-- 016: Add composite indexes on fct_sales for common query patterns
-- Idempotent: uses IF NOT EXISTS

BEGIN;

-- Accelerate product-filtered queries with tenant isolation
CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_product
    ON public_marts.fct_sales (tenant_id, product_key);

-- Accelerate customer-filtered queries with tenant isolation
CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_customer
    ON public_marts.fct_sales (tenant_id, customer_key);

-- Accelerate staff-filtered queries with tenant isolation
CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_staff
    ON public_marts.fct_sales (tenant_id, staff_key);

-- Accelerate date-range queries with tenant isolation
CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_date
    ON public_marts.fct_sales (tenant_id, date_key);

COMMIT;
