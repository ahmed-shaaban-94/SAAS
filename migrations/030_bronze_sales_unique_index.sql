-- Migration 030: Add unique index on bronze.sales for pipeline idempotency
-- Prevents duplicate rows when the loader is re-run on the same source files.
-- Composite key: (source_file, billing_document, item_no) — identifies a unique
-- sales line item within a source file. ON CONFLICT DO NOTHING in loader.py
-- relies on this index to silently skip already-loaded rows.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'bronze'
          AND tablename  = 'sales'
          AND indexname  = 'uq_bronze_sales_source_document_item'
    ) THEN
        CREATE UNIQUE INDEX uq_bronze_sales_source_document_item
            ON bronze.sales (source_file, billing_document, item_no)
            WHERE billing_document IS NOT NULL
              AND item_no IS NOT NULL;

        RAISE NOTICE 'Created unique index uq_bronze_sales_source_document_item on bronze.sales';
    ELSE
        RAISE NOTICE 'Index uq_bronze_sales_source_document_item already exists — skipping';
    END IF;
END;
$$;

INSERT INTO public.schema_migrations (filename) VALUES ('030_bronze_sales_unique_index.sql')
    ON CONFLICT (filename) DO NOTHING;
