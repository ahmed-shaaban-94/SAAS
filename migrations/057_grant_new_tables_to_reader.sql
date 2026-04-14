-- Migration: 057 — Consolidating GRANT SELECT for all new pharma tables
-- Layer: Infrastructure
-- Idempotent. (Re-granting is safe in PostgreSQL)

GRANT SELECT ON TABLE bronze.stock_receipts    TO datapulse_reader;
GRANT SELECT ON TABLE bronze.stock_adjustments TO datapulse_reader;
GRANT SELECT ON TABLE bronze.inventory_counts  TO datapulse_reader;
GRANT SELECT ON TABLE public.reorder_config    TO datapulse_reader;
GRANT SELECT ON TABLE bronze.batches           TO datapulse_reader;
GRANT SELECT ON TABLE bronze.suppliers         TO datapulse_reader;
GRANT SELECT ON TABLE bronze.purchase_orders   TO datapulse_reader;
GRANT SELECT ON TABLE bronze.po_lines          TO datapulse_reader;
GRANT SELECT ON TABLE bronze.pos_transactions  TO datapulse_reader;
