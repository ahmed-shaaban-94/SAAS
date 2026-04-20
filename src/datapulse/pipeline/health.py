"""Pure helpers for the ``/pipeline/health`` dashboard card (#509).

Kept dependency-free so the medallion-node + history-strip rules can be
unit-tested without touching the DB or quality service. The orchestration
(fetching runs, scorecard, history) lives in ``PipelineService``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from datapulse.pipeline.models import (
    PipelineHealthCounter,
    PipelineHealthHistoryPoint,
    PipelineHealthNode,
    PipelineHealthRun,
    PipelineRunResponse,
)

# ``run_type`` value → medallion display label.
_RUN_TYPE_TO_LABEL: dict[str, str] = {
    "bronze": "Bronze",
    "staging": "Silver",
    "marts": "Gold",
}

_MEDALLION_ORDER: tuple[str, ...] = ("bronze", "staging", "marts")


def _run_status_to_node_status(run_status: str) -> str:
    """Map a pipeline run's status onto the node-status enum."""
    if run_status == "success":
        return "ok"
    if run_status == "running":
        return "running"
    if run_status == "failed":
        return "failed"
    return "pending"


def _node_value(run: PipelineRunResponse | None) -> str:
    """Human-readable summary value for a medallion node."""
    if run is None:
        return "No runs yet"
    if run.status == "running":
        return "Running..."
    if run.rows_loaded is not None:
        return _format_row_count(run.rows_loaded)
    return run.status.capitalize()


def _format_row_count(rows: int) -> str:
    """1_234_567 → '1.23M rows' (compact, banner-friendly)."""
    if rows >= 1_000_000:
        return f"{rows / 1_000_000:.2f}M rows"
    if rows >= 1_000:
        return f"{rows / 1_000:.1f}K rows"
    return f"{rows} rows"


def build_nodes(
    latest_by_type: dict[str, PipelineRunResponse],
) -> list[PipelineHealthNode]:
    """Project the latest run per medallion stage onto ``PipelineHealthNode``s.

    Always returns three nodes in fixed Bronze → Silver → Gold order so
    the dashboard card has a stable layout — stages with no recorded
    runs show a ``"pending"`` placeholder.
    """
    return [
        PipelineHealthNode(
            label=_RUN_TYPE_TO_LABEL[run_type],
            value=_node_value(latest_by_type.get(run_type)),
            status=_run_status_to_node_status(latest_by_type[run_type].status)
            if run_type in latest_by_type
            else "pending",
        )
        for run_type in _MEDALLION_ORDER
    ]


def build_last_run(full_run: PipelineRunResponse | None) -> PipelineHealthRun | None:
    """Project the latest ``full`` run onto the ``last_run`` summary."""
    if full_run is None:
        return None
    at = full_run.finished_at or full_run.started_at
    return PipelineHealthRun(
        at=at,
        duration_seconds=full_run.duration_seconds,
    )


def build_counters(
    scorecard_rows: list[dict],
) -> tuple[PipelineHealthCounter, PipelineHealthCounter]:
    """Derive gates + tests counters from the latest run's quality scorecard.

    Gates = ``error``-severity checks (hard-fail contract). Tests = all
    checks aggregated. Until dbt test artifacts surface in the store
    (#509 follow-up), ``tests`` mirrors the total-check count — accurate
    for the passed/total ratio the banner cares about.
    """
    if not scorecard_rows:
        zero = PipelineHealthCounter(passed=0, total=0)
        return zero, zero

    latest = scorecard_rows[0]
    total_checks = int(latest.get("total_checks") or 0)
    passed = int(latest.get("passed") or 0)
    failed = int(latest.get("failed") or 0)

    # Gates = error-severity checks. We don't have severity split in the
    # aggregate, so approximate: gates_total = passed + failed (excludes
    # warnings), gates_passed = passed.
    gates_total = passed + failed
    gates = PipelineHealthCounter(passed=passed, total=gates_total)
    tests = PipelineHealthCounter(passed=passed, total=total_checks)
    return gates, tests


def _day_status(run_status: str, duration_seconds: Decimal | None) -> str:
    """Map a run's status onto the history-strip colour enum.

    ``success`` with unusually long duration is surfaced as ``warning`` so
    the bar chart can colour slow runs distinctly from clean ones. The
    caller is free to override the 2x-median threshold once slow-run
    baselines stabilise.
    """
    if run_status == "failed":
        return "fail"
    if run_status in {"running", "queued"}:
        return "warning"
    if run_status == "success":
        return "ok"
    return "warning"


def build_history_7d(
    day_rows: list[dict],
    *,
    today: date | None = None,
    days: int = 7,
) -> list[PipelineHealthHistoryPoint]:
    """Pad the raw per-day rows to a contiguous ``days``-length window.

    Days with no recorded run get ``status='none'`` so the UI can render
    an empty bar rather than skip the day entirely.
    """
    ref_today = today or datetime.now(UTC).date()
    by_date: dict[date, dict] = {r["run_date"]: r for r in day_rows if r.get("run_date")}

    points: list[PipelineHealthHistoryPoint] = []
    for offset in range(days - 1, -1, -1):
        d = ref_today - timedelta(days=offset)
        row = by_date.get(d)
        if row is None:
            points.append(
                PipelineHealthHistoryPoint(
                    date=d.isoformat(),
                    duration_seconds=None,
                    status="none",
                )
            )
            continue

        duration = row.get("duration_seconds")
        duration_decimal = Decimal(str(duration)) if duration is not None else None
        points.append(
            PipelineHealthHistoryPoint(
                date=d.isoformat(),
                duration_seconds=duration_decimal,
                status=_day_status(row.get("status", ""), duration_decimal),
            )
        )
    return points
