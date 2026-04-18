-- Migration: 078 — Link pos.transactions to shifts + add commit_confirmed_at
-- Layer: POS operational
-- Idempotent.
--
-- Two additive columns on pos.transactions:
-- * shift_id            — explicit FK to pos.shift_records(id) used by the
--                         server-side shift-close guard to query "any rows
--                         under this shift where commit_confirmed_at IS NULL?"
-- * commit_confirmed_at — timestamp when the transaction reached final
--                         committed state (set atomically by the new
--                         POST /pos/transactions/commit endpoint).
-- Design ref: §3.6 + §4.2.

ALTER TABLE pos.transactions
    ADD COLUMN IF NOT EXISTS shift_id            BIGINT REFERENCES pos.shift_records(id);

ALTER TABLE pos.transactions
    ADD COLUMN IF NOT EXISTS commit_confirmed_at TIMESTAMPTZ;

-- Back-fill shift_id: join through shift_records on same terminal where the
-- transaction's created_at falls inside the shift's opened_at..closed_at window.
UPDATE pos.transactions t
   SET shift_id = sr.id
  FROM pos.shift_records sr
 WHERE t.shift_id IS NULL
   AND sr.terminal_id = t.terminal_id
   AND sr.opened_at  <= t.created_at
   AND (sr.closed_at IS NULL OR sr.closed_at >= t.created_at);

-- Back-fill commit_confirmed_at for already-final rows
UPDATE pos.transactions
   SET commit_confirmed_at = COALESCE(commit_confirmed_at, created_at)
 WHERE status IN ('completed', 'voided', 'returned')
   AND commit_confirmed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pos_txn_shift
    ON pos.transactions (shift_id, terminal_id);

-- Partial index powering the shift-close server-side guard
CREATE INDEX IF NOT EXISTS idx_pos_txn_incomplete
    ON pos.transactions (shift_id, terminal_id)
    WHERE commit_confirmed_at IS NULL;

COMMENT ON COLUMN pos.transactions.shift_id IS
  'Link to pos.shift_records(id). Set atomically at commit time; back-filled for legacy rows via time-window join.';
COMMENT ON COLUMN pos.transactions.commit_confirmed_at IS
  'Timestamp when the transaction reached final committed state. NULL while draft/in-flight. Queried by shift-close guard.';
