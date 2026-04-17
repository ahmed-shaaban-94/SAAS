-- Migration: 044 — Control Center: pipeline_drafts + pipeline_releases
-- Layer: application / control_center
-- Phase: Control Center Phase 1a (Foundation)
--
-- Run order: after 043_control_center_mappings.sql
-- Idempotent: safe to run multiple times
--
-- What this does:
--   1. Creates pipeline_drafts — in-progress edits with optimistic locking
--      and an explicit state machine enforced via CHECK.
--   2. Creates pipeline_releases — append-only snapshots of published configs.
--      Rollback creates release N+1 whose snapshot == target release's
--      snapshot. We NEVER delete or mutate released rows.
--
-- Design notes:
--   - draft status enum: enforced at the DB layer, not the service layer.
--   - release_version is strictly monotonic per tenant (UNIQUE constraint).
--   - snapshot_json holds full {source_connection, profile, mapping_template}
--     at publish time — Power BI & dashboards read the effective release.

-- ============================================================
-- 1. Pipeline drafts (mutable until published)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pipeline_drafts (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id               INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    entity_type             VARCHAR(50) NOT NULL,
    entity_id               BIGINT,
    draft_json              JSONB NOT NULL DEFAULT '{}'::jsonb,
    status                  VARCHAR(30) NOT NULL DEFAULT 'draft',
    validation_report_json  JSONB,
    preview_result_json     JSONB,
    version                 INT NOT NULL DEFAULT 0,
    created_by              TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_pipeline_drafts_status CHECK (status IN (
        'draft',
        'validating',
        'validated',
        'previewing',
        'previewed',
        'publishing',
        'published',
        'invalidated',
        'preview_failed',
        'publish_failed'
    )),
    CONSTRAINT chk_pipeline_drafts_entity_type CHECK (entity_type IN (
        'source_connection', 'pipeline_profile', 'mapping_template', 'bundle'
    ))
);

CREATE INDEX IF NOT EXISTS idx_pipeline_drafts_tenant_status
    ON public.pipeline_drafts (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_pipeline_drafts_entity
    ON public.pipeline_drafts (tenant_id, entity_type, entity_id);

DROP TRIGGER IF EXISTS trg_pipeline_drafts_updated_at ON public.pipeline_drafts;
CREATE TRIGGER trg_pipeline_drafts_updated_at
    BEFORE UPDATE ON public.pipeline_drafts
    FOR EACH ROW EXECUTE FUNCTION public.control_center_set_updated_at();

ALTER TABLE public.pipeline_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_drafts FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.pipeline_drafts
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_write ON public.pipeline_drafts
        FOR ALL TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.pipeline_drafts TO datapulse_reader;

COMMENT ON TABLE public.pipeline_drafts IS
    'Control Center: mutable drafts of source/profile/mapping edits. '
    'Status enforces the state machine draft→validating→validated→'
    'previewing→previewed→publishing→published (+ failed branches). '
    'version column supports optimistic locking on PATCH.';

-- ============================================================
-- 2. Pipeline releases (append-only, immutable snapshots)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pipeline_releases (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id         INT NOT NULL REFERENCES bronze.tenants(tenant_id) ON DELETE CASCADE,
    release_version   INT NOT NULL,
    draft_id          BIGINT REFERENCES public.pipeline_drafts(id) ON DELETE SET NULL,
    source_release_id BIGINT REFERENCES public.pipeline_releases(id),  -- set on rollback
    snapshot_json     JSONB NOT NULL,
    release_notes     TEXT NOT NULL DEFAULT '',
    is_rollback       BOOLEAN NOT NULL DEFAULT FALSE,
    published_by      TEXT,
    published_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_pipeline_releases_tenant_version UNIQUE (tenant_id, release_version)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_releases_tenant_latest
    ON public.pipeline_releases (tenant_id, release_version DESC);

ALTER TABLE public.pipeline_releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_releases FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.pipeline_releases
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- SELECT-only for datapulse_reader — releases are append-only. Inserts go
-- through the datapulse superuser role via the service layer.
DO $$ BEGIN
    CREATE POLICY reader_select ON public.pipeline_releases
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_insert ON public.pipeline_releases
        FOR INSERT TO datapulse_reader
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- NO UPDATE / DELETE policies — releases are immutable by policy.
GRANT SELECT, INSERT ON TABLE public.pipeline_releases TO datapulse_reader;

COMMENT ON TABLE public.pipeline_releases IS
    'Control Center: append-only snapshots of published config bundles. '
    'Rollback creates a NEW release with source_release_id pointing at the '
    'target and is_rollback=true. Never UPDATE or DELETE rows here.';
