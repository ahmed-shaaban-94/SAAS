"""Business logic layer for targets and alerts."""

from __future__ import annotations

from datapulse.logging import get_logger
from datapulse.targets.models import (
    AlertConfigCreate,
    AlertConfigResponse,
    AlertLogResponse,
    BudgetSummary,
    TargetCreate,
    TargetResponse,
    TargetSummary,
)
from datapulse.targets.repository import TargetsRepository

log = get_logger(__name__)


class TargetsService:
    """Orchestrates target and alert operations."""

    def __init__(self, repo: TargetsRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------

    def create_target(self, data: TargetCreate) -> TargetResponse:
        """Create a new sales target."""
        log.info(
            "service_create_target",
            target_type=data.target_type,
            period=data.period,
        )
        return self._repo.create_target(data)

    def list_targets(
        self,
        target_type: str | None = None,
        granularity: str | None = None,
        period: str | None = None,
    ) -> list[TargetResponse]:
        """List targets with optional filters."""
        return self._repo.list_targets(
            target_type=target_type,
            granularity=granularity,
            period_prefix=period,
        )

    def delete_target(self, target_id: int) -> bool:
        """Delete a target by ID."""
        return self._repo.delete_target(target_id)

    def get_target_summary(self, year: int) -> TargetSummary:
        """Get target vs actual summary for a given year.

        Delegates to the repository which computes monthly comparisons
        and YTD totals.
        """
        log.info("service_target_summary", year=year)
        return self._repo.get_target_vs_actual(year)

    def get_budget_summary(self, year: int) -> BudgetSummary:
        """Get budget vs actual summary by origin for a given year."""
        log.info("service_budget_summary", year=year)
        return self._repo.get_budget_vs_actual(year)

    # ------------------------------------------------------------------
    # Alert configs
    # ------------------------------------------------------------------

    def list_alert_configs(self) -> list[AlertConfigResponse]:
        """Return all alert configurations."""
        return self._repo.list_alert_configs()

    def create_alert_config(self, data: AlertConfigCreate) -> AlertConfigResponse:
        """Create a new alert configuration."""
        log.info("service_create_alert_config", alert_name=data.alert_name)
        return self._repo.create_alert_config(data)

    def toggle_alert(self, alert_id: int, enabled: bool) -> AlertConfigResponse | None:
        """Enable or disable an alert configuration."""
        log.info("service_toggle_alert", alert_id=alert_id, enabled=enabled)
        return self._repo.update_alert_config(alert_id, enabled)

    # ------------------------------------------------------------------
    # Alert logs
    # ------------------------------------------------------------------

    def get_active_alerts(
        self, limit: int = 50, unacknowledged_only: bool = False
    ) -> list[AlertLogResponse]:
        """Return recent alert log entries."""
        return self._repo.list_alert_logs(
            limit=limit,
            unacknowledged_only=unacknowledged_only,
        )

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert log entry as acknowledged."""
        return self._repo.acknowledge_alert(alert_id)
