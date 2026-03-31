"""Tests for column type detection."""

import polars as pl

from datapulse.import_pipeline.models import DetectedType
from datapulse.import_pipeline.type_detector import detect_column_types


class TestDetectColumnTypes:
    def test_detects_integer(self):
        df = pl.DataFrame({"count": [1, 2, 3, 4, 5]})
        cols = detect_column_types(df)
        assert cols[0].detected_type == DetectedType.INTEGER

    def test_detects_float(self):
        df = pl.DataFrame({"price": [1.5, 2.0, 3.75]})
        cols = detect_column_types(df)
        assert cols[0].detected_type == DetectedType.FLOAT

    def test_detects_string(self):
        df = pl.DataFrame({"name": ["Alice", "Bob", "Charlie"]})
        cols = detect_column_types(df)
        assert cols[0].detected_type == DetectedType.STRING

    def test_detects_boolean(self):
        df = pl.DataFrame({"active": [True, False, True]})
        cols = detect_column_types(df)
        assert cols[0].detected_type == DetectedType.BOOLEAN

    def test_counts_nulls(self):
        df = pl.DataFrame({"value": [1, None, 3, None, 5]})
        cols = detect_column_types(df)
        assert cols[0].null_count == 2

    def test_counts_unique(self):
        df = pl.DataFrame({"category": ["A", "B", "A", "C", "B"]})
        cols = detect_column_types(df)
        assert cols[0].unique_count == 3

    def test_sample_values(self):
        df = pl.DataFrame({"name": ["Alice", "Bob", "Charlie", "Diana", "Eve"]})
        cols = detect_column_types(df, sample_values_count=3)
        assert len(cols[0].sample_values) == 3
        assert cols[0].sample_values[0] == "Alice"

    def test_multiple_columns(self):
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
                "score": [1.5, 2.5, 3.5],
            }
        )
        cols = detect_column_types(df)
        assert len(cols) == 3
        types = {c.name: c.detected_type for c in cols}
        assert types["id"] == DetectedType.INTEGER
        assert types["name"] == DetectedType.STRING
        assert types["score"] == DetectedType.FLOAT
