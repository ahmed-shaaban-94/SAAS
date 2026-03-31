"""AI-Light business logic — orchestrates analytics data + OpenRouter LLM."""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from datapulse.ai_light.client import OpenRouterClient
from datapulse.ai_light.models import (
    AISummary,
    Anomaly,
    AnomalyReport,
    ChangeDelta,
    ChangeNarrative,
)
from datapulse.ai_light.prompts import (
    ANOMALY_PROMPT,
    CHANGES_PROMPT,
    SUMMARY_PROMPT,
    SYSTEM_PROMPT,
)
from datapulse.analytics.models import AnalyticsFilter, DateRange
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.config import Settings
from datapulse.logging import get_logger

log = get_logger(__name__)


import re as _re

_CONTROL_CHARS_RE = _re.compile(r"[\x00-\x1f\x7f-\x9f]")
_INJECTION_DELIMITERS_RE = _re.compile(r"[<>\[\]{}|\\`]")
_INJECTION_PREFIXES_RE = _re.compile(
    r"(?i)(ignore\s+(previous|above)|system\s*:|<\s*/?\s*system|you\s+are\s+now)"
)


def _sanitize_for_prompt(text: str, max_len: int = 100) -> str:
    """Strip control chars, prompt injection markers, and truncate user-controlled text."""
    cleaned = _CONTROL_CHARS_RE.sub(" ", text)
    cleaned = _INJECTION_DELIMITERS_RE.sub("", cleaned)
    cleaned = _INJECTION_PREFIXES_RE.sub("", cleaned)
    return cleaned.strip()[:max_len]


class AILightService:
    """Generates AI-powered insights from analytics data."""

    def __init__(self, settings: Settings, session: Session) -> None:
        self._client = OpenRouterClient(settings)
        self._repo = AnalyticsRepository(session)

    @property
    def is_available(self) -> bool:
        return self._client.is_configured

    def generate_summary(self, target_date: date | None = None) -> AISummary:
        """Generate an executive narrative summary."""
        target = target_date or date.today()

        kpi = self._repo.get_kpi_summary(target)
        top_products = self._repo.get_top_products(AnalyticsFilter(limit=5))
        top_customers = self._repo.get_top_customers(AnalyticsFilter(limit=5))

        products_text = "\n".join(
            f"  {i.rank}. {_sanitize_for_prompt(i.name)}: "
            f"{i.value:,.0f} EGP ({i.pct_of_total:.1f}%)"
            for i in top_products.items
        )
        customers_text = "\n".join(
            f"  {i.rank}. {_sanitize_for_prompt(i.name)}: "
            f"{i.value:,.0f} EGP ({i.pct_of_total:.1f}%)"
            for i in top_customers.items
        )

        prompt = SUMMARY_PROMPT.format(
            today_net=f"{kpi.today_net:,.0f}",
            mtd_net=f"{kpi.mtd_net:,.0f}",
            ytd_net=f"{kpi.ytd_net:,.0f}",
            mom_growth=f"{kpi.mom_growth_pct or 0:.1f}",
            yoy_growth=f"{kpi.yoy_growth_pct or 0:.1f}",
            daily_transactions=kpi.daily_transactions,
            daily_customers=kpi.daily_customers,
            top_products=products_text,
            top_customers=customers_text,
        )

        raw = self._client.chat(SYSTEM_PROMPT, prompt)

        # Parse: first paragraph = narrative, bullet lines = highlights
        lines = [line.strip() for line in raw.strip().split("\n") if line.strip()]
        highlights = [line.lstrip("•-* ") for line in lines if line.startswith(("•", "-", "*"))]
        narrative_lines = [line for line in lines if not line.startswith(("•", "-", "*"))]
        narrative = " ".join(narrative_lines) if narrative_lines else raw

        return AISummary(
            narrative=narrative,
            highlights=highlights or ["No highlights extracted."],
            period=target.isoformat(),
        )

    def detect_anomalies(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AnomalyReport:
        """Detect anomalies in daily sales data using statistical + AI analysis."""
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=30))

        filters = AnalyticsFilter(date_range=DateRange(start_date=start, end_date=end))
        trends = self._repo.get_daily_trend(filters)

        values = [float(p.value) for p in trends.points]
        if len(values) < 3:
            return AnomalyReport(
                anomalies=[], period=f"{start} to {end}", total_checked=len(values)
            )

        avg = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0

        # Statistical detection: points > 2 std devs from mean
        stat_anomalies = []
        for point in trends.points:
            val = float(point.value)
            if std > 0 and abs(val - avg) > 2 * std:
                severity = "high" if abs(val - avg) > 3 * std else "medium"
                direction = "spike" if val > avg else "drop"
                stat_anomalies.append(
                    Anomaly(
                        date=point.period,
                        metric="daily_net_sales",
                        actual_value=Decimal(str(val)),
                        expected_range_low=Decimal(str(round(avg - 2 * std, 2))),
                        expected_range_high=Decimal(str(round(avg + 2 * std, 2))),
                        severity=severity,
                        description=f"Unusual {direction}: {val:,.0f} EGP vs avg {avg:,.0f} EGP",
                    )
                )

        # If OpenRouter is available, enhance with AI analysis
        if self._client.is_configured and values:
            try:
                daily_text = "\n".join(f"  {p.period}: {p.value:,.0f} EGP" for p in trends.points)
                prompt = ANOMALY_PROMPT.format(
                    daily_data=daily_text,
                    avg=f"{avg:,.0f}",
                    std_dev=f"{std:,.0f}",
                    min_val=f"{min(values):,.0f}",
                    max_val=f"{max(values):,.0f}",
                )
                ai_results = self._client.chat_json(SYSTEM_PROMPT, prompt)
                if not isinstance(ai_results, list):
                    ai_results = [ai_results] if isinstance(ai_results, dict) else []
                for item in ai_results:
                    # Only add AI anomalies not already found statistically
                    ai_date = item.get("date", "")
                    if not any(a.date == ai_date for a in stat_anomalies):
                        stat_anomalies.append(
                            Anomaly(
                                date=ai_date,
                                metric="daily_net_sales",
                                actual_value=Decimal("0"),
                                expected_range_low=Decimal(str(round(avg - 2 * std, 2))),
                                expected_range_high=Decimal(str(round(avg + 2 * std, 2))),
                                severity=item.get("severity", "low"),
                                description=item.get("description", "AI-detected anomaly"),
                            )
                        )
            except Exception as exc:
                log.warning("ai_anomaly_detection_failed", error=str(exc))

        return AnomalyReport(
            anomalies=stat_anomalies,
            period=f"{start} to {end}",
            total_checked=len(values),
        )

    def explain_changes(
        self,
        current_date: date | None = None,
        previous_date: date | None = None,
    ) -> ChangeNarrative:
        """Compare two periods and generate a change narrative."""
        current = current_date or date.today()
        previous = previous_date or (current - timedelta(days=30))

        kpi_current = self._repo.get_kpi_summary(current)
        kpi_previous = self._repo.get_kpi_summary(previous)

        def _delta(metric: str, curr_val: Decimal, prev_val: Decimal) -> ChangeDelta:
            if prev_val and prev_val != 0:
                pct = ((curr_val - prev_val) / abs(prev_val)) * 100
            else:
                pct = Decimal("0")
            if pct > Decimal("1"):
                direction = "up"
            elif pct < Decimal("-1"):
                direction = "down"
            else:
                direction = "flat"
            return ChangeDelta(
                metric=metric,
                previous_value=prev_val,
                current_value=curr_val,
                change_pct=pct,
                direction=direction,
            )

        deltas = [
            _delta("Daily Net Sales", kpi_current.today_net, kpi_previous.today_net),
            _delta("MTD Net Sales", kpi_current.mtd_net, kpi_previous.mtd_net),
            _delta("YTD Net Sales", kpi_current.ytd_net, kpi_previous.ytd_net),
            _delta(
                "Daily Transactions",
                Decimal(kpi_current.daily_transactions),
                Decimal(kpi_previous.daily_transactions),
            ),
            _delta(
                "Daily Customers",
                Decimal(kpi_current.daily_customers),
                Decimal(kpi_previous.daily_customers),
            ),
        ]

        # Generate AI narrative if available
        narrative = self._build_change_narrative_text(deltas)
        if self._client.is_configured:
            try:
                prompt = CHANGES_PROMPT.format(
                    current_period=current.isoformat(),
                    previous_period=previous.isoformat(),
                    current_net=f"{kpi_current.today_net:,.0f}",
                    current_txns=kpi_current.daily_transactions,
                    current_customers=kpi_current.daily_customers,
                    previous_net=f"{kpi_previous.today_net:,.0f}",
                    previous_txns=kpi_previous.daily_transactions,
                    previous_customers=kpi_previous.daily_customers,
                    top_movers="(product-level detail not available for this comparison)",
                )
                narrative = self._client.chat(SYSTEM_PROMPT, prompt)
            except Exception as exc:
                log.warning("ai_change_narrative_failed", error=str(exc))

        return ChangeNarrative(
            narrative=narrative,
            deltas=deltas,
            current_period=current.isoformat(),
            previous_period=previous.isoformat(),
        )

    @staticmethod
    def _build_change_narrative_text(deltas: list[ChangeDelta]) -> str:
        """Fallback narrative when OpenRouter is not available."""
        parts = []
        for d in deltas:
            parts.append(
                f"{d.metric}: {float(d.current_value):,.0f} "
                f"({d.direction} {abs(float(d.change_pct)):.1f}%)"
            )
        return "Period comparison: " + "; ".join(parts) + "."
