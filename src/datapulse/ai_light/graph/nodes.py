"""LangGraph node functions for the AI Light graph.

Every node is a pure function:  ``(state, tools, client, settings) -> dict``
returning only the *delta* keys it produces. The graph builder wraps these
in lambdas that supply the closed-over dependencies.

Node execution order (non-deep-dive):
    cache_check → route → plan_* → fetch_data → analyze → validate
        → synthesize  (happy path)
        → analyze     (retry, up to 2 times)
        → fallback    (after 2 retries)
    cost_track → cache_write → END
"""

from __future__ import annotations

import json
import re
import statistics
import time
from collections.abc import Callable
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from datapulse.ai_light.graph.schemas import SCHEMA_REGISTRY
from datapulse.logging import get_logger

if TYPE_CHECKING:
    from datapulse.ai_light.client import OpenRouterClient
    from datapulse.ai_light.graph.state import AILightState
    from datapulse.config import Settings

log = get_logger(__name__)

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_INJECTION_RE = re.compile(
    r"(?i)(ignore\s+(previous|above)|system\s*:|<\s*/?\s*system|you\s+are\s+now)"
)


def _sanitize(text: str, max_len: int = 200) -> str:
    cleaned = _CONTROL_CHARS.sub(" ", str(text))
    cleaned = _INJECTION_RE.sub("", cleaned)
    return cleaned.strip()[:max_len]


def _trace(node: str, **extra: Any) -> dict[str, Any]:
    return {"node": node, "ts": time.time(), **extra}


# ── plan nodes ────────────────────────────────────────────────────────────


def plan_summary(state: AILightState) -> dict[str, Any]:
    """Declare the tool calls needed for the summary path."""
    return {
        "step_trace": [_trace("plan_summary")],
        "_tools_plan": ["get_kpi_summary", "get_top_products", "get_top_customers"],
    }


def plan_anomalies(state: AILightState) -> dict[str, Any]:
    """Declare tool calls needed for anomaly detection.

    Fetches daily trend data + active monitoring alerts so the LLM can
    combine statistical signals with pre-existing alert context.
    """
    return {
        "step_trace": [_trace("plan_anomalies")],
        "_tools_plan": ["get_daily_trend", "get_active_anomaly_alerts"],
    }


def plan_changes(state: AILightState) -> dict[str, Any]:
    """Declare tool calls needed for change narrative.

    Fetches KPI snapshots for both periods plus top gainers/losers and
    top staff, giving the LLM multi-dimensional change context.
    """
    return {
        "step_trace": [_trace("plan_changes")],
        "_tools_plan": [
            "get_kpi_current",
            "get_kpi_previous",
            "get_top_gainers",
            "get_top_losers",
            "get_top_staff",
        ],
    }


# ── fetch_data node ───────────────────────────────────────────────────────


def make_fetch_data_node(
    tools: dict[str, Callable[..., dict[str, Any]]],
) -> Callable[[AILightState], dict[str, Any]]:
    """Return a fetch_data node closed over *tools*."""

    def fetch_data(state: AILightState) -> dict[str, Any]:  # noqa: C901 (acceptable complexity)
        insight = state.get("insight_type", "summary")
        start = state.get("start_date")
        end = state.get("end_date")
        target = state.get("target_date")
        current = state.get("current_date")
        previous = state.get("previous_date")
        updates: dict[str, Any] = {"step_trace": [_trace("fetch_data", insight=insight)]}

        try:
            if insight == "summary":
                updates["kpi_data"] = tools["get_kpi_summary"](target_date=target)
                updates["top_products"] = tools["get_top_products"](start_date=start, end_date=end)
                updates["top_customers"] = tools["get_top_customers"](
                    start_date=start, end_date=end
                )

            elif insight == "anomalies":
                updates["daily_trend"] = tools["get_daily_trend"](start_date=start, end_date=end)
                updates["anomaly_alerts"] = tools["get_active_anomaly_alerts"](limit=10).get(
                    "alerts", []
                )

            elif insight == "changes":
                updates["kpi_current"] = tools["get_kpi_summary"](target_date=current)
                updates["kpi_previous"] = tools["get_kpi_summary"](target_date=previous)

                # Build date windows for movers: 30-day window around each anchor date
                if current and previous:
                    curr_end = current
                    curr_start = current - timedelta(days=30)
                    prev_end = previous
                    prev_start = previous - timedelta(days=30)

                    gainers = tools["get_top_gainers"](
                        current_start=curr_start,
                        current_end=curr_end,
                        previous_start=prev_start,
                        previous_end=prev_end,
                    )
                    losers = tools["get_top_losers"](
                        current_start=curr_start,
                        current_end=curr_end,
                        previous_start=prev_start,
                        previous_end=prev_end,
                    )
                    staff = tools["get_top_staff"](start_date=curr_start, end_date=curr_end)
                    updates["top_gainers"] = gainers
                    updates["top_losers"] = losers
                    updates["top_staff"] = staff

        except Exception as exc:
            log.error("fetch_data_failed", error=str(exc), insight=insight)
            existing = list(state.get("errors") or [])
            updates["errors"] = [*existing, f"fetch_data: {exc}"]

        return updates

    return fetch_data


# ── analyze node ─────────────────────────────────────────────────────────


def _build_anomaly_stats(daily_trend: dict[str, Any]) -> dict[str, Any]:
    """Compute statistical summary from daily trend data."""
    points = daily_trend.get("points", [])
    values = [float(p.get("value", 0)) for p in points if p.get("value") is not None]
    if len(values) < 2:
        return {"avg": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "count": len(values)}
    avg = statistics.mean(values)
    std = statistics.stdev(values)
    return {
        "avg": round(avg, 2),
        "std": round(std, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "count": len(values),
    }


def _build_changes_stats(
    kpi_current: dict[str, Any], kpi_previous: dict[str, Any]
) -> dict[str, Any]:
    """Compute period-over-period deltas for the statistical_analysis."""
    metrics = [
        "today_gross",
        "mtd_gross",
        "ytd_gross",
        "daily_transactions",
        "daily_customers",
    ]
    deltas: list[dict[str, Any]] = []
    for m in metrics:
        curr = float(kpi_current.get(m, 0) or 0)
        prev = float(kpi_previous.get(m, 0) or 0)
        pct = ((curr - prev) / abs(prev) * 100) if prev != 0 else 0.0
        deltas.append(
            {
                "metric": m,
                "current_value": curr,
                "previous_value": prev,
                "change_pct": round(pct, 2),
                "direction": "up" if pct > 1 else ("down" if pct < -1 else "flat"),
            }
        )
    return {"deltas": deltas}


def make_analyze_node(
    client: OpenRouterClient,
    settings: Settings,
) -> Callable[[AILightState], dict[str, Any]]:
    """Return an analyze node closed over *client*."""

    from datapulse.ai_light.graph.prompts import (
        ANOMALY_PROMPT_V2,
        CHANGES_PROMPT_V2,
        SUMMARY_PROMPT_V2,
        SYSTEM_PROMPT,
    )

    def analyze(state: AILightState) -> dict[str, Any]:  # noqa: C901
        insight = state.get("insight_type", "summary")
        updates: dict[str, Any] = {"step_trace": [_trace("analyze", insight=insight)]}
        stat_analysis: dict[str, Any] = {}
        prompt: str | None = None

        # Build statistical analysis + prompt per insight type
        if insight == "summary":
            kpi = state.get("kpi_data") or {}
            top_products = state.get("top_products") or {}
            top_customers = state.get("top_customers") or {}

            products_text = "\n".join(
                f"  {i.get('rank', idx + 1)}. {_sanitize(i.get('name', ''))}: "
                f"{float(i.get('value', 0)):,.0f} EGP"
                for idx, i in enumerate((top_products.get("items") or [])[:5])
            )
            customers_text = "\n".join(
                f"  {i.get('rank', idx + 1)}. {_sanitize(i.get('name', ''))}: "
                f"{float(i.get('value', 0)):,.0f} EGP"
                for idx, i in enumerate((top_customers.get("items") or [])[:5])
            )
            stat_analysis = {
                "today_gross": kpi.get("today_gross", 0),
                "mtd_gross": kpi.get("mtd_gross", 0),
            }
            prompt = SUMMARY_PROMPT_V2.format(
                today_gross=f"{float(kpi.get('today_gross', 0)):,.0f}",
                mtd_gross=f"{float(kpi.get('mtd_gross', 0)):,.0f}",
                ytd_gross=f"{float(kpi.get('ytd_gross', 0)):,.0f}",
                mom_growth=f"{float(kpi.get('mom_growth_pct') or 0):.1f}",
                yoy_growth=f"{float(kpi.get('yoy_growth_pct') or 0):.1f}",
                daily_transactions=kpi.get("daily_transactions", 0),
                daily_customers=kpi.get("daily_customers", 0),
                top_products=products_text or "No data",
                top_customers=customers_text or "No data",
            )

        elif insight == "anomalies":
            daily = state.get("daily_trend") or {}
            alerts = state.get("anomaly_alerts") or []
            stat_analysis = _build_anomaly_stats(daily)
            points = daily.get("points", [])
            daily_text = "\n".join(
                f"  {_sanitize(p.get('period', ''))}: {float(p.get('value', 0)):,.0f} EGP"
                for p in points
            )
            alerts_text = (
                "\n".join(
                    f"  - {_sanitize(a.get('metric', ''))}: {a.get('severity', 'medium')} "
                    f"severity on {_sanitize(a.get('period', ''))}"
                    for a in alerts[:5]
                )
                or "None"
            )
            prompt = ANOMALY_PROMPT_V2.format(
                daily_data=daily_text or "No data",
                avg=f"{stat_analysis['avg']:,.0f}",
                std_dev=f"{stat_analysis['std']:,.0f}",
                min_val=f"{stat_analysis['min']:,.0f}",
                max_val=f"{stat_analysis['max']:,.0f}",
                active_alerts=alerts_text,
            )

        elif insight == "changes":
            kpi_curr = state.get("kpi_current") or {}
            kpi_prev = state.get("kpi_previous") or {}
            stat_analysis = _build_changes_stats(kpi_curr, kpi_prev)
            gainers = state.get("top_gainers") or {}
            losers = state.get("top_losers") or {}
            staff = state.get("top_staff") or {}

            def _fmt_movers(items: list) -> str:
                return (
                    ", ".join(
                        f"{_sanitize(m.get('name', ''))}: {float(m.get('change_pct', 0)):+.1f}%"
                        for m in items[:3]
                    )
                    or "None"
                )

            def _fmt_staff(items: list) -> str:
                return (
                    ", ".join(
                        f"{_sanitize(m.get('name', ''))}: {float(m.get('value', 0)):,.0f} EGP"
                        for m in items[:3]
                    )
                    or "None"
                )

            current_dt = state.get("current_date") or date.today()
            previous_dt = state.get("previous_date") or (current_dt - timedelta(days=30))

            prompt = CHANGES_PROMPT_V2.format(
                current_period=current_dt.isoformat(),
                previous_period=previous_dt.isoformat(),
                current_net=f"{float(kpi_curr.get('today_gross', 0)):,.0f}",
                current_txns=kpi_curr.get("daily_transactions", 0),
                current_customers=kpi_curr.get("daily_customers", 0),
                previous_net=f"{float(kpi_prev.get('today_gross', 0)):,.0f}",
                previous_txns=kpi_prev.get("daily_transactions", 0),
                previous_customers=kpi_prev.get("daily_customers", 0),
                top_gainers=_fmt_movers(gainers.get("gainers") or []),
                top_losers=_fmt_movers(losers.get("losers") or []),
                top_staff=_fmt_staff(staff.get("items") or []),
            )

        updates["statistical_analysis"] = stat_analysis

        # LLM call — skip if no prompt or client unconfigured
        if prompt and client.is_configured:
            try:
                raw = client.chat(SYSTEM_PROMPT, prompt, temperature=0.2)
                updates["llm_raw_output"] = raw
                updates["model_used"] = getattr(settings, "openrouter_model", "unknown")
                # Best-effort token usage (may not be returned by all models)
                updates["token_usage"] = {"input": 0, "output": 0, "total": 0}
                # Parse JSON
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    lines = [ln for ln in cleaned.split("\n") if not ln.strip().startswith("```")]
                    cleaned = "\n".join(lines)
                parsed = json.loads(cleaned)
                updates["llm_parsed_output"] = parsed
            except json.JSONDecodeError as exc:
                log.warning("analyze_json_parse_failed", error=str(exc))
                existing = list(state.get("errors") or [])
                updates["errors"] = [*existing, f"json_parse: {exc}"]
            except Exception as exc:
                log.warning("analyze_llm_failed", error=str(exc))
                existing = list(state.get("errors") or [])
                updates["errors"] = [*existing, f"llm: {exc}"]

        return updates

    return analyze


# ── validate node ─────────────────────────────────────────────────────────


def validate(state: AILightState) -> dict[str, Any]:
    """Validate llm_parsed_output against the insight-type Pydantic schema.

    Returns:
        ``validation_retries`` incremented by 1 if validation fails.
        No changes on success (edges handle routing).
    """
    insight = state.get("insight_type", "summary")
    parsed = state.get("llm_parsed_output")

    if parsed is None:
        retries = (state.get("validation_retries") or 0) + 1
        log.warning("validate_no_output", retries=retries)
        return {
            "validation_retries": retries,
            "step_trace": [_trace("validate", result="no_output", retries=retries)],
        }

    schema_cls = SCHEMA_REGISTRY.get(insight)
    if schema_cls is None:
        # Unknown type — pass through
        return {"step_trace": [_trace("validate", result="unknown_type")]}

    try:
        schema_cls.model_validate(parsed)
        return {"step_trace": [_trace("validate", result="ok")]}
    except Exception as exc:
        retries = (state.get("validation_retries") or 0) + 1
        log.warning("validate_schema_failed", insight=insight, retries=retries, error=str(exc))
        existing = list(state.get("errors") or [])
        return {
            "validation_retries": retries,
            "errors": [*existing, f"validation: {exc}"],
            "step_trace": [_trace("validate", result="failed", retries=retries)],
        }


# ── fallback node ─────────────────────────────────────────────────────────


def fallback(state: AILightState) -> dict[str, Any]:
    """Produce a stats-only response when LLM validation fails after max retries.

    Contract: must return the exact same shape as ``synthesize``.
    ``degraded=True`` signals to callers that the LLM path was not used.
    """
    insight = state.get("insight_type", "summary")
    updates: dict[str, Any] = {
        "degraded": True,
        "step_trace": [_trace("fallback", insight=insight)],
    }

    if insight == "summary":
        kpi = state.get("kpi_data") or {}
        gross = float(kpi.get("today_gross", 0))
        mtd = float(kpi.get("mtd_gross", 0))
        updates["narrative"] = (
            f"Today's gross sales: {gross:,.0f} EGP. "
            f"Month-to-date: {mtd:,.0f} EGP. "
            "(AI narrative unavailable — statistical summary only.)"
        )
        updates["highlights"] = [
            f"Today gross: {gross:,.0f} EGP",
            f"MTD: {mtd:,.0f} EGP",
        ]
        updates["anomalies_list"] = None
        updates["deltas"] = None

    elif insight == "anomalies":
        stat = state.get("statistical_analysis") or {}
        updates["narrative"] = (
            f"Statistical analysis detected anomalies in daily sales data. "
            f"Average: {stat.get('avg', 0):,.0f} EGP, "
            f"Std dev: {stat.get('std', 0):,.0f} EGP. "
            "(AI narrative unavailable — statistical summary only.)"
        )
        updates["highlights"] = None
        updates["anomalies_list"] = []
        updates["deltas"] = None

    elif insight == "changes":
        stat = state.get("statistical_analysis") or {}
        deltas = stat.get("deltas", [])
        parts = [
            f"{d['metric']}: {d['current_value']:,.0f} "
            f"({d['direction']} {abs(d['change_pct']):.1f}%)"
            for d in deltas
        ]
        updates["narrative"] = (
            "Period comparison: " + "; ".join(parts) + ". (AI narrative unavailable.)"
        )
        updates["highlights"] = None
        updates["anomalies_list"] = None
        updates["deltas"] = deltas

    else:
        updates["narrative"] = "AI analysis unavailable — statistical fallback."
        updates["highlights"] = None
        updates["anomalies_list"] = None
        updates["deltas"] = None

    return updates


# ── synthesize node ───────────────────────────────────────────────────────


def synthesize(state: AILightState) -> dict[str, Any]:
    """Compose final output from validated LLM output + statistical analysis.

    Contract: produces the same keys as ``fallback`` with ``degraded=False``.
    """
    insight = state.get("insight_type", "summary")
    parsed = state.get("llm_parsed_output") or {}
    stat = state.get("statistical_analysis") or {}
    updates: dict[str, Any] = {
        "degraded": False,
        "step_trace": [_trace("synthesize", insight=insight)],
    }

    if insight == "summary":
        updates["narrative"] = parsed.get("narrative", "")
        updates["highlights"] = parsed.get("highlights", [])
        updates["anomalies_list"] = None
        updates["deltas"] = None

    elif insight == "anomalies":
        raw_anomalies = parsed.get("anomalies", [])
        updates["narrative"] = parsed.get("narrative", "")
        updates["highlights"] = None
        updates["anomalies_list"] = [
            {
                "date": a.get("date", ""),
                "description": _sanitize(a.get("description", ""), 500),
                "severity": (
                    a.get("severity", "low")
                    if a.get("severity") in ("low", "medium", "high")
                    else "low"
                ),
            }
            for a in raw_anomalies
            if isinstance(a, dict)
        ]
        updates["deltas"] = None

    elif insight == "changes":
        updates["narrative"] = parsed.get("narrative", "")
        updates["highlights"] = parsed.get("key_changes", [])
        updates["anomalies_list"] = None
        updates["deltas"] = stat.get("deltas")

    else:
        updates["narrative"] = parsed.get("narrative", "")
        updates["highlights"] = None
        updates["anomalies_list"] = None
        updates["deltas"] = None

    return updates


# ── cost_track node ───────────────────────────────────────────────────────


def make_cost_track_node(
    session: Any,
    start_time_ref: list[float],
) -> Callable[[AILightState], dict[str, Any]]:
    """Return a cost_track node that writes to ai_invocations."""

    def cost_track(state: AILightState) -> dict[str, Any]:
        from datapulse.ai_light.graph.cost import compute_cost_cents, write_invocation_row

        token_usage = state.get("token_usage") or {}
        model = state.get("model_used") or ""
        cost = compute_cost_cents(
            model,
            token_usage.get("input", 0),
            token_usage.get("output", 0),
        )
        t_start = start_time_ref[0] if start_time_ref else time.time()
        duration_ms = int((time.time() - t_start) * 1000)
        status = "degraded" if state.get("degraded") else "success"
        errors = state.get("errors") or []

        try:
            tid_str = state.get("tenant_id", "1")
            write_invocation_row(
                session,
                run_id=state.get("run_id", ""),
                insight_type=state.get("insight_type", ""),
                model=model,
                token_usage=token_usage,
                cost_cents=cost,
                duration_ms=duration_ms,
                status=status,
                error_message="; ".join(errors[:3]) if errors else None,
                tenant_id=int(tid_str) if str(tid_str).isdigit() else 1,
            )
        except Exception as exc:
            log.warning("cost_track_write_failed", error=str(exc))

        return {
            "cost_cents": cost,
            "step_trace": [_trace("cost_track", cost_cents=cost, status=status)],
        }

    return cost_track
