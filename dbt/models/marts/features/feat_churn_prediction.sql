{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_feat_churn_risk ON {{ this }} (tenant_id, risk_level)",
            "CREATE INDEX IF NOT EXISTS idx_feat_churn_probability ON {{ this }} (tenant_id, churn_probability DESC)"
        ]
    )
}}

-- Customer churn prediction
-- Uses signals from feat_customer_health + feat_customer_segments
-- Logistic-style formula to compute churn probability

WITH health AS (
    SELECT
        tenant_id,
        customer_key,
        health_score,
        health_band,
        recency_days,
        frequency_3m,
        monetary_3m,
        trend
    FROM {{ ref('feat_customer_health') }}
),

segments AS (
    SELECT
        tenant_id,
        customer_key,
        customer_name,
        rfm_segment,
        r_score,
        f_score,
        m_score,
        lifetime_days
    FROM {{ ref('feat_customer_segments') }}
),

combined AS (
    SELECT
        h.tenant_id,
        h.customer_key,
        s.customer_name,
        h.health_score,
        h.health_band,
        h.recency_days,
        h.frequency_3m,
        h.monetary_3m,
        h.trend,
        s.rfm_segment,
        s.lifetime_days,
        -- Normalize signals for the logistic function (0-1 scale)
        LEAST(h.recency_days::NUMERIC / 365, 1.0) AS recency_norm,
        CASE WHEN h.frequency_3m > 0 THEN 1.0 / h.frequency_3m ELSE 1.0 END AS freq_inv,
        CASE h.trend
            WHEN 'declining' THEN 1.0
            WHEN 'stable' THEN 0.3
            WHEN 'improving' THEN 0.0
            ELSE 0.5
        END AS trend_flag,
        (100 - h.health_score)::NUMERIC / 100 AS health_inv
    FROM health h
    JOIN segments s ON h.tenant_id = s.tenant_id AND h.customer_key = s.customer_key
)

SELECT
    tenant_id,
    customer_key,
    customer_name,
    health_score,
    health_band,
    recency_days,
    frequency_3m,
    monetary_3m,
    trend,
    rfm_segment,
    lifetime_days,
    -- Logistic churn probability: higher = more likely to churn
    ROUND(
        1.0 / (1.0 + EXP(-(
            2.0 * recency_norm
            + 1.5 * freq_inv
            + 1.0 * trend_flag
            + 1.5 * health_inv
            - 3.0
        ))),
        4
    ) AS churn_probability,
    CASE
        WHEN 1.0 / (1.0 + EXP(-(2.0 * recency_norm + 1.5 * freq_inv + 1.0 * trend_flag + 1.5 * health_inv - 3.0))) >= 0.7
            THEN 'high'
        WHEN 1.0 / (1.0 + EXP(-(2.0 * recency_norm + 1.5 * freq_inv + 1.0 * trend_flag + 1.5 * health_inv - 3.0))) >= 0.4
            THEN 'medium'
        ELSE 'low'
    END AS risk_level
FROM combined
