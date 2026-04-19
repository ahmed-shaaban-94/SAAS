-- Migration: 093 — POS device fingerprint v2 + v1 deprecation window
-- Layer: POS operational
-- Idempotent.
--
-- Issue: #480 (epic #479). The v1 fingerprint `sha256:<hex>` was computed
-- from `hostname + random deviceUuid`; the UUID lived in the SQLite DB on
-- the terminal. A full OS reinstall wiped the DB → new UUID → the same
-- physical machine looked brand-new to the server, defeating the "one
-- physical machine per terminal" guarantee.
--
-- v2 augments the digest with OS-level identifiers that survive a reimage
-- on the same hardware (Windows MachineGuid, macOS IOPlatformUUID, Linux
-- `/etc/machine-id`) plus the first non-virtual MAC. Format:
--     sha256v2:<hex>
--
-- Rollout strategy:
--   * NEW columns are nullable so old pilots (v1-only clients) keep working.
--   * Clients now send BOTH `X-Device-Fingerprint` (v1) and
--     `X-Device-Fingerprint-V2` (v2) on every request.
--   * Server accepts either header until the deprecation window closes.
--   * Per-tenant `pos_fingerprint_v1_deprecated_at` controls when v1 is
--     rejected. NULL = still accepted. Set to a past UTC timestamp to
--     flip a tenant into v2-only mode; admins get a month of overlap.

-- ── pos.terminal_devices ───────────────────────────────────────────────────
ALTER TABLE pos.terminal_devices
    ADD COLUMN IF NOT EXISTS device_fingerprint_v2 TEXT;

COMMENT ON COLUMN pos.terminal_devices.device_fingerprint_v2 IS
  'v2 fingerprint (sha256v2:<hex>) built from OS machine-id + MAC + hostname. '
  'NULL for devices registered before v2 rolled out. New registrations populate both.';

-- A non-unique index so the verifier can look up by v2 alone during the
-- deprecation window (an admin reimaged a box, v1 changed but v2 stayed
-- the same → we can still reconcile to the old row).
CREATE INDEX IF NOT EXISTS idx_pos_device_fingerprint_v2
    ON pos.terminal_devices (device_fingerprint_v2)
    WHERE device_fingerprint_v2 IS NOT NULL AND revoked_at IS NULL;

-- ── bronze.tenants — per-tenant v1 deprecation switch ──────────────────────
ALTER TABLE bronze.tenants
    ADD COLUMN IF NOT EXISTS pos_fingerprint_v1_deprecated_at TIMESTAMPTZ;

COMMENT ON COLUMN bronze.tenants.pos_fingerprint_v1_deprecated_at IS
  'Deprecation cut-off for POS device fingerprint v1. NULL = v1 still accepted. '
  'Set to a past timestamp to reject requests that only present the v1 header. '
  'Operators give tenants ~30 days of overlap between v2 rollout and v1 sunset.';
