-- Migration 013: Create anomaly_alerts table for anomaly detection pipeline.
-- Stores detected anomalies with severity, suppression, and acknowledgement tracking.

CREATE TABLE IF NOT EXISTS public.anomaly_alerts (
    id              SERIAL PRIMARY KEY,
    tenant_id       INT NOT NULL REFERENCES bronze.tenants(tenant_id),
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    metric          VARCHAR(100) NOT NULL,
    period          DATE NOT NULL,
    actual_value    NUMERIC(18,4) NOT NULL,
    expected_value  NUMERIC(18,4) NOT NULL,
    lower_bound     NUMERIC(18,4) NOT NULL,
    upper_bound     NUMERIC(18,4) NOT NULL,
    z_score         NUMERIC(8,4),
    severity        VARCHAR(20) NOT NULL,
    direction       VARCHAR(10) NOT NULL,
    is_suppressed   BOOLEAN DEFAULT FALSE,
    suppression_reason VARCHAR(200),
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(200),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Row Level Security
DO $$ BEGIN
    ALTER TABLE public.anomaly_alerts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.anomaly_alerts FORCE ROW LEVEL SECURITY;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.anomaly_alerts FOR ALL TO datapulse
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.anomaly_alerts FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_tenant_period
    ON public.anomaly_alerts(tenant_id, period DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_severity
    ON public.anomaly_alerts(tenant_id, severity, acknowledged);

-- Note: migration tracking is handled by prestart.sh — no self-insert needed.
