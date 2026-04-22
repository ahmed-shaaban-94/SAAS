-- Migration: 109 — rx schema, prescriptions, prescription items, dispense events
-- Layer: rx (new schema)
-- Idempotent.
--
-- Creates:
--   1. rx schema
--   2. rx.prescriptions       — prescription headers
--   3. rx.prescription_items  — drug line items per prescription
--   4. rx.dispense_events     — dispensing audit trail
--   RLS on all tables

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Schema
-- ─────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS rx;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. rx.prescriptions
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rx.prescriptions (
    id              BIGSERIAL   PRIMARY KEY,
    tenant_id       BIGINT      NOT NULL,
    patient_name    TEXT,
    patient_dob     DATE,
    doctor_name     TEXT,
    doctor_license  TEXT,
    issue_date      DATE        NOT NULL,
    expiry_date     DATE,
    refills_total   SMALLINT    NOT NULL DEFAULT 1,
    refills_used    SMALLINT    NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prescriptions_tenant_id -- migration-safety: ok
    ON rx.prescriptions (tenant_id);

CREATE INDEX IF NOT EXISTS idx_prescriptions_issue_date -- migration-safety: ok
    ON rx.prescriptions (tenant_id, issue_date);

COMMENT ON TABLE rx.prescriptions IS
    'Prescription headers. refills_used must not exceed refills_total (enforced at service layer). '
    'Added in migration 109.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. rx.prescription_items
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rx.prescription_items (
    id               BIGSERIAL       PRIMARY KEY,
    prescription_id  BIGINT          NOT NULL REFERENCES rx.prescriptions(id) ON DELETE CASCADE,
    drug_code        TEXT            NOT NULL,
    quantity         NUMERIC(10,3),
    instructions     TEXT
);

CREATE INDEX IF NOT EXISTS idx_prescription_items_prescription_id -- migration-safety: ok
    ON rx.prescription_items (prescription_id);

COMMENT ON TABLE rx.prescription_items IS
    'Drug line items for a prescription. Cascades on prescription deletion. Added in migration 109.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. rx.dispense_events
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rx.dispense_events (
    id               BIGSERIAL   PRIMARY KEY,
    prescription_id  BIGINT      NOT NULL REFERENCES rx.prescriptions(id),
    transaction_id   BIGINT,
    dispensed_by     TEXT,
    dispensed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_dispense_events_prescription_id -- migration-safety: ok
    ON rx.dispense_events (prescription_id);

COMMENT ON TABLE rx.dispense_events IS
    'Audit log of each dispensing event against a prescription. Added in migration 109.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. RLS
-- ─────────────────────────────────────────────────────────────────────────────

-- rx.prescriptions
ALTER TABLE rx.prescriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rx.prescriptions FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON rx.prescriptions
        USING (tenant_id = current_setting('app.tenant_id', true)::bigint);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- rx.prescription_items (joined via prescription_id → tenant-scoped parent)
ALTER TABLE rx.prescription_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE rx.prescription_items FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON rx.prescription_items
        USING (
            EXISTS (
                SELECT 1
                  FROM rx.prescriptions p
                 WHERE p.id = prescription_id
                   AND p.tenant_id = current_setting('app.tenant_id', true)::bigint
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- rx.dispense_events (joined via prescription_id → tenant-scoped parent)
ALTER TABLE rx.dispense_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE rx.dispense_events FORCE  ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY tenant_isolation ON rx.dispense_events
        USING (
            EXISTS (
                SELECT 1
                  FROM rx.prescriptions p
                 WHERE p.id = prescription_id
                   AND p.tenant_id = current_setting('app.tenant_id', true)::bigint
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Grants (guarded — role may not exist in all environments)
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'datapulse_api') THEN
        GRANT SELECT, INSERT, UPDATE ON TABLE rx.prescriptions                 TO datapulse_api;
        GRANT SELECT, INSERT, UPDATE ON TABLE rx.prescription_items            TO datapulse_api;
        GRANT SELECT, INSERT, UPDATE ON TABLE rx.dispense_events               TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE rx.prescriptions_id_seq               TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE rx.prescription_items_id_seq          TO datapulse_api;
        GRANT USAGE, SELECT ON SEQUENCE rx.dispense_events_id_seq             TO datapulse_api;
    END IF;
END $$;
