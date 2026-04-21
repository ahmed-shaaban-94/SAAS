{{
    config(
        materialized='incremental',
        unique_key=['tenant_id', 'product_key', 'site_key'],
        incremental_strategy='delete+insert',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_tenant ON {{ this }} (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_product ON {{ this }} (product_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_site ON {{ this }} (site_key)",
            "CREATE INDEX IF NOT EXISTS idx_agg_stock_levels_drug_code ON {{ this }} (drug_code)"
        ]
    )
}}

-- Current stock levels per product per site.
-- Grain: one row per (tenant_id, product_key, site_key).
-- current_quantity = SUM of all movement quantities (receipts +, dispenses -,
--                    adjustments +/-, returns +).
--
-- Incremental strategy: partition refresh.
--   A naive ``incremental + merge`` is semantically wrong here because
--   current_quantity = SUM(*all* movements for the key), not SUM(new) +
--   existing. Merging new rows would double-count.
--
--   Instead, on each incremental run we:
--     1. Identify (tenant, product, site) partitions that have new movements
--        since the previous build (watermark on fct_stock_movements.loaded_at).
--     2. Re-SUM over the *full* history for those partitions only.
--     3. ``delete+insert`` replaces each affected partition atomically.
--
--   ``--full-refresh`` rebuilds every partition (no watermark).
--
-- Trade-offs:
--   - Dim-only changes (e.g. drug_name renamed) don't propagate until a
--     movement touches the partition or a scheduled ``--full-refresh`` runs.
--     Acceptable for pharma: drug names rarely change, and a nightly full
--     refresh catches drift.
--   - A retired product_key with no recent movements keeps its last-known
--     row. Historical correctness.

{% if is_incremental() %}
WITH last_build AS (
    SELECT COALESCE(MAX(last_loaded_at), '1970-01-01'::timestamptz) AS watermark
    FROM {{ this }}
),
affected_keys AS (
    SELECT DISTINCT
        tenant_id,
        product_key,
        site_key
    FROM {{ ref('fct_stock_movements') }}
    WHERE loaded_at > (SELECT watermark FROM last_build)
      AND product_key != -1
      AND site_key    != -1
)
{% else %}
WITH affected_keys AS (
    -- Full build: every partition with at least one valid movement.
    SELECT DISTINCT
        tenant_id,
        product_key,
        site_key
    FROM {{ ref('fct_stock_movements') }}
    WHERE product_key != -1
      AND site_key    != -1
)
{% endif %}

SELECT
    m.tenant_id,
    m.product_key,
    m.site_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    s.site_code,
    s.site_name,
    SUM(m.quantity)                                                                             AS current_quantity,
    SUM(CASE WHEN m.movement_type = 'receipt'
        THEN m.quantity ELSE 0 END)                                                             AS total_received,
    SUM(CASE WHEN m.movement_type = 'dispense'
        THEN ABS(m.quantity) ELSE 0 END)                                                        AS total_dispensed,
    SUM(CASE WHEN m.movement_type IN ('damage', 'shrinkage', 'write_off')
        THEN ABS(m.quantity) ELSE 0 END)                                                        AS total_wastage,
    MAX(m.movement_date)                                                                        AS last_movement_date,
    -- Watermark for the next incremental run. Must be MAX(loaded_at), NOT
    -- MAX(movement_date) — a late-arriving movement for an old date would be
    -- invisible if we watermarked on movement_date.
    MAX(m.loaded_at)                                                                            AS last_loaded_at

FROM {{ ref('fct_stock_movements') }} m
INNER JOIN affected_keys ak
    ON m.tenant_id   = ak.tenant_id
   AND m.product_key = ak.product_key
   AND m.site_key    = ak.site_key
INNER JOIN {{ ref('dim_product') }} p ON m.product_key = p.product_key AND m.tenant_id = p.tenant_id
INNER JOIN {{ ref('dim_site') }}    s ON m.site_key    = s.site_key    AND m.tenant_id = s.tenant_id
WHERE m.product_key != -1
  AND m.site_key    != -1

GROUP BY
    m.tenant_id,
    m.product_key,
    m.site_key,
    p.drug_code,
    p.drug_name,
    p.drug_brand,
    s.site_code,
    s.site_name
