"""Token → cost mapping and invocation tracking for AI-Light graph.

Cost values are approximate (in USD cents per 1k tokens) and updated manually.
Rounds up to nearest 0.0001 cent for precision without float weirdness.
"""

from __future__ import annotations

from decimal import ROUND_UP, Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)

# Cost in USD cents per 1,000 tokens (input / output)
# Source: openrouter.ai pricing as of 2026-04
_COST_TABLE: dict[str, tuple[float, float]] = {
    "openai/gpt-4o-mini": (0.015, 0.060),  # 0.015 / 0.060 per 1k
    "openai/gpt-4o": (0.25, 0.75),
    "anthropic/claude-3.5-haiku": (0.025, 0.125),
    "anthropic/claude-3.5-sonnet": (0.15, 0.75),
    "openrouter/free": (0.0, 0.0),
}
_DEFAULT_COST = (0.05, 0.15)  # conservative fallback for unknown models


def estimate_cost_cents(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Return cost estimate in USD cents (Decimal for DB storage)."""
    in_rate, out_rate = _COST_TABLE.get(model, _DEFAULT_COST)
    raw = (input_tokens * in_rate + output_tokens * out_rate) / 1000
    return Decimal(str(raw)).quantize(Decimal("0.0001"), rounding=ROUND_UP)


def check_daily_cap(session: Session, tenant_id: str, max_tokens: int) -> int:
    """Return tokens used today for this tenant.  0 if ai_invocations doesn't exist yet."""
    try:
        row = session.execute(
            text(
                """
                SELECT COALESCE(SUM(input_tokens + output_tokens), 0)
                FROM   public.ai_invocations
                WHERE  tenant_id = :tid
                  AND  created_at >= current_date
                """
            ),
            {"tid": tenant_id},
        ).scalar()
        return int(row or 0)
    except Exception as exc:
        log.warning("ai_cap_check_failed", error=str(exc))
        return 0


def write_invocation_row(
    session: Session,
    *,
    tenant_id: str,
    run_id: str,
    insight_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_cents: Decimal,
    duration_ms: int,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    """Insert a row into public.ai_invocations (best-effort; never raises)."""
    try:
        session.execute(
            text(
                """
                INSERT INTO public.ai_invocations
                    (tenant_id, run_id, insight_type, model,
                     input_tokens, output_tokens, cost_cents,
                     duration_ms, status, error_message)
                VALUES
                    (:tenant_id, :run_id::uuid, :insight_type, :model,
                     :input_tokens, :output_tokens, :cost_cents,
                     :duration_ms, :status, :error_message)
                """
            ),
            {
                "tenant_id": int(tenant_id),
                "run_id": run_id,
                "insight_type": insight_type,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_cents": cost_cents,
                "duration_ms": duration_ms,
                "status": status,
                "error_message": error_message,
            },
        )
        session.commit()
    except Exception as exc:
        import contextlib

        log.warning("ai_invocation_write_failed", run_id=run_id, error=str(exc))
        with contextlib.suppress(Exception):
            session.rollback()
