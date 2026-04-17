-- Migration: 073 — Additional composite indexes for POS query performance
-- Layer: POS operational
-- Idempotent.
-- Note: Primary indexes are created inline in 065-071b migrations.
--       This migration adds supplementary covering/composite indexes identified
--       as needed for the transaction history and shift reconciliation queries.

-- Covering index for the transaction history list query (tenant + date + status)
CREATE INDEX IF NOT EXISTS idx_pos_txn_history_cover
    ON pos.transactions (tenant_id, created_at DESC, status, grand_total, payment_method);

-- Partial index: active (non-voided, non-returned) transactions per terminal
CREATE INDEX IF NOT EXISTS idx_pos_txn_terminal_active
    ON pos.transactions (terminal_id, created_at DESC)
    WHERE status IN ('draft', 'completed');

-- Controlled-substance item lookup (for pharmacist audit reports)
CREATE INDEX IF NOT EXISTS idx_pos_items_controlled
    ON pos.transaction_items (tenant_id, pharmacist_id, loaded_at DESC)
    WHERE is_controlled = true;

-- Returns lookup by staff and date range
CREATE INDEX IF NOT EXISTS idx_pos_returns_staff
    ON pos.returns (tenant_id, staff_id, created_at DESC);

-- Shift reconciliation: find open shifts quickly
CREATE INDEX IF NOT EXISTS idx_pos_shifts_open
    ON pos.shift_records (terminal_id)
    WHERE closed_at IS NULL;

-- COMMENT ON INDEX requires schema-qualified names because the ``pos`` schema
-- is not on the default search_path for the migration role. Without the
-- qualifier psql raises "relation does not exist".
COMMENT ON INDEX pos.idx_pos_txn_history_cover IS
    'Covering index for transaction list endpoint — avoids table heap fetch for common columns.';
COMMENT ON INDEX pos.idx_pos_items_controlled IS
    'Partial index for controlled-substance audit queries — only indexes rows where is_controlled=true.';
