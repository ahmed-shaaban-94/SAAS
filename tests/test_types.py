"""Tests for shared types and validators."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from datapulse.types import JsonDecimal, validate_source_dir


class TestJsonDecimal:
    def test_serializes_as_float(self):
        class M(BaseModel):
            value: JsonDecimal

        m = M(value=Decimal("123.45"))
        data = m.model_dump()
        assert isinstance(data["value"], float)
        assert data["value"] == 123.45

    def test_json_output_is_number(self):
        class M(BaseModel):
            value: JsonDecimal

        m = M(value=Decimal("99.99"))
        json_str = m.model_dump_json()
        assert "99.99" in json_str
        # Should NOT be a string like "99.99"
        assert '"99.99"' not in json_str

    def test_zero_decimal(self):
        class M(BaseModel):
            value: JsonDecimal

        m = M(value=Decimal("0"))
        assert m.model_dump()["value"] == 0.0


class TestValidateSourceDir:
    def test_valid_path(self):
        result = validate_source_dir("/app/data/raw/sales")
        assert result == "/app/data/raw/sales"

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="must not contain"):
            validate_source_dir("/app/data/../etc/passwd")

    def test_rejects_outside_root(self):
        with pytest.raises(ValueError, match="must be inside"):
            validate_source_dir("/tmp/evil")

    def test_rejects_similar_prefix(self):
        """'/app/data_evil' starts with '/app/data' but is NOT inside it."""
        with pytest.raises(ValueError, match="must be inside"):
            validate_source_dir("/app/data_evil")

    def test_custom_allowed_root(self):
        result = validate_source_dir("/custom/root/sub", allowed_root="/custom/root")
        assert result == "/custom/root/sub"

    def test_exact_root_path(self):
        result = validate_source_dir("/app/data")
        assert result == "/app/data"
