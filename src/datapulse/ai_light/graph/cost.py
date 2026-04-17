"""Cost tracking — writes one row to public.ai_invocations per graph invocation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from datapulse.ai_light.graph.state import AILightState

log = get_logger(__name__)

# Cost per 1M input tokens (cents). Extend as new models are added.
_INPUT_COST_PER_1M: dict[str, float] = {
    "openai/gpt-4o-mini": 15.0,
    "openai/gpt-4o": 250.0,
    "anthropic/claude-3.5-haiku": 80.0,
    "anthropic/claude-3.5-sonnet": 300.0,
    "openrouter/free": 0.0,
}
_OUTPUT_COST_PER_1M: dict[str, float] = {
    "openai/gpt-4o-mini": 60.0,
    "openai/gpt-4o": 1000.0,
    "anthropic/claude-3.5-haiku": 400.0,
    "anthropic/claude-3.5-sonnet": 1500.0,
    "openrouter/free": 0.0,
}


def compute_cost_cents(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in US cents for a given model and token counts."""
    in_rate = _INPUT_COST_PER_1M.get(model, 0.0)
    out_rate = _OUTPUT_COST_PER_1M.get(model, 0.0)
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


def write_invocation_row(session: Session, state: AILightState) -> None:
    """Insert one row into public.ai_invocations.

    Non-fatal — callers must catch exceptions.
    """
    run_id = state.get("run_id") or str(uuid.uuid4())
    insight_type = state.get("insight_type", "summary")
    model = state.get("model_used") or ""
    usage = state.get("token_usage") or {}
    input_tokens = usage.get("input", 0)
    output_tokens = usage.get("output", 0)
    degraded = state.get("degraded", False)
    errors = state.get("errors") or []
    tenant_id = state.get("tenant_id", "1")

    # Coerce tenant_id to int (RLS policy expects INT)
    try:
        tenant_id_int = int(tenant_id)
    except (ValueError, TypeError):
        tenant_id_int = 1

    cost_cents = compute_cost_cents(model, input_tokens, output_tokens)

    step_trace = state.get("step_trace") or []
    # Estimate duration from first and last trace timestamps
    duration_ms = 0
    if len(step_trace) >= 2:
        try:
            from datetime import datetime

            t0 = datetime.fromisoformat(step_trace[0]["ts"])
            t1 = datetime.fromisoformat(step_trace[-1]["ts"])
            duration_ms = int((t1 - t0).total_seconds() * 1000)
        except Exception:
            pass

    if errors and not degraded:
        status = "error"
    elif degraded:
        status = "degraded"
    else:
        status = "success"

    error_message: str | None = "; ".join(str(e) for e in errors) if errors else None

    stmt = text("""
        INSERT INTO public.ai_invocations
            (tenant_id, run_id, insight_type, model,
             input_tokens, output_tokens, cost_cents,
             duration_ms, status, error_message)
        VALUES
            (:tenant_id, :run_id::uuid, :insight_type, :model,
             :input_tokens, :output_tokens, :cost_cents,
             :duration_ms, :status, :error_message)
    """)

    session.execute(
        stmt,
        {
            "tenant_id": tenant_id_int,
            "run_id": run_id,
            "insight_type": insight_type,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_cents": round(cost_cents, 4),
            "duration_ms": duration_ms,
            "status": status,
            "error_message": error_message,
        },
    )
    session.commit()
    log.info(
        "ai_invocation_recorded",
        run_id=run_id,
        model=model,
        tokens=input_tokens + output_tokens,
        cost_cents=cost_cents,
        status=status,
    )
