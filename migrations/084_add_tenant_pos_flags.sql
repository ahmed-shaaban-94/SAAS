-- Migration: 084 — Tenant POS multi-terminal flags
-- Layer: tenants (bronze)
-- Idempotent.
--
-- Phase 1 POS is restricted to single-terminal sites (§1.4). Multi-till
-- pharmacies are out of scope until F1 — the server-side guard in
-- POST /pos/terminals rejects a second concurrent terminal when
-- pos_max_terminals = 1 (the default).

ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS pos_multi_terminal_allowed BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS pos_max_terminals INT NOT NULL DEFAULT 1;

COMMENT ON COLUMN bronze.tenants.pos_multi_terminal_allowed IS
  'Phase 1 POS is restricted to single-terminal sites. Flip to true only after F1 multi-terminal coordination ships.';
COMMENT ON COLUMN bronze.tenants.pos_max_terminals IS
  'Hard cap on concurrent active POS terminals per tenant. Default 1.';
