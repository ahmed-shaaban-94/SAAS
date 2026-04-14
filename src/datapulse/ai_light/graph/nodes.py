"""LangGraph node functions for the AI-Light insight graph.

Each node is a pure function:  state -> dict  (partial state update).
Nodes never mutate the input state; they return deltas.

Node execution order (happy path):
    cache_check -> route -> plan_* -> fetch_data -> analyze
                -> validate -> synthesize -> cost_track -> cache_write -> END

Phase D additions:
    synthesize is an interrupt point when state["require_review"] is True.
    After human approval the graph resumes at synthesize with optional edits merged.
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime

import httpx

from datapulse.ai_light.graph.cost import estimate_cost_cents, write_invocation_row
from datapulse.ai_light.graph.prompts import (
    ANOMALY_PROMPT,
    CHANGES_PROMPT,
    DEEP_DIVE_PROMPT,
    SUMMARY_PROMPT,
    SYSTEM_PROMPT,
)
from datapulse.ai_light.graph.schemas import SCHEMA_MAP
from datapulse.logging import get_logger

log = get_logger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_MAX_TOOL_ITERATIONS = 5
_MAX_VALIDATE_RETRIES = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_ts() -> str:
    return datetime.now(UTC).isoformat()


def _step(node: str, status: str, **extra) -> dict:
    return {"step_trace": [{"node": node, "ts": _now_ts(), "status": status, **extra}]}


def _call_openrouter(
    api_key: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
) -> tuple[str, dict]:
    """Call OpenRouter and return (content, usage_dict).  Raises on failure."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://datapulse.dev",
        "X-Title": "DataPulse AI-Light",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": 2048,
    }
    resp = httpx.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, usage


def _parse_json(raw: str) -> dict | list:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.split("\n") if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# cache_check
# ---------------------------------------------------------------------------


def cache_check(state: dict) -> dict:
    """Check Redis for a cached response.  Returns cache_hit=True and pre-fills
    outputs if found, or cache_hit=False to continue the graph."""
    # Redis cache check is handled by graph_service.py before invoking the graph.
    # Nodes don't have direct access to Redis; the service short-circuits instead.
    return {**_step("cache_check", "pass"), "cache_hit": False}


# ---------------------------------------------------------------------------
# route  (no-op — handled by conditional edge in builder)
# ---------------------------------------------------------------------------


def route(state: dict) -> dict:
    return _step("route", "pass")


# ---------------------------------------------------------------------------
# plan_* nodes
# ---------------------------------------------------------------------------


def plan_summary(state: dict) -> dict:
    return {
        **_step("plan_summary", "pass"),
        "planned_tools": ["get_kpi_summary", "get_top_products", "get_top_customers"],
    }


def plan_anomalies(state: dict) -> dict:
    return {
        **_step("plan_anomalies", "pass"),
        "planned_tools": ["get_daily_trend", "get_active_anomaly_alerts"],
    }


def plan_changes(state: dict) -> dict:
    return {
        **_step("plan_changes", "pass"),
        "planned_tools": ["get_kpi_summary"],
    }


def plan_deep_dive(state: dict) -> dict:
    return {
        **_step("plan_deep_dive", "pass"),
        "planned_tools": [
            "get_kpi_summary",
            "get_daily_trend",
            "get_monthly_trend",
            "get_top_products",
            "get_top_customers",
            "get_active_anomaly_alerts",
            "get_forecast_summary",
            "get_target_vs_actual",
        ],
    }


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------


def fetch_data(state: dict) -> dict:
    """Execute pre-planned tool calls using closures bound to the tenant session.

    For Phase A–C the tool registry (injected via state["_tools"]) maps tool
    names to callables.  For deep_dive the same registry is used; the
    plan_deep_dive node pre-selects which tools to run.

    If a tool raises, it is logged and omitted (degraded mode).
    """
    tools: dict = state.get("_tools", {})
    planned: list[str] = state.get("planned_tools", [])

    results: dict = {}
    errors: list[str] = []

    for tool_name in planned:
        fn = tools.get(tool_name)
        if fn is None:
            continue
        try:
            results[tool_name] = fn()
        except Exception as exc:
            log.warning("tool_call_failed", tool=tool_name, error=str(exc))
            errors.append(f"{tool_name}: {exc}")

    return {
        **_step("fetch_data", "done", tools_executed=list(results.keys())),
        "fetched_data": results,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def analyze(state: dict) -> dict:
    """Run statistical analysis and call OpenRouter for the narrative."""
    api_key: str = state.get("_openrouter_api_key", "")
    model: str = state.get("_openrouter_model", "openrouter/free")
    insight_type: str = state.get("insight_type", "summary")
    fetched: dict = state.get("fetched_data", {})
    retries: int = state.get("validation_retries", 0)

    # --- Statistical analysis (always; used as fallback too) ---
    stats: dict = {}
    daily = fetched.get("get_daily_trend", {})
    if daily and "points" in daily:
        values = [float(p.get("value", 0)) for p in daily["points"]]
        if len(values) >= 2:
            stats["mean"] = round(statistics.mean(values), 2)
            stats["stdev"] = round(statistics.stdev(values), 2)
            stats["min"] = round(min(values), 2)
            stats["max"] = round(max(values), 2)

    if not api_key:
        return {
            **_step("analyze", "no_api_key"),
            "statistical_analysis": stats,
            "llm_raw_output": None,
            "llm_parsed_output": None,
            "token_usage": {"input": 0, "output": 0, "total": 0},
        }

    # --- Build prompt based on insight_type ---
    prompt = _build_prompt(insight_type, fetched, state, stats)

    try:
        raw, usage = _call_openrouter(api_key, model, SYSTEM_PROMPT, prompt)
        parsed = _parse_json(raw)
        return {
            **_step("analyze", "done", attempt=retries),
            "statistical_analysis": stats,
            "llm_raw_output": raw,
            "llm_parsed_output": parsed if isinstance(parsed, dict) else {"items": parsed},
            "model_used": model,
            "token_usage": {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
        }
    except Exception as exc:
        log.warning("analyze_failed", error=str(exc), attempt=retries)
        return {
            **_step("analyze", "error", error=str(exc)),
            "statistical_analysis": stats,
            "llm_raw_output": None,
            "llm_parsed_output": None,
            "errors": [f"analyze: {exc}"],
            "token_usage": {"input": 0, "output": 0, "total": 0},
        }


def _build_prompt(insight_type: str, fetched: dict, state: dict, stats: dict) -> str:
    kpi = fetched.get("get_kpi_summary", {})
    daily = fetched.get("get_daily_trend", {})
    points = daily.get("points", [])

    if insight_type == "summary":
        top_products = fetched.get("get_top_products", {}).get("items", [])
        top_customers = fetched.get("get_top_customers", {}).get("items", [])
        return SUMMARY_PROMPT.format(
            today_date=state.get("target_date", "today"),
            today_gross=f"{kpi.get('today_gross', 0):,.0f}",
            mtd_gross=f"{kpi.get('mtd_gross', 0):,.0f}",
            ytd_gross=f"{kpi.get('ytd_gross', 0):,.0f}",
            mom_growth=f"{kpi.get('mom_growth_pct') or 0:.1f}",
            yoy_growth=f"{kpi.get('yoy_growth_pct') or 0:.1f}",
            daily_transactions=kpi.get("daily_transactions", 0),
            daily_customers=kpi.get("daily_customers", 0),
            top_products="\n".join(
                f"  {i + 1}. {p.get('name', '')}: {p.get('value', 0):,.0f} EGP"
                for i, p in enumerate(top_products[:5])
            ),
            top_customers="\n".join(
                f"  {i + 1}. {c.get('name', '')}: {c.get('value', 0):,.0f} EGP"
                for i, c in enumerate(top_customers[:5])
            ),
        )

    if insight_type == "anomalies":
        daily_text = "\n".join(
            f"  {p.get('period', '')}: {p.get('value', 0):,.0f} EGP" for p in points
        )
        return ANOMALY_PROMPT.format(
            daily_data=daily_text or "(no data)",
            avg=f"{stats.get('mean', 0):,.0f}",
            std_dev=f"{stats.get('stdev', 0):,.0f}",
            min_val=f"{stats.get('min', 0):,.0f}",
            max_val=f"{stats.get('max', 0):,.0f}",
        )

    if insight_type == "changes":
        kpi2 = fetched.get("get_kpi_summary_previous", kpi)
        return CHANGES_PROMPT.format(
            current_period=state.get("end_date", "current"),
            previous_period=state.get("start_date", "previous"),
            current_net=f"{kpi.get('today_gross', 0):,.0f}",
            current_txns=kpi.get("daily_transactions", 0),
            current_customers=kpi.get("daily_customers", 0),
            previous_net=f"{kpi2.get('today_gross', 0):,.0f}",
            previous_txns=kpi2.get("daily_transactions", 0),
            previous_customers=kpi2.get("daily_customers", 0),
            top_movers="(see data above)",
        )

    # deep_dive
    return DEEP_DIVE_PROMPT.format(
        start_date=state.get("start_date", ""),
        end_date=state.get("end_date", ""),
    )


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def validate(state: dict) -> dict:
    """Validate LLM output against the Pydantic schema for this insight type.

    Returns validation_retries unchanged on success, incremented on failure.
    The conditional edge uses this to route to analyze (retry) or fallback.
    """
    insight_type: str = state.get("insight_type", "summary")
    parsed = state.get("llm_parsed_output")
    retries: int = state.get("validation_retries", 0)

    if parsed is None:
        return {
            **_step("validate", "null_output"),
            "validation_retries": retries + 1,
            "errors": ["validate: llm_parsed_output is None"],
        }

    schema_cls = SCHEMA_MAP.get(insight_type)
    if schema_cls is None:
        return {**_step("validate", "no_schema"), "validation_retries": retries}

    try:
        schema_cls.model_validate(parsed)
        return {**_step("validate", "ok"), "validation_retries": retries}
    except Exception as exc:
        log.warning("validation_failed", insight_type=insight_type, error=str(exc))
        return {
            **_step("validate", "schema_error", error=str(exc)),
            "validation_retries": retries + 1,
            "errors": [f"validate: {exc}"],
        }


# ---------------------------------------------------------------------------
# fallback
# ---------------------------------------------------------------------------


def fallback(state: dict) -> dict:
    """Stats-only narrative when LLM validation exhausted or circuit open."""
    stats = state.get("statistical_analysis") or {}
    insight_type = state.get("insight_type", "summary")

    if stats:
        narrative = (
            f"Statistical summary ({insight_type}): "
            f"mean={stats.get('mean', 'N/A')}, "
            f"std={stats.get('stdev', 'N/A')}, "
            f"range=[{stats.get('min', 'N/A')}, {stats.get('max', 'N/A')}]."
        )
    else:
        narrative = f"Insight generation encountered an error. Please retry. ({insight_type})"

    return {
        **_step("fallback", "degraded"),
        "narrative": narrative,
        "highlights": ["Statistical analysis used; AI narrative unavailable."],
        "anomalies_list": [],
        "deltas": [],
        "degraded": True,
    }


# ---------------------------------------------------------------------------
# synthesize  (Phase D: interrupt point for HITL)
# ---------------------------------------------------------------------------


def synthesize(state: dict) -> dict:
    """Compose the final response from validated LLM output.

    Phase D: when require_review=True this node is the interrupt point.
    After interrupt_before=["synthesize"] fires, the run pauses here.
    On resume (POST /approve), human edits are merged into state before
    this node executes.
    """
    parsed = state.get("llm_parsed_output") or {}
    human_edits: dict = state.get("human_edits") or {}

    # Merge human edits (override specific keys)
    effective = {**parsed, **human_edits}

    narrative = effective.get("narrative", "")
    highlights = effective.get("highlights", [])
    anomalies_list = effective.get("anomalies", effective.get("anomalies_list", []))
    deltas = effective.get("deltas", [])

    return {
        **_step("synthesize", "done"),
        "narrative": narrative,
        "highlights": highlights if isinstance(highlights, list) else [],
        "anomalies_list": anomalies_list if isinstance(anomalies_list, list) else [],
        "deltas": deltas if isinstance(deltas, list) else [],
        "degraded": False,
    }


# ---------------------------------------------------------------------------
# cost_track
# ---------------------------------------------------------------------------


def cost_track(state: dict) -> dict:
    """Write an ai_invocations row (best-effort; never raises)."""
    session = state.get("_session")
    if session is None:
        return _step("cost_track", "skip_no_session")

    usage = state.get("token_usage") or {}
    input_t = int(usage.get("input", 0))
    output_t = int(usage.get("output", 0))
    model = state.get("model_used", "")
    cost = estimate_cost_cents(model, input_t, output_t)
    start_ms = state.get("_start_ms", 0)
    duration = int((time.monotonic() * 1000) - start_ms) if start_ms else 0
    status = "degraded" if state.get("degraded") else "success"
    errors = state.get("errors", [])
    if errors:
        status = "error" if not state.get("narrative") else status

    write_invocation_row(
        session,
        tenant_id=str(state.get("tenant_id", "1")),
        run_id=state.get("run_id", ""),
        insight_type=state.get("insight_type", "unknown"),
        model=model,
        input_tokens=input_t,
        output_tokens=output_t,
        cost_cents=cost,
        duration_ms=duration,
        status=status,
        error_message="; ".join(errors) if errors else None,
    )
    return {**_step("cost_track", "done"), "cost_cents": float(cost)}


# ---------------------------------------------------------------------------
# cache_write
# ---------------------------------------------------------------------------


def cache_write(state: dict) -> dict:
    """Write result to Redis (delegated to graph_service; node is a no-op marker)."""
    return _step("cache_write", "delegated")
