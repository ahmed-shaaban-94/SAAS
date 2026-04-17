"""LangGraph node functions for the AI-Light graph (Phase A-2, summary path).

Each node receives the full AILightState and returns a dict containing only
the state keys it modifies. Nodes must NOT mutate the state dict in-place.
"""

from __future__ import annotations

import json
import statistics
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from datapulse.ai_light.graph.prompts import (
    PROMPT_VERSION,
    SUMMARY_PROMPT,
    SYSTEM_PROMPT_V2,
    _sanitize_for_prompt,
)
from datapulse.ai_light.graph.schemas import SummaryOutput
from datapulse.ai_light.graph.state import AILightState
from datapulse.cache import cache_get, cache_set, get_cache_version
from datapulse.logging import get_logger

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

log = get_logger(__name__)

# TTL constants (seconds)
_TTL_SUMMARY = 300
_TTL_ANOMALIES = 600
_TTL_CHANGES = 300
_TTL_DEEP_DIVE = 900

# OpenRouter token→cost map (cost per 1M tokens in USD, converted to cents)
_COST_PER_1M_INPUT: dict[str, float] = {
    "openai/gpt-4o-mini": 15.0,  # $0.15 / 1M input → 15 cents / 1M
    "openai/gpt-4o": 250.0,
    "anthropic/claude-3.5-haiku": 80.0,
    "anthropic/claude-3.5-sonnet": 300.0,
    "openrouter/free": 0.0,
}
_COST_PER_1M_OUTPUT: dict[str, float] = {
    "openai/gpt-4o-mini": 60.0,
    "openai/gpt-4o": 1000.0,
    "anthropic/claude-3.5-haiku": 400.0,
    "anthropic/claude-3.5-sonnet": 1500.0,
    "openrouter/free": 0.0,
}


def _cache_key(tenant_id: str, insight_type: str, params_hash: str) -> str:
    version = get_cache_version()
    return f"ai_light:{tenant_id}:{insight_type}:{params_hash}:{version}"


def _make_trace_entry(node: str, **extra: Any) -> dict[str, Any]:
    return {
        "node": node,
        "ts": datetime.now(UTC).isoformat(),
        **extra,
    }


# ---------------------------------------------------------------------------
# Node: cache_check
# ---------------------------------------------------------------------------


def cache_check(state: AILightState) -> dict[str, Any]:
    """Check Redis for a cached result. Sets cache_hit=True and pre-fills outputs if hit."""
    tenant_id = state.get("tenant_id", "0")
    insight_type = state.get("insight_type", "")
    params_hash = state.get("params_hash", "")

    key = _cache_key(tenant_id, insight_type, params_hash)
    cached = cache_get(key)

    trace = _make_trace_entry("cache_check", key=key, hit=cached is not None)

    if cached is None:
        log.info("ai_light_cache_miss", key=key)
        return {"cache_hit": False, "step_trace": [trace]}

    log.info("ai_light_cache_hit", key=key)
    return {
        "cache_hit": True,
        "narrative": cached.get("narrative"),
        "highlights": cached.get("highlights"),
        "degraded": cached.get("degraded", False),
        "step_trace": [trace],
    }


# ---------------------------------------------------------------------------
# Node: plan_summary
# ---------------------------------------------------------------------------


def plan_summary(state: AILightState) -> dict[str, Any]:
    """Record the execution plan for the summary insight type."""
    trace = _make_trace_entry(
        "plan_summary",
        plan=["get_kpi_summary", "get_top_products", "get_top_customers"],
        target_date=state.get("target_date"),
    )
    return {"step_trace": [trace]}


# ---------------------------------------------------------------------------
# Node: fetch_data  (summary path)
# ---------------------------------------------------------------------------


def fetch_data(state: AILightState, tools: list[Any]) -> dict[str, Any]:
    """Execute the data-fetching tools for the current insight type.

    For the summary path, calls get_kpi_summary, get_top_products,
    get_top_customers deterministically (no LLM tool-use loop yet).
    """
    insight_type = state.get("insight_type", "summary")
    target_date = state.get("target_date") or date.today().isoformat()

    # Build a name→tool map for easy lookup
    tool_map: dict[str, Any] = {t.name: t for t in tools}

    updates: dict[str, Any] = {}
    errors: list[str] = list(state.get("errors") or [])

    if insight_type == "summary":
        # Tool 1: KPI summary
        try:
            kpi = tool_map["get_kpi_summary"].invoke({"target_date": target_date})
            updates["kpi_data"] = kpi
        except Exception as exc:
            log.warning("fetch_kpi_failed", error=str(exc))
            errors.append(f"get_kpi_summary: {exc}")

        # Tool 3: Top products
        try:
            products = tool_map["get_top_products"].invoke({"limit": 5})
            updates["top_products"] = products
        except Exception as exc:
            log.warning("fetch_top_products_failed", error=str(exc))
            errors.append(f"get_top_products: {exc}")

        # Tool 4: Top customers
        try:
            customers = tool_map["get_top_customers"].invoke({"limit": 5})
            updates["top_customers"] = customers
        except Exception as exc:
            log.warning("fetch_top_customers_failed", error=str(exc))
            errors.append(f"get_top_customers: {exc}")

    trace = _make_trace_entry("fetch_data", insight_type=insight_type, errors=errors)
    return {**updates, "errors": errors if errors else state.get("errors"), "step_trace": [trace]}


# ---------------------------------------------------------------------------
# Node: analyze
# ---------------------------------------------------------------------------


def analyze(state: AILightState, llm: ChatOpenAI) -> dict[str, Any]:
    """Run statistical analysis + LLM narrative generation."""
    kpi = state.get("kpi_data") or {}
    products = state.get("top_products") or {}
    customers = state.get("top_customers") or {}

    # Statistical analysis
    stat: dict[str, Any] = {}
    prod_values = [float(i.get("value", 0)) for i in (products.get("items") or [])]
    cust_values = [float(i.get("value", 0)) for i in (customers.get("items") or [])]
    if prod_values:
        stat["top_product_avg"] = statistics.mean(prod_values)
        stat["top_product_std"] = statistics.stdev(prod_values) if len(prod_values) > 1 else 0.0
    if cust_values:
        stat["top_customer_avg"] = statistics.mean(cust_values)

    # Build prompt
    products_text = "\n".join(
        f"  {i.get('rank', idx + 1)}. {_sanitize_for_prompt(i.get('name', ''))}: "
        f"{float(i.get('value', 0)):,.0f} EGP ({float(i.get('pct_of_total', 0)):.1f}%)"
        for idx, i in enumerate(products.get("items") or [])
    )
    customers_text = "\n".join(
        f"  {i.get('rank', idx + 1)}. {_sanitize_for_prompt(i.get('name', ''))}: "
        f"{float(i.get('value', 0)):,.0f} EGP ({float(i.get('pct_of_total', 0)):.1f}%)"
        for idx, i in enumerate(customers.get("items") or [])
    )

    prompt_text = SUMMARY_PROMPT.format(
        prompt_version=PROMPT_VERSION,
        today_gross=f"{float(kpi.get('today_gross', 0)):,.0f}",
        mtd_gross=f"{float(kpi.get('mtd_gross', 0)):,.0f}",
        ytd_gross=f"{float(kpi.get('ytd_gross', 0)):,.0f}",
        mom_growth=f"{float(kpi.get('mom_growth_pct', 0) or 0):.1f}",
        yoy_growth=f"{float(kpi.get('yoy_growth_pct', 0) or 0):.1f}",
        daily_transactions=kpi.get("daily_transactions", 0),
        daily_customers=kpi.get("daily_customers", 0),
        top_products=products_text or "(no data)",
        top_customers=customers_text or "(no data)",
    )

    llm_raw: str | None = None
    llm_parsed: dict[str, Any] | None = None
    token_usage: dict[str, int] = {"input": 0, "output": 0, "total": 0}
    model_used: str | None = None
    errors: list[str] = list(state.get("errors") or [])

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_V2},
            {"role": "user", "content": prompt_text},
        ]
        response = llm.invoke(messages)
        llm_raw = str(response.content)

        # Extract usage metadata if available
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            token_usage = {
                "input": getattr(um, "input_tokens", 0) or 0,
                "output": getattr(um, "output_tokens", 0) or 0,
                "total": getattr(um, "total_tokens", 0) or 0,
            }
        model_used = getattr(llm, "model_name", None) or getattr(llm, "model", None)

        # Attempt JSON parse
        cleaned = llm_raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines)
        llm_parsed = json.loads(cleaned)

    except json.JSONDecodeError as exc:
        log.warning("ai_light_json_parse_failed", error=str(exc), raw=str(llm_raw)[:300])
        errors.append(f"json_parse: {exc}")
    except Exception as exc:
        log.warning("ai_light_llm_failed", error=str(exc))
        errors.append(f"llm: {exc}")

    trace = _make_trace_entry(
        "analyze",
        tokens=token_usage,
        model=model_used,
        json_ok=llm_parsed is not None,
    )
    return {
        "statistical_analysis": stat,
        "llm_raw_output": llm_raw,
        "llm_parsed_output": llm_parsed,
        "token_usage": token_usage,
        "model_used": model_used,
        "errors": errors or None,
        "step_trace": [trace],
    }


# ---------------------------------------------------------------------------
# Node: validate
# ---------------------------------------------------------------------------


def validate(state: AILightState) -> dict[str, Any]:
    """Validate LLM output against the Pydantic schema for the insight type."""
    insight_type = state.get("insight_type", "summary")
    parsed = state.get("llm_parsed_output")
    retries = state.get("validation_retries", 0)
    errors: list[str] = list(state.get("errors") or [])

    valid = False
    if parsed is not None:
        try:
            if insight_type == "summary":
                SummaryOutput(**parsed)
                valid = True
        except Exception as exc:
            log.warning("ai_light_validation_failed", error=str(exc), retries=retries)
            errors.append(f"validation: {exc}")

    trace = _make_trace_entry("validate", valid=valid, retries=retries)
    return {
        "validation_retries": retries + (0 if valid else 1),
        "errors": errors or None,
        "step_trace": [trace],
    }


# ---------------------------------------------------------------------------
# Node: synthesize
# ---------------------------------------------------------------------------


def synthesize(state: AILightState) -> dict[str, Any]:
    """Compose the final outputs from validated LLM output."""
    parsed = state.get("llm_parsed_output") or {}
    narrative = parsed.get("narrative", "")
    highlights = parsed.get("highlights", [])

    trace = _make_trace_entry("synthesize", highlights_count=len(highlights))
    return {
        "narrative": narrative,
        "highlights": highlights,
        "degraded": False,
        "step_trace": [trace],
    }


# ---------------------------------------------------------------------------
# Node: fallback
# ---------------------------------------------------------------------------


def fallback(state: AILightState) -> dict[str, Any]:
    """Generate a stats-only narrative when LLM has failed."""
    stat = state.get("statistical_analysis") or {}
    kpi = state.get("kpi_data") or {}

    parts: list[str] = []
    if kpi:
        parts.append(
            f"Today's gross sales: {float(kpi.get('today_gross', 0)):,.0f} EGP. "
            f"MTD: {float(kpi.get('mtd_gross', 0)):,.0f} EGP. "
            f"YTD: {float(kpi.get('ytd_gross', 0)):,.0f} EGP."
        )
    if stat.get("top_product_avg"):
        parts.append(f"Average revenue across top products: {stat['top_product_avg']:,.0f} EGP.")

    narrative = " ".join(parts) or "Insufficient data to generate summary."
    highlights = ["AI narrative unavailable — statistical summary shown."]

    trace = _make_trace_entry("fallback", reason="llm_failed_or_max_retries")
    return {
        "narrative": narrative,
        "highlights": highlights,
        "degraded": True,
        "step_trace": [trace],
    }


# ---------------------------------------------------------------------------
# Node: cost_track  (side-effect: writes to DB via cost.py)
# ---------------------------------------------------------------------------


def cost_track(state: AILightState, session: Any) -> dict[str, Any]:
    """Record token usage and cost in public.ai_invocations (non-fatal side effect)."""
    from datapulse.ai_light.graph.cost import write_invocation_row

    try:
        write_invocation_row(session, state)
    except Exception as exc:
        log.warning("ai_light_cost_track_failed", error=str(exc))

    trace = _make_trace_entry("cost_track")
    return {"step_trace": [trace]}


# ---------------------------------------------------------------------------
# Node: cache_write  (side-effect: writes to Redis)
# ---------------------------------------------------------------------------


def cache_write(state: AILightState) -> dict[str, Any]:
    """Write the final output to Redis with an appropriate TTL."""
    insight_type = state.get("insight_type", "summary")
    tenant_id = state.get("tenant_id", "0")
    params_hash = state.get("params_hash", "")

    ttl_map = {
        "summary": _TTL_SUMMARY,
        "anomalies": _TTL_ANOMALIES,
        "changes": _TTL_CHANGES,
        "deep_dive": _TTL_DEEP_DIVE,
    }
    ttl = ttl_map.get(insight_type, _TTL_SUMMARY)

    key = _cache_key(tenant_id, insight_type, params_hash)
    payload = {
        "narrative": state.get("narrative"),
        "highlights": state.get("highlights"),
        "degraded": state.get("degraded", False),
    }
    try:
        cache_set(key, payload, ttl=ttl)
        log.info("ai_light_cache_written", key=key, ttl=ttl)
    except Exception as exc:
        log.warning("ai_light_cache_write_failed", error=str(exc))

    trace = _make_trace_entry("cache_write", key=key, ttl=ttl)
    return {"step_trace": [trace]}
