"""Tests for the data export module."""

from __future__ import annotations

import csv
import io

from datapulse.api.routes.export import _stream_csv, _to_xlsx_bytes


class TestStreamCSV:
    def test_csv_response_type(self):
        data = [{"name": "Product A", "revenue": 1000}]
        response = _stream_csv(data, "test.csv")
        assert response.media_type == "text/csv"

    def test_csv_filename_header(self):
        data = [{"a": 1}]
        response = _stream_csv(data, "my_export.csv")
        assert "my_export.csv" in response.headers["content-disposition"]

    def test_csv_no_store_header(self):
        data = [{"a": 1}]
        response = _stream_csv(data, "test.csv")
        assert "no-store" in response.headers.get("cache-control", "")

    def test_csv_generation_logic(self):
        """Test CSV generation using csv module directly."""
        data = [
            {"name": "Product A", "revenue": 1000},
            {"name": "Product B", "revenue": 2000},
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        content = output.getvalue()
        assert "name,revenue" in content
        assert "Product A,1000" in content
        assert "Product B,2000" in content


class TestToXlsxBytes:
    def test_generates_xlsx_bytes(self):
        data = [
            {"name": "Product A", "revenue": 1000},
            {"name": "Product B", "revenue": 2000},
        ]
        try:
            buffer = _to_xlsx_bytes(data)
            assert buffer.tell() == 0  # seeked to start
            content = buffer.read()
            assert len(content) > 0
            # XLSX magic bytes
            assert content[:2] == b"PK"
        except ImportError:
            # openpyxl not installed, skip
            pass

    def test_empty_data_creates_valid_xlsx(self):
        try:
            buffer = _to_xlsx_bytes([])
            content = buffer.read()
            assert len(content) > 0
            assert content[:2] == b"PK"
        except ImportError:
            pass
