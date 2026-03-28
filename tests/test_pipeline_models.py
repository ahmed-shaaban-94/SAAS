"""Tests for pipeline Pydantic models."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from datapulse.pipeline.models import (
    VALID_STATUSES,
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
)


class TestPipelineRunCreate:
    def test_minimal(self):
        m = PipelineRunCreate(run_type="full_refresh")
        assert m.run_type == "full_refresh"
        assert m.trigger_source is None
        assert m.metadata == {}

    def test_full(self):
        m = PipelineRunCreate(
            run_type="incremental", trigger_source="n8n", metadata={"key": "val"},
        )
        assert m.trigger_source == "n8n"
        assert m.metadata == {"key": "val"}

    def test_frozen(self):
        m = PipelineRunCreate(run_type="full_refresh")
        with pytest.raises(Exception):
            m.run_type = "other"


class TestPipelineRunUpdate:
    def test_all_none(self):
        m = PipelineRunUpdate()
        assert m.status is None
        assert m.finished_at is None
        assert m.rows_loaded is None

    def test_partial(self):
        m = PipelineRunUpdate(status="running", rows_loaded=1000)
        assert m.status == "running"
        assert m.rows_loaded == 1000
        assert m.error_message is None

    def test_frozen(self):
        m = PipelineRunUpdate(status="running")
        with pytest.raises(Exception):
            m.status = "failed"


class TestPipelineRunResponse:
    def test_full_construction(self):
        now = datetime.now(timezone.utc)
        m = PipelineRunResponse(
            id=uuid4(), tenant_id=1, run_type="full_refresh",
            status="success", trigger_source="manual",
            started_at=now, finished_at=now,
            duration_seconds=Decimal("12.34"), rows_loaded=5000,
            error_message=None, metadata={"ai_summary": "ok"},
        )
        assert m.status == "success"
        assert m.rows_loaded == 5000

    def test_frozen(self):
        now = datetime.now(timezone.utc)
        m = PipelineRunResponse(
            id=uuid4(), tenant_id=1, run_type="x", status="pending",
            trigger_source=None, started_at=now, finished_at=None,
            duration_seconds=None, rows_loaded=None,
            error_message=None, metadata={},
        )
        with pytest.raises(Exception):
            m.status = "running"

    def test_json_decimal_serializes_as_float(self):
        now = datetime.now(timezone.utc)
        m = PipelineRunResponse(
            id=uuid4(), tenant_id=1, run_type="x", status="success",
            trigger_source=None, started_at=now, finished_at=now,
            duration_seconds=Decimal("45.67"), rows_loaded=100,
            error_message=None, metadata={},
        )
        data = m.model_dump()
        assert isinstance(data["duration_seconds"], float)
        assert data["duration_seconds"] == 45.67


class TestPipelineRunList:
    def test_empty(self):
        m = PipelineRunList(items=[], total=0, offset=0, limit=20)
        assert m.items == []
        assert m.total == 0

    def test_with_items(self):
        now = datetime.now(timezone.utc)
        item = PipelineRunResponse(
            id=uuid4(), tenant_id=1, run_type="x", status="success",
            trigger_source=None, started_at=now, finished_at=now,
            duration_seconds=Decimal("1.0"), rows_loaded=10,
            error_message=None, metadata={},
        )
        m = PipelineRunList(items=[item], total=1, offset=0, limit=20)
        assert len(m.items) == 1


class TestValidStatuses:
    def test_contains_all_expected(self):
        expected = {
            "pending", "running", "bronze_complete", "silver_complete",
            "gold_complete", "success", "failed",
        }
        assert VALID_STATUSES == expected

    def test_is_frozenset(self):
        assert isinstance(VALID_STATUSES, frozenset)
