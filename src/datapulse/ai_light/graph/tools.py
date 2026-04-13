"""LangGraph tool registry for AI-Light.

Builds the 15-tool registry defined in §4 of the plan.  Tools are closure-bound
to a *per-request*, tenant-scoped SQLAlchemy session so each LangGraph run is
fully RLS-isolated.

Each tool wraps an existing service/repository method and returns a plain ``dict``
(serialised via ``.model_dump(mode="json")`` for Pydantic models).  The
``@tool`` decorator (from ``langchain_core.tools``) auto-generates the
``args_schema`` from type hints.

Tool registry
-------------
 1. ``get_kpi_summary``       — AnalyticsRepository.get_kpi_summary
 2. ``get_daily_trend``       — AnalyticsRepository.get_daily_trend
 3. ``get_monthly_trend``     — AnalyticsRepository.get_monthly_trend
 4. ``get_top_products``      — AnalyticsRepository.get_top_products
 5. ``get_top_customers``     — AnalyticsRepository.get_top_customers
 6. ``get_top_staff``         — AnalyticsRepository.get_top_staff
 7. ``get_site_performance``  — AnalyticsService.get_site_comparison
 8. ``get_top_gainers``       — AnalyticsService.get_top_movers(direction="up")
 9. ``get_top_losers``        — AnalyticsService.get_top_movers(direction="down")
10. ``get_active_anomaly_alerts`` — AnomalyService.get_active_alerts
11. ``get_revenue_forecast``  — ForecastingService.get_revenue_forecast
12. ``get_forecast_summary``  — ForecastingService.get_forecast_summary
13. ``get_customer_segments`` — ForecastingService.get_customer_segments
14. ``get_target_vs_actual``  — TargetsService.get_target_summary
15. ``get_churn_risk``        — ChurnRepository.get_risk_distribution

Implementation note (Phase A-1): placeholder — ``build_tool_registry`` is
declared but not implemented.  The ``langchain_core`` import is guarded so the
``[ai]`` extras are not required at import time.
"""

from __future__ import annotations

from typing import Any


def build_tool_registry(session: Any, settings: Any) -> list[Any]:  # noqa: ARG001
    """Build and return the list of LangChain tools for a single graph run.

    Parameters
    ----------
    session:
        A tenant-scoped SQLAlchemy ``Session`` (RLS already applied via
        ``SET LOCAL app.tenant_id``).
    settings:
        Application ``Settings`` instance.

    Returns
    -------
    list[BaseTool]
        Fifteen tools bound to *session*, ready for the ReAct agent node.

    Raises
    ------
    NotImplementedError
        Until Phase A implements the summary path.
    """
    raise NotImplementedError("Tool registry will be implemented in Phase A (summary path).")
