"""Token-to-cost mapping, daily cap checker, and invocation persistence for AI-Light.

Responsibilities
----------------
``TOKEN_COST_MAP``         — Per-model cost in USD per 1 000 tokens (input / output).
``estimate_cost_cents``    — Convert token counts to fractional cents using the map.
``check_daily_cap``        — Return True if the tenant (or global) daily token budget
                             is already exhausted; the ``cost_track`` node calls this
                             before writing and the graph short-circuits to ``fallback``.
``write_invocation_row``   — Insert one row into ``public.ai_invocations`` as a
                             fire-and-forget side effect of the ``cost_track`` node.

Implementation note (Phase A-1): ``TOKEN_COST_MAP`` is pre-populated with a
representative subset of OpenRouter models.  ``estimate_cost_cents``,
``check_daily_cap``, and ``write_invocation_row`` are stubs — implemented in
Phase A when the ``cost_track`` node is wired.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Per-model cost map (USD per 1 000 tokens, input / output)
# Source: OpenRouter pricing as of 2026-04.  Update as models change.
# ---------------------------------------------------------------------------

TOKEN_COST_MAP: dict[str, dict[str, float]] = {
    # OpenAI-compatible via OpenRouter
    "openai/gpt-4o-mini": {"input": 0.000150, "output": 0.000600},
    "openai/gpt-4o": {"input": 0.002500, "output": 0.010000},
    # Anthropic via OpenRouter
    "anthropic/claude-3.5-haiku": {"input": 0.000250, "output": 0.001250},
    "anthropic/claude-3.5-sonnet": {"input": 0.003000, "output": 0.015000},
    # Free / default tier (cost is effectively $0 but we still track tokens)
    "openrouter/free": {"input": 0.0, "output": 0.0},
}

# Fallback pricing for unknown models — conservative estimate.
_UNKNOWN_MODEL_COST: dict[str, float] = {"input": 0.001000, "output": 0.005000}


def estimate_cost_cents(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the estimated cost in fractional cents for a single LLM call.

    Parameters
    ----------
    model:
        OpenRouter model identifier (e.g. ``"openai/gpt-4o-mini"``).
    input_tokens:
        Number of prompt tokens consumed.
    output_tokens:
        Number of completion tokens generated.

    Returns
    -------
    float
        Cost in cents (USD × 100).  Returns 0.0 for models with zero-cost pricing.
    """
    raise NotImplementedError("estimate_cost_cents — Phase A")


def check_daily_cap(session: Any, settings: Any, tenant_id: int) -> bool:  # noqa: ARG001
    """Return True if the daily token budget is exhausted for *tenant_id*.

    Queries ``public.ai_invocations`` for the sum of
    ``input_tokens + output_tokens`` since midnight UTC.  Compares against
    ``settings.ai_light_max_tokens_per_day``.

    Implementation note: Phase A implements this.  Returns False (cap not
    reached) until then so the stub does not block any requests.
    """
    return False  # Placeholder — never blocks in Phase A-1


def write_invocation_row(
    session: Any,
    *,
    tenant_id: int,
    run_id: str,
    insight_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_cents: float,
    duration_ms: int,
    status: str,
    error_message: str | None = None,
) -> None:
    """Insert one row into ``public.ai_invocations``.

    Called as a fire-and-forget side effect from the ``cost_track`` node.
    Errors are logged but not re-raised (observability must not block the
    API response).

    Implementation note (Phase A-1): no-op stub.  Phase A implements the
    ``INSERT`` using raw SQL via ``session.execute(text(...), {...})``.
    """
    return  # Placeholder — no-op in Phase A-1
