-- Migration 008: Create audit_log table for API request tracking
-- Tracks who accessed what data and triggered which operations

BEGIN;

INSERT INTO public.schema_migrations (filename)
VALUES ('008_create_audit_log.sql')
ON CONFLICT (filename) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.audit_log (
    id BIGSERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    request_params JSONB DEFAULT '{}',
    response_status INT,
    duration_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON public.audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON public.audit_log (action);

COMMIT;
