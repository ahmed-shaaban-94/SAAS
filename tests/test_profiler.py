"""Tests for the data profiler module."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from datapulse.pipeline.profiler import (
    _STAGE_TABLE,
    ColumnProfile,
    TableProfile,
    profile_table,
)


class TestColumnProfile:
    def test_frozen(self):
        cp = ColumnProfile(
            column_name="test",
            data_type="integer",
            total_rows=100,
            null_count=5,
            null_rate=5.0,
            unique_count=50,
            cardinality=0.5,
        )
        with pytest.raises(AttributeError):
            cp.column_name = "modified"  # type: ignore

    def test_default_values(self):
        cp = ColumnProfile(
            column_name="col",
            data_type="text",
            total_rows=10,
            null_count=0,
            null_rate=0.0,
            unique_count=10,
            cardinality=1.0,
        )
        assert cp.min_value is None
        assert cp.max_value is None
        assert cp.mean is None
        assert cp.stddev is None
        assert cp.most_common == []


class TestTableProfile:
    def test_frozen(self):
        tp = TableProfile(
            schema_name="bronze",
            table_name="sales",
            row_count=1000,
            column_count=5,
            columns=[],
            profiled_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            tp.row_count = 2000  # type: ignore


class TestStageTable:
    def test_has_bronze(self):
        assert "bronze" in _STAGE_TABLE
        assert _STAGE_TABLE["bronze"] == ("bronze", "sales")

    def test_has_silver(self):
        assert "silver" in _STAGE_TABLE
        assert _STAGE_TABLE["silver"] == ("public_staging", "stg_sales")

    def test_has_gold(self):
        assert "gold" in _STAGE_TABLE


class TestProfileTable:
    def test_raises_for_unknown_stage(self):
        session = MagicMock()
        with pytest.raises(ValueError, match="Unknown stage"):
            profile_table(session, "unknown_stage")

    def test_returns_table_profile(self):
        session = MagicMock()
        # row count
        session.execute.return_value.scalar_one.return_value = 100
        # column metadata
        col_meta_row = MagicMock()
        col_meta_row._mapping = {"column_name": "net_sales", "data_type": "numeric"}
        session.execute.return_value.fetchall.side_effect = [
            [col_meta_row],  # column metadata
            [],  # most_common values
        ]
        # stats: null_count, unique_count
        stats_row = MagicMock()
        stats_row._mapping = {"null_count": 5, "unique_count": 80}
        # numeric stats: min, max, avg, stddev
        num_row = MagicMock()
        num_row.__getitem__ = lambda self, i: ["0", "1000", 500.0, 200.0][i]

        # Complex mock setup for multiple execute calls
        execute_results = []

        # 1st call: row count
        row_count_result = MagicMock()
        row_count_result.scalar_one.return_value = 100
        execute_results.append(row_count_result)

        # 2nd call: column metadata
        col_meta_result = MagicMock()
        col_meta_result.fetchall.return_value = [col_meta_row]
        execute_results.append(col_meta_result)

        # 3rd call: null/unique stats
        stats_result = MagicMock()
        stats_result.fetchone.return_value = stats_row
        execute_results.append(stats_result)

        # 4th call: numeric stats
        num_result = MagicMock()
        num_result.fetchone.return_value = num_row
        execute_results.append(num_result)

        # 5th call: most common
        mc_result = MagicMock()
        mc_result.fetchall.return_value = []
        execute_results.append(mc_result)

        session.execute.side_effect = execute_results

        profile = profile_table(session, "bronze")

        assert profile.schema_name == "bronze"
        assert profile.table_name == "sales"
        assert profile.row_count == 100
        assert len(profile.columns) == 1
        assert profile.columns[0].column_name == "net_sales"
