"""Market Basket Analysis — learn cross-sell rules from completed POS transactions.

Algorithm (pair-wise association rules, no external API):
  1. Pull all completed basket items for the tenant from pos.transaction_items.
  2. Self-join on transaction_id to get every (A, B) drug pair per basket.
  3. Compute support_count = |baskets(A ∩ B)| and confidence = support / |baskets(A)|.
  4. Keep pairs that clear MIN_SUPPORT and MIN_CONFIDENCE.
  5. UPSERT into pos.cross_sell_rules (source='learned'), overwriting previous
     learned entries but leaving manual ones untouched.

Tunable constants (no external calls, no LLM):
  MIN_SUPPORT    — minimum basket co-occurrence count (absolute)
  MIN_CONFIDENCE — minimum P(B|A) [0-1]
  TOP_N_PER_DRUG — cap suggestions per primary drug

Everything runs in one SQL round-trip; Polars is only used if you want
to post-process outside SQL (e.g. for unit tests with in-memory data).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)

MIN_SUPPORT: int = 3  # at least 3 baskets must contain both drugs
MIN_CONFIDENCE: float = 0.05  # P(B|A) ≥ 5 %
TOP_N_PER_DRUG: int = 5  # keep at most 5 suggestions per primary drug


@dataclass(frozen=True)
class MBARule:
    primary_drug_code: str
    suggested_drug_code: str
    support_count: int
    confidence: float


# ── SQL ───────────────────────────────────────────────────────────────────────

_MINE_SQL = sa_text("""
WITH baskets AS (
    -- one row per (transaction, drug) for completed sales
    SELECT DISTINCT
        ti.transaction_id,
        ti.drug_code
    FROM   pos.transaction_items ti
    JOIN   pos.transactions      t  ON t.id = ti.transaction_id
    WHERE  t.tenant_id = :tenant_id
    AND    t.status    = 'completed'
    -- only look at the last N days to keep it fresh
    AND    t.created_at >= now() - (:lookback_days || ' days')::interval
),
basket_sizes AS (
    SELECT drug_code, COUNT(DISTINCT transaction_id) AS basket_count
    FROM   baskets
    GROUP  BY drug_code
),
pairs AS (
    SELECT
        a.drug_code                          AS primary_drug_code,
        b.drug_code                          AS suggested_drug_code,
        COUNT(DISTINCT a.transaction_id)     AS support_count
    FROM   baskets a
    JOIN   baskets b ON b.transaction_id = a.transaction_id
                    AND b.drug_code      <> a.drug_code
    GROUP  BY a.drug_code, b.drug_code
    HAVING COUNT(DISTINCT a.transaction_id) >= :min_support
),
ranked AS (
    SELECT
        p.primary_drug_code,
        p.suggested_drug_code,
        p.support_count,
        ROUND(p.support_count::numeric / bs.basket_count, 4) AS confidence,
        ROW_NUMBER() OVER (
            PARTITION BY p.primary_drug_code
            ORDER BY p.support_count DESC, p.suggested_drug_code
        ) AS rn
    FROM   pairs     p
    JOIN   basket_sizes bs ON bs.drug_code = p.primary_drug_code
    WHERE  ROUND(p.support_count::numeric / bs.basket_count, 4) >= :min_confidence
)
SELECT primary_drug_code, suggested_drug_code, support_count, confidence
FROM   ranked
WHERE  rn <= :top_n
ORDER  BY primary_drug_code, confidence DESC
""")

_UPSERT_SQL = sa_text("""
INSERT INTO pos.cross_sell_rules
    (tenant_id, primary_drug_code, suggested_drug_code,
     reason, reason_tag, source, confidence, support_count, updated_at)
VALUES
    (:tenant_id, :primary, :suggested,
     :reason, 'FREQ', 'learned', :confidence, :support_count, now())
ON CONFLICT (tenant_id, primary_drug_code, suggested_drug_code)
DO UPDATE SET
    confidence    = EXCLUDED.confidence,
    support_count = EXCLUDED.support_count,
    reason        = EXCLUDED.reason,
    reason_tag    = EXCLUDED.reason_tag,
    source        = 'learned',
    updated_at    = now()
WHERE pos.cross_sell_rules.source = 'learned'   -- never overwrite manual rules
""")

_DELETE_STALE_SQL = sa_text("""
DELETE FROM pos.cross_sell_rules
WHERE  tenant_id = :tenant_id
AND    source    = 'learned'
AND    updated_at < now() - interval '14 days'
""")


# ── Public API ────────────────────────────────────────────────────────────────


def run_mba(
    session: Session,
    tenant_id: int,
    *,
    lookback_days: int = 90,
    min_support: int = MIN_SUPPORT,
    min_confidence: float = MIN_CONFIDENCE,
    top_n: int = TOP_N_PER_DRUG,
) -> dict[str, int]:
    """Mine rules and upsert into pos.cross_sell_rules.

    Returns a dict with keys: rules_found, rules_upserted, stale_deleted.
    """
    session.execute(sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

    rows = session.execute(
        _MINE_SQL,
        {
            "tenant_id": tenant_id,
            "lookback_days": lookback_days,
            "min_support": min_support,
            "min_confidence": min_confidence,
            "top_n": top_n,
        },
    ).fetchall()

    rules_found = len(rows)
    rules_upserted = 0

    for row in rows:
        primary, suggested, support_count, confidence = (
            row.primary_drug_code,
            row.suggested_drug_code,
            int(row.support_count),
            float(row.confidence),
        )
        pct = int(round(confidence * 100))
        reason = f"نُوصي به في {pct}٪ من فواتير {primary}"

        session.execute(
            _UPSERT_SQL,
            {
                "tenant_id": tenant_id,
                "primary": primary,
                "suggested": suggested,
                "reason": reason,
                "confidence": confidence,
                "support_count": support_count,
            },
        )
        rules_upserted += 1

    # Remove learned rules that haven't been seen for 14 days
    stale_result = session.execute(_DELETE_STALE_SQL, {"tenant_id": tenant_id})
    stale_deleted: int = getattr(stale_result, "rowcount", 0) or 0

    session.commit()

    log.info(
        "mba_complete",
        tenant_id=tenant_id,
        rules_found=rules_found,
        rules_upserted=rules_upserted,
        stale_deleted=stale_deleted,
    )
    return {
        "rules_found": rules_found,
        "rules_upserted": rules_upserted,
        "stale_deleted": stale_deleted,
    }
