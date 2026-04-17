-- Migration: 049 – AI invocation tracking for cost & observability
-- Layer: infrastructure
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.ai_invocations (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     INT NOT NULL DEFAULT 1,
    run_id        UUID NOT NULL,
    insight_type  TEXT NOT NULL,           -- summary | anomalies | changes | deep_dive
    model         TEXT NOT NULL DEFAULT '',
    input_tokens  INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    cost_cents    NUMERIC(10,4) NOT NULL DEFAULT 0,
    duration_ms   INT NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'success'
                  CHECK (status IN ('success', 'degraded', 'error')),
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_invocations_tenant   ON public.ai_invocations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_invocations_created  ON public.ai_invocations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_invocations_run      ON public.ai_invocations(run_id);
CREATE INDEX IF NOT EXISTS idx_ai_invocations_type     ON public.ai_invocations(tenant_id, insight_type, created_at DESC);

ALTER TABLE public.ai_invocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_invocations FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_ai_invocations ON public.ai_invocations;
CREATE POLICY tenant_isolation_ai_invocations ON public.ai_invocations
    USING (tenant_id = current_setting('app.tenant_id', true)::INT);

COMMENT ON TABLE public.ai_invocations IS
  'Tracks each AI/LLM invocation for cost monitoring and observability. RLS-protected.';
