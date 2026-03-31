"""Tests for datapulse.tasks.models module."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from datapulse.tasks.models import QueryResponse, QueryResult, QueryStatus, QuerySubmit

# ---------------------------------------------------------------------------
# QueryStatus
# ---------------------------------------------------------------------------


class TestQueryStatus:
    """Tests for the QueryStatus StrEnum."""

    def test_has_all_four_members(self) -> None:
        assert len(QueryStatus) == 4

    @pytest.mark.parametrize(
        ("member", "expected"),
        [
            (QueryStatus.pending, "pending"),
            (QueryStatus.running, "running"),
            (QueryStatus.complete, "complete"),
            (QueryStatus.failed, "failed"),
        ],
    )
    def test_values_are_correct_strings(self, member: QueryStatus, expected: str) -> None:
        assert member.value == expected
        assert str(member) == expected


# ---------------------------------------------------------------------------
# QuerySubmit
# ---------------------------------------------------------------------------


class TestQuerySubmit:
    """Tests for the QuerySubmit model."""

    def test_accepts_valid_sql(self) -> None:
        qs = QuerySubmit(sql="SELECT 1")
        assert qs.sql == "SELECT 1"

    def test_rejects_empty_sql(self) -> None:
        with pytest.raises(ValidationError, match="sql"):
            QuerySubmit(sql="")

    def test_default_row_limit(self) -> None:
        qs = QuerySubmit(sql="SELECT 1")
        assert qs.row_limit == 10_000

    def test_custom_row_limit(self) -> None:
        qs = QuerySubmit(sql="SELECT 1", row_limit=500)
        assert qs.row_limit == 500

    def test_rejects_row_limit_below_one(self) -> None:
        with pytest.raises(ValidationError, match="row_limit"):
            QuerySubmit(sql="SELECT 1", row_limit=0)

    def test_rejects_row_limit_above_max(self) -> None:
        with pytest.raises(ValidationError, match="row_limit"):
            QuerySubmit(sql="SELECT 1", row_limit=100_001)

    def test_rejects_sql_exceeding_max_length(self) -> None:
        with pytest.raises(ValidationError, match="sql"):
            QuerySubmit(sql="X" * 10_001)

    def test_accepts_sql_at_max_length(self) -> None:
        qs = QuerySubmit(sql="X" * 10_000)
        assert len(qs.sql) == 10_000

    def test_accepts_row_limit_boundary_values(self) -> None:
        low = QuerySubmit(sql="SELECT 1", row_limit=1)
        high = QuerySubmit(sql="SELECT 1", row_limit=100_000)
        assert low.row_limit == 1
        assert high.row_limit == 100_000


# ---------------------------------------------------------------------------
# QueryResponse
# ---------------------------------------------------------------------------


class TestQueryResponse:
    """Tests for the QueryResponse model."""

    def test_creation_with_all_required_fields(self) -> None:
        now = datetime.now(tz=UTC)
        resp = QueryResponse(
            query_id="abc-123",
            status=QueryStatus.pending,
            submitted_at=now,
        )
        assert resp.query_id == "abc-123"
        assert resp.status == QueryStatus.pending
        assert resp.submitted_at == now

    def test_rejects_missing_fields(self) -> None:
        with pytest.raises(ValidationError):
            QueryResponse()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# QueryResult
# ---------------------------------------------------------------------------


class TestQueryResult:
    """Tests for the QueryResult model."""

    @pytest.fixture()
    def _now(self) -> datetime:
        return datetime.now(tz=UTC)

    def test_minimal_creation(self, _now: datetime) -> None:
        result = QueryResult(
            query_id="q-1",
            status=QueryStatus.complete,
            submitted_at=_now,
        )
        assert result.query_id == "q-1"
        assert result.status == QueryStatus.complete
        assert result.submitted_at == _now

    def test_defaults(self, _now: datetime) -> None:
        result = QueryResult(
            query_id="q-1",
            status=QueryStatus.complete,
            submitted_at=_now,
        )
        assert result.completed_at is None
        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.truncated is False
        assert result.duration_ms is None
        assert result.error is None

    def test_creation_with_all_optional_fields(self, _now: datetime) -> None:
        completed = datetime.now(tz=UTC)
        result = QueryResult(
            query_id="q-2",
            status=QueryStatus.complete,
            submitted_at=_now,
            completed_at=completed,
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
            truncated=True,
            duration_ms=42.5,
            error="partial timeout",
        )
        assert result.completed_at == completed
        assert result.columns == ["id", "name"]
        assert result.rows == [[1, "Alice"], [2, "Bob"]]
        assert result.row_count == 2
        assert result.truncated is True
        assert result.duration_ms == 42.5
        assert result.error == "partial timeout"

    def test_failed_result_with_error(self, _now: datetime) -> None:
        result = QueryResult(
            query_id="q-err",
            status=QueryStatus.failed,
            submitted_at=_now,
            error="syntax error at position 5",
        )
        assert result.status == QueryStatus.failed
        assert result.error == "syntax error at position 5"
