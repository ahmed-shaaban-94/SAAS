"""Unit tests for the pipeline-health composite (#509).

Tests the pure builders exhaustively, plus a service-level orchestration
test proving the ``PipelineService.get_health_summary`` fan-out.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec
from uuid import UUID

from datapulse.pipeline.health import (
    build_counters,
    build_history_7d,
    build_last_run,
    build_nodes,
)
from datapulse.pipeline.models import PipelineRunResponse
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService

# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────


_DEFAULT_FINISH = datetime(2026, 4, 20, 4, 7, tzinfo=UTC)
_FINISH_UNSET: datetime = datetime(1900, 1, 1, tzinfo=UTC)  # sentinel


def _run(
    run_type: str,
    status: str = "success",
    *,
    rows_loaded: int | None = 1_000_000,
    duration: Decimal | None = Decimal("420.5"),
    started_at: datetime | None = None,
    finished_at: datetime | None = _FINISH_UNSET,
) -> PipelineRunResponse:
    start = started_at or datetime(2026, 4, 20, 4, 0, tzinfo=UTC)
    finish = _DEFAULT_FINISH if finished_at is _FINISH_UNSET else finished_at
    return PipelineRunResponse(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=1,
        run_type=run_type,
        status=status,
        trigger_source="test",
        started_at=start,
        finished_at=finish,
        duration_seconds=duration,
        rows_loaded=rows_loaded,
        error_message=None,
        metadata={},
    )


# ────────────────────────────────────────────────────────────────────────
# build_nodes
# ────────────────────────────────────────────────────────────────────────


def test_nodes_emits_three_in_bronze_silver_gold_order():
    latest = {
        "bronze": _run("bronze"),
        "staging": _run("staging"),
        "marts": _run("marts"),
    }
    nodes = build_nodes(latest)
    assert [n.label for n in nodes] == ["Bronze", "Silver", "Gold"]


def test_nodes_formats_row_counts_compactly():
    latest = {
        "bronze": _run("bronze", rows_loaded=1_230_000),
        "staging": _run("staging", rows_loaded=45_000),
        "marts": _run("marts", rows_loaded=47),
    }
    nodes = build_nodes(latest)
    assert nodes[0].value == "1.23M rows"
    assert nodes[1].value == "45.0K rows"
    assert nodes[2].value == "47 rows"


def test_nodes_use_running_placeholder_when_stage_in_flight():
    latest = {"bronze": _run("bronze", status="running", rows_loaded=None)}
    nodes = build_nodes(latest)
    assert nodes[0].value == "Running..."
    assert nodes[0].status == "running"


def test_nodes_missing_stage_shows_pending_placeholder():
    """A stage with no recorded run must still appear (fixed layout)."""
    nodes = build_nodes({})
    assert [n.status for n in nodes] == ["pending", "pending", "pending"]
    assert all(n.value == "No runs yet" for n in nodes)


def test_nodes_failed_run_surfaced_as_failed_status():
    nodes = build_nodes({"bronze": _run("bronze", status="failed", rows_loaded=None)})
    assert nodes[0].status == "failed"


# ────────────────────────────────────────────────────────────────────────
# build_last_run
# ────────────────────────────────────────────────────────────────────────


def test_last_run_none_when_no_full_run():
    assert build_last_run(None) is None


def test_last_run_prefers_finished_at_when_present():
    run = _run("full")
    summary = build_last_run(run)
    assert summary is not None
    assert summary.at == run.finished_at
    assert summary.duration_seconds == Decimal("420.5")


def test_last_run_falls_back_to_started_at_when_still_running():
    run = _run("full", status="running", finished_at=None, duration=None)
    summary = build_last_run(run)
    assert summary is not None
    assert summary.at == run.started_at
    assert summary.duration_seconds is None


# ────────────────────────────────────────────────────────────────────────
# build_counters
# ────────────────────────────────────────────────────────────────────────


def test_counters_empty_when_no_scorecard_rows():
    gates, tests = build_counters([])
    assert gates.passed == 0
    assert gates.total == 0
    assert tests.passed == 0
    assert tests.total == 0


def test_counters_derives_gates_and_tests_from_latest_scorecard():
    rows = [
        {"total_checks": 50, "passed": 47, "failed": 2, "warned": 1},
    ]
    gates, tests = build_counters(rows)
    # gates = passed + failed (errors only, excludes warnings)
    assert gates.passed == 47
    assert gates.total == 49
    # tests = all checks
    assert tests.passed == 47
    assert tests.total == 50


# ────────────────────────────────────────────────────────────────────────
# build_history_7d
# ────────────────────────────────────────────────────────────────────────


_TODAY = date(2026, 4, 20)


def test_history_returns_exactly_seven_points():
    history = build_history_7d([], today=_TODAY)
    assert len(history) == 7


def test_history_pads_missing_days_with_none_status():
    history = build_history_7d([], today=_TODAY)
    assert all(p.status == "none" for p in history)
    assert all(p.duration_seconds is None for p in history)


def test_history_orders_oldest_to_newest():
    history = build_history_7d([], today=_TODAY)
    assert history[0].date == "2026-04-14"
    assert history[-1].date == "2026-04-20"


def test_history_maps_success_to_ok_and_failed_to_fail():
    rows = [
        {
            "run_date": _TODAY,
            "status": "success",
            "duration_seconds": Decimal("380.0"),
        },
        {
            "run_date": _TODAY - timedelta(days=1),
            "status": "failed",
            "duration_seconds": Decimal("120.0"),
        },
    ]
    history = build_history_7d(rows, today=_TODAY)
    by_date = {p.date: p for p in history}
    assert by_date["2026-04-20"].status == "ok"
    assert by_date["2026-04-20"].duration_seconds == Decimal("380.0")
    assert by_date["2026-04-19"].status == "fail"


def test_history_running_status_maps_to_warning():
    rows = [{"run_date": _TODAY, "status": "running", "duration_seconds": None}]
    history = build_history_7d(rows, today=_TODAY)
    by_date = {p.date: p for p in history}
    assert by_date["2026-04-20"].status == "warning"


# ────────────────────────────────────────────────────────────────────────
# Service orchestration
# ────────────────────────────────────────────────────────────────────────


def test_service_composes_health_from_repos():
    repo = create_autospec(PipelineRepository, instance=True)
    repo.get_latest_run_per_type.return_value = {
        "bronze": _run("bronze", rows_loaded=1_130_000),
        "staging": _run("staging", status="running", rows_loaded=None),
        "marts": _run("marts", rows_loaded=47),
    }
    repo.get_latest_run.return_value = _run("full")
    repo.get_recent_days_summary.return_value = [
        {
            "run_date": _TODAY,
            "status": "success",
            "duration_seconds": Decimal("420.5"),
        },
    ]

    quality_repo = create_autospec(QualityRepository, instance=True)
    quality_repo.get_scorecard.return_value = [
        {"total_checks": 50, "passed": 47, "failed": 3, "warned": 0},
    ]

    service = PipelineService(repo=repo, quality_repo=quality_repo)
    health = service.get_health_summary()

    # Three medallion nodes, right labels
    assert [n.label for n in health.nodes] == ["Bronze", "Silver", "Gold"]
    # last_run pointer populated from full run
    assert health.last_run is not None
    # counters reflect latest scorecard row
    assert health.gates.passed == 47
    assert health.tests.total == 50
    # history_7d is always 7 long
    assert len(health.history_7d) == 7
    # next_run_at is a known gap (scheduler not queryable yet)
    assert health.next_run_at is None


def test_service_tolerates_missing_quality_repo():
    """Pipeline health must not crash when quality data is unavailable."""
    repo = create_autospec(PipelineRepository, instance=True)
    repo.get_latest_run_per_type.return_value = {}
    repo.get_latest_run.return_value = None
    repo.get_recent_days_summary.return_value = []

    service = PipelineService(repo=repo, quality_repo=None)
    health = service.get_health_summary()

    assert health.gates.total == 0
    assert health.tests.total == 0


def test_service_tolerates_quality_repo_failure():
    """A broken quality repo degrades to zero counters, not a 500."""
    repo = create_autospec(PipelineRepository, instance=True)
    repo.get_latest_run_per_type.return_value = {}
    repo.get_latest_run.return_value = None
    repo.get_recent_days_summary.return_value = []

    quality_repo = MagicMock()
    quality_repo.get_scorecard.side_effect = RuntimeError("db down")

    service = PipelineService(repo=repo, quality_repo=quality_repo)
    health = service.get_health_summary()

    assert health.gates.total == 0
    assert health.tests.total == 0
