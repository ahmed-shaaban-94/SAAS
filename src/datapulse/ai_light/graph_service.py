"""AILightGraphService — LangGraph-backed implementation of the AI-Light service.

Implements the same interface as AILightService so deps.py can swap them
transparently behind the feature flag ai_light_use_langgraph.

Key Phase D additions:
- start_deep_dive(require_review=True) → pauses at synthesize, returns run_id + draft
- get_review_state(run_id) → pending draft for human review
- approve_run(run_id, edits) → resumes the graph with human edits merged

SSE streaming is handled at the route level (stream=True query param).  This
service exposes stream_run() as an async generator of (node, partial_state) tuples.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from datapulse.ai_light.models import (
    AISummary,
    Anomaly,
    AnomalyReport,
    ChangeDelta,
    ChangeNarrative,
    DeepDiveDraft,
    DeepDiveRequest,
    DeepDiveResponse,
)
from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)

# Module-level graph cache (compiled once per process)
_compiled_graph = None
_compiled_settings_hash: str | None = None


def _get_graph(settings: Settings):
    global _compiled_graph, _compiled_settings_hash

    key = f"{settings.ai_light_checkpoint_backend}:{settings.database_url[:30]}"
    if _compiled_graph is None or _compiled_settings_hash != key:
        from datapulse.ai_light.graph.builder import build_graph

        _compiled_graph = build_graph(settings)
        _compiled_settings_hash = key

    return _compiled_graph


def _params_hash(data: dict) -> str:
    return hashlib.md5(  # nosec B324 (non-cryptographic cache key, not used for security)
        json.dumps(data, sort_keys=True, default=str).encode(),
        usedforsecurity=False,
    ).hexdigest()[:16]


def _thread_id(tenant_id: str, insight_type: str, run_id: str) -> str:
    return f"{tenant_id}:{insight_type}:{run_id}"


class AILightGraphService:
    """LangGraph-backed AI-Light service.

    Session is kept for tool closures (RLS-scoped) and cost tracking.
    The compiled graph is reused across requests.
    """

    def __init__(self, settings: Settings, session: Session) -> None:
        self._settings = settings
        self._session = session
        self._graph = _get_graph(settings)

    @property
    def is_available(self) -> bool:
        return bool(self._settings.openrouter_api_key)

    # ------------------------------------------------------------------
    # Legacy interface (identical shape to AILightService)
    # ------------------------------------------------------------------

    def generate_summary(self, target_date: date | None = None) -> AISummary:
        target = target_date or date.today()
        state = self._build_initial_state("summary", target_date=str(target))
        final = self._run_sync(state)
        return AISummary(
            narrative=final.get("narrative", "Summary unavailable."),
            highlights=final.get("highlights", []),
            period=str(target),
        )

    def detect_anomalies(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AnomalyReport:
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=30))
        state = self._build_initial_state("anomalies", start_date=str(start), end_date=str(end))
        final = self._run_sync(state)
        anomalies = [
            Anomaly(
                date=a.get("date", ""),
                metric=a.get("metric", "daily_net_sales"),
                actual_value=a.get("actual_value", 0),
                expected_range_low=a.get("expected_range_low", 0),
                expected_range_high=a.get("expected_range_high", 0),
                severity=a.get("severity", "low"),
                description=a.get("description", ""),
            )
            for a in (final.get("anomalies_list") or [])
        ]
        return AnomalyReport(
            anomalies=anomalies,
            period=f"{start} to {end}",
            total_checked=len(anomalies),
        )

    def explain_changes(
        self,
        current_date: date | None = None,
        previous_date: date | None = None,
    ) -> ChangeNarrative:
        current = current_date or date.today()
        previous = previous_date or (current - timedelta(days=30))
        state = self._build_initial_state(
            "changes",
            start_date=str(previous),
            end_date=str(current),
        )
        final = self._run_sync(state)
        deltas = [
            ChangeDelta(
                metric=d.get("metric", ""),
                previous_value=d.get("previous_value", 0),
                current_value=d.get("current_value", 0),
                change_pct=d.get("change_pct", 0),
                direction=d.get("direction", "flat"),
            )
            for d in (final.get("deltas") or [])
        ]
        return ChangeNarrative(
            narrative=final.get("narrative", ""),
            deltas=deltas,
            current_period=str(current),
            previous_period=str(previous),
        )

    # ------------------------------------------------------------------
    # Deep-dive (Phase C/D)
    # ------------------------------------------------------------------

    def start_deep_dive(self, req: DeepDiveRequest) -> DeepDiveResponse | DeepDiveDraft:
        """Run a deep-dive.  If require_review=True, pauses at synthesize and
        returns a DeepDiveDraft (202 Accepted) instead of the full response."""
        run_id = str(uuid.uuid4())
        tenant_id = self._get_tenant_id()
        state = self._build_initial_state(
            "deep_dive",
            start_date=str(req.start_date or (date.today() - timedelta(days=30))),
            end_date=str(req.end_date or date.today()),
            run_id=run_id,
            require_review=req.require_review,
        )

        thread = _thread_id(tenant_id, "deep_dive", run_id)
        config: dict[str, Any] = {"configurable": {"thread_id": thread}}

        if req.require_review:
            config["interrupt_before"] = ["synthesize"]

        final = self._graph.invoke(state, config=config)

        # Check if interrupted (paused before synthesize)
        snapshot = self._graph.get_state(config)
        interrupted = bool(snapshot and snapshot.next)

        if interrupted:
            return DeepDiveDraft(
                run_id=run_id,
                tenant_id=tenant_id,
                narrative_draft=final.get("llm_raw_output", ""),
                highlights_draft=final.get("highlights") or [],
                data_snapshot=self._summarize_data_snapshot(final),
                step_trace=final.get("step_trace") or [],
            )

        return self._to_deep_dive_response(run_id, final)

    def get_review_state(self, run_id: str) -> DeepDiveDraft | None:
        """Return the pending draft state for a paused HITL run."""
        tenant_id = self._get_tenant_id()
        thread = _thread_id(tenant_id, "deep_dive", run_id)
        config = {"configurable": {"thread_id": thread}}

        try:
            snapshot = self._graph.get_state(config)
        except Exception as exc:
            log.warning("get_review_state_failed", run_id=run_id, error=str(exc))
            return None

        if not snapshot or not snapshot.next:
            return None  # not paused

        values = snapshot.values or {}
        return DeepDiveDraft(
            run_id=run_id,
            tenant_id=tenant_id,
            narrative_draft=values.get("llm_raw_output", ""),
            highlights_draft=values.get("highlights") or [],
            data_snapshot=self._summarize_data_snapshot(values),
            step_trace=values.get("step_trace") or [],
        )

    def approve_run(self, run_id: str, edits: dict | None = None) -> DeepDiveResponse:
        """Resume a paused HITL run, optionally injecting human edits."""
        tenant_id = self._get_tenant_id()
        thread = _thread_id(tenant_id, "deep_dive", run_id)
        config = {"configurable": {"thread_id": thread}}

        # Inject human edits into state before resuming
        if edits:
            self._graph.update_state(config, {"human_edits": edits}, as_node="synthesize")

        final = self._graph.invoke(None, config=config)  # None = resume from checkpoint
        return self._to_deep_dive_response(run_id, final)

    # ------------------------------------------------------------------
    # SSE streaming
    # ------------------------------------------------------------------

    async def stream_run(
        self,
        insight_type: str,
        **params,
    ) -> AsyncIterator[tuple[str, dict]]:
        """Async generator yielding (node_name, partial_state) tuples.

        Used by the SSE endpoint.  Requires an async-capable checkpointer
        or MemorySaver (which works synchronously inside astream).
        """
        run_id = params.pop("run_id", str(uuid.uuid4()))
        require_review = params.pop("require_review", False)
        tenant_id = self._get_tenant_id()

        state = self._build_initial_state(
            insight_type, run_id=run_id, require_review=require_review, **params
        )
        thread = _thread_id(tenant_id, insight_type, run_id)
        config: dict[str, Any] = {"configurable": {"thread_id": thread}}
        if require_review:
            config["interrupt_before"] = ["synthesize"]

        async for node_name, chunk in self._graph.astream(
            state, config=config, stream_mode="updates"
        ):
            yield node_name, chunk

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_tenant_id(self) -> str:
        """Extract tenant_id from the session's LOCAL setting."""
        try:
            from sqlalchemy import text

            row = self._session.execute(
                text("SELECT current_setting('app.tenant_id', true)")
            ).scalar()
            return str(row or "1")
        except Exception:
            return "1"

    def _build_initial_state(self, insight_type: str, **kwargs) -> dict:
        """Assemble the initial state dict injected into the graph."""
        params = {k: v for k, v in kwargs.items() if v is not None}
        return {
            "insight_type": insight_type,
            "tenant_id": self._get_tenant_id(),
            "run_id": kwargs.get("run_id", str(uuid.uuid4())),
            "params_hash": _params_hash({"insight_type": insight_type, **params}),
            "require_review": kwargs.get("require_review", False),
            "validation_retries": 0,
            "circuit_breaker_failures": 0,
            "cache_hit": False,
            "degraded": False,
            "step_trace": [],
            "errors": [],
            "token_usage": {"input": 0, "output": 0, "total": 0},
            "cost_cents": 0.0,
            # Injected runtime dependencies (not serialised into checkpoint)
            "_session": self._session,
            "_openrouter_api_key": self._settings.openrouter_api_key,
            "_openrouter_model": (
                self._settings.openrouter_agent_model or self._settings.openrouter_model
            ),
            "_tools": self._build_tool_registry(),
            "_start_ms": time.monotonic() * 1000,
            **params,
        }

    def _build_tool_registry(self) -> dict:
        """Return a dict of tool_name → callable, all bound to the current session."""
        from datapulse.analytics.models import AnalyticsFilter
        from datapulse.analytics.repository import AnalyticsRepository

        repo = AnalyticsRepository(self._session)
        today = date.today()
        default_filter = AnalyticsFilter(limit=10)

        tools = {
            "get_kpi_summary": lambda: _to_dict(repo.get_kpi_summary(today)),
            "get_top_products": lambda: _to_dict(repo.get_top_products(default_filter)),
            "get_top_customers": lambda: _to_dict(repo.get_top_customers(default_filter)),
        }

        # Optional tools — only register if the repos are importable
        try:
            from datapulse.analytics.trend_repository import TrendRepository

            trend_repo = TrendRepository(self._session)
            tools["get_daily_trend"] = lambda: _to_dict(trend_repo.get_daily_trend(default_filter))
            tools["get_monthly_trend"] = lambda: _to_dict(
                trend_repo.get_monthly_trend(default_filter)
            )
        except ImportError:
            pass

        try:
            from datapulse.anomalies.service import AnomalyService

            anomaly_svc = AnomalyService(self._session)
            tools["get_active_anomaly_alerts"] = lambda: _to_dict(
                anomaly_svc.get_active_alerts(limit=20)
            )
        except ImportError:
            pass

        try:
            from datapulse.forecasting.repository import ForecastingRepository
            from datapulse.forecasting.service import ForecastingService

            fc_svc = ForecastingService(ForecastingRepository(self._session))
            tools["get_forecast_summary"] = lambda: _to_dict(fc_svc.get_forecast_summary())
        except ImportError:
            pass

        try:
            from datapulse.targets.repository import TargetsRepository
            from datapulse.targets.service import TargetsService

            tgt_svc = TargetsService(TargetsRepository(self._session))
            tools["get_target_vs_actual"] = lambda: _to_dict(tgt_svc.get_target_summary(today.year))
        except ImportError:
            pass

        return tools

    @staticmethod
    def _summarize_data_snapshot(state: dict) -> dict:
        """Extract a compact view of fetched data for the review UI."""
        fetched = state.get("fetched_data") or {}
        stats = state.get("statistical_analysis") or {}
        kpi = fetched.get("get_kpi_summary", {})
        return {
            "kpi_snapshot": {
                "today_gross": kpi.get("today_gross"),
                "mtd_gross": kpi.get("mtd_gross"),
                "ytd_gross": kpi.get("ytd_gross"),
            },
            "statistical_analysis": stats,
            "tools_executed": list(fetched.keys()),
        }

    def _to_deep_dive_response(self, run_id: str, final: dict) -> DeepDiveResponse:
        from datapulse.ai_light.models import AIInsightMeta

        meta = AIInsightMeta(
            run_id=run_id,
            model=final.get("model_used", ""),
            tokens=final.get("token_usage", {}).get("total", 0),
            cost_cents=final.get("cost_cents", 0.0),
            degraded=final.get("degraded", False),
            duration_ms=0,
        )
        return DeepDiveResponse(
            narrative=final.get("narrative", ""),
            highlights=final.get("highlights") or [],
            anomalies_list=final.get("anomalies_list") or [],
            deltas=final.get("deltas") or [],
            degraded=final.get("degraded", False),
            meta=meta,
        )

    def _run_sync(self, state: dict) -> dict:
        """Invoke the graph synchronously and return the final state."""
        tenant_id = state.get("tenant_id", "1")
        run_id = state.get("run_id", str(uuid.uuid4()))
        insight_type = state.get("insight_type", "summary")
        thread = _thread_id(tenant_id, insight_type, run_id)
        config = {"configurable": {"thread_id": thread}}
        result = self._graph.invoke(state, config=config)
        return result or {}


def _to_dict(obj: Any) -> dict | list:
    """Convert Pydantic model or arbitrary object to dict/list for state storage."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return vars(obj)
    return obj or {}
