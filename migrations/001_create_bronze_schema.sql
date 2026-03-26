-- Migration: Create bronze schema and sales table (medallion architecture)
-- Layer: Bronze (raw data, as-is from source)

CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.sales (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Source tracking
    source_file     TEXT        NOT NULL,
    source_quarter  TEXT        NOT NULL,   -- e.g. 'Q1.2023'
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Transaction identifiers
    reference_no    TEXT,
    date            DATE,
    billing_document TEXT,
    billing_type    TEXT,
    billing_type2   TEXT,
    fi_document_no  TEXT,
    crm_order       TEXT,
    knumv           TEXT,
    item_no         TEXT,

    -- Product
    material        TEXT,
    material_desc   TEXT,
    brand           TEXT,
    item_cluster    TEXT,
    item_status     TEXT,
    mat_group       TEXT,
    mat_group_short TEXT,
    cosm_mg         TEXT,

    -- Classification
    category        TEXT,
    subcategory     TEXT,
    division        TEXT,
    segment         TEXT,

    -- Customer / Site
    customer        TEXT,
    customer_name   TEXT,
    site            TEXT,
    site_name       TEXT,
    buyer           TEXT,

    -- Personnel
    personel_number TEXT,
    person_name     TEXT,
    position        TEXT,
    area_mg         TEXT,

    -- Financials
    quantity        DOUBLE PRECISION,
    net_sales       DOUBLE PRECISION,
    gross_sales     DOUBLE PRECISION,
    sales_not_tax   DOUBLE PRECISION,
    dis_tax         DOUBLE PRECISION,
    tax             DOUBLE PRECISION,
    paid            BIGINT,
    kzwi1           DOUBLE PRECISION,
    subtotal5_discount DOUBLE PRECISION,
    add_dis         BIGINT,

    -- Insurance
    insurance_tel   TEXT,
    insurance_no    TEXT,

    -- Other
    certification   TEXT,
    assignment      TEXT,
    ref_return_date TEXT,
    ref_return      TEXT
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_bronze_sales_date ON bronze.sales (date);
CREATE INDEX IF NOT EXISTS idx_bronze_sales_quarter ON bronze.sales (source_quarter);
CREATE INDEX IF NOT EXISTS idx_bronze_sales_customer ON bronze.sales (customer);
CREATE INDEX IF NOT EXISTS idx_bronze_sales_material ON bronze.sales (material);
CREATE INDEX IF NOT EXISTS idx_bronze_sales_category ON bronze.sales (category);
CREATE INDEX IF NOT EXISTS idx_bronze_sales_brand ON bronze.sales (brand);
CREATE INDEX IF NOT EXISTS idx_bronze_sales_site ON bronze.sales (site);

COMMENT ON TABLE bronze.sales IS 'Bronze layer — raw sales data imported from quarterly Excel files';
COMMENT ON COLUMN bronze.sales.source_file IS 'Original Excel filename (e.g. Q1.2023.xlsx)';
COMMENT ON COLUMN bronze.sales.source_quarter IS 'Quarter identifier extracted from filename';
