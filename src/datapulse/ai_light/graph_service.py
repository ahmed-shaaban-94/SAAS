"""AILightGraphService — LangGraph-backed implementation of the AI-Light interface.

Implements the same 4-method interface as AILightService (composition, not inheritance).
For Phase A-2, generate_summary runs the LangGraph flow; the other two methods
delegate to the wrapped AILightService.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from datapulse.ai_light.models import AISummary, AnomalyReport, ChangeNarrative
from datapulse.ai_light.service import AILightService
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)


class AILightGraphService:
    """LangGraph-backed AI-Light service.

    Wraps AILightService (composition) so that detect_anomalies and
    explain_changes continue to work while generate_summary uses the
    new LangGraph flow.
    """

    def __init__(self, settings: Settings, session: Session) -> None:
        self._settings = settings
        self._session = session
        self._legacy = AILightService(settings=settings, session=session)
        self._repo = AnalyticsRepository(session)

    @property
    def is_available(self) -> bool:
        return bool(self._settings.openrouter_api_key)

    def generate_summary(self, target_date: date | None = None) -> AISummary:
        """Run the LangGraph summary graph and return an AISummary."""
        target = target_date or date.today()

        params_hash = hashlib.md5(  # noqa: S324 — non-cryptographic use
            json.dumps({"target_date": target.isoformat()}, sort_keys=True).encode()
        ).hexdigest()

        tenant_id = str(getattr(self._session, "_tenant_id", "1"))
        run_id = str(uuid.uuid4())

        # Build per-request LLM and tool registry
        agent_model = self._settings.openrouter_agent_model or self._settings.openrouter_model
        llm = self._build_llm(agent_model)
        tools = self._build_tools()

        initial_state: dict[str, Any] = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "insight_type": "summary",
            "target_date": target.isoformat(),
            "params_hash": params_hash,
            "use_langgraph": True,
            "cache_hit": False,
            "validation_retries": 0,
            "circuit_breaker_failures": 0,
            "degraded": False,
            "step_trace": [],
        }

        thread_config = {"configurable": {"thread_id": f"{tenant_id}:summary:{run_id}"}}

        from datapulse.ai_light.graph.builder import build_graph, set_runtime_context

        set_runtime_context(llm=llm, tools=tools, session=self._session)
        graph = build_graph(self._settings)

        try:
            final_state = graph.invoke(initial_state, config=thread_config)
        except Exception as exc:
            log.error("ai_light_graph_failed", error=str(exc))
            # Fallback to legacy service on catastrophic failure
            return self._legacy.generate_summary(target_date=target_date)

        narrative = final_state.get("narrative") or ""
        highlights = final_state.get("highlights") or ["No highlights available."]

        if not narrative:
            log.warning("ai_light_graph_empty_output", run_id=run_id)
            return self._legacy.generate_summary(target_date=target_date)

        return AISummary(
            narrative=narrative,
            highlights=highlights,
            period=target.isoformat(),
        )

    def detect_anomalies(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AnomalyReport:
        """Delegate to legacy service (Phase B adds LangGraph path)."""
        return self._legacy.detect_anomalies(start_date=start_date, end_date=end_date)

    def explain_changes(
        self,
        current_date: date | None = None,
        previous_date: date | None = None,
    ) -> ChangeNarrative:
        """Delegate to legacy service (Phase B adds LangGraph path)."""
        return self._legacy.explain_changes(
            current_date=current_date, previous_date=previous_date
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_llm(self, model: str) -> Any:
        """Construct a ChatOpenAI instance pointing at OpenRouter."""
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            openai_api_key=self._settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
            max_tokens=1024,
            default_headers={
                "HTTP-Referer": "https://datapulse.dev",
                "X-Title": "DataPulse AI-Light",
            },
        )

    def _build_tools(self) -> list[Any]:
        """Build the tool registry bound to the current session."""
        from datapulse.ai_light.graph.tools import build_tool_registry

        return build_tool_registry(self._repo)
