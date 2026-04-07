"""Tests for PDF report generator."""

import pytest

from datapulse.reports.pdf_generator import (
    _fmt,
    generate_dashboard_pdf,
    generate_report_pdf,
)


class TestFmt:
    def test_none(self):
        assert _fmt(None) == "—"

    def test_int(self):
        assert _fmt(1234) == "1,234"

    def test_float_large(self):
        assert _fmt(1234.5678) == "1,235"

    def test_float_small(self):
        assert _fmt(3.14) == "3.14"

    def test_string(self):
        assert _fmt("hello") == "hello"

    def test_zero(self):
        assert _fmt(0) == "0"


class TestGenerateReportPdf:
    def test_empty_sections(self):
        pdf = generate_report_pdf("Test Report", [])
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100
        assert pdf[:5] == b"%PDF-"

    def test_text_section(self):
        pdf = generate_report_pdf("Test", [
            {"type": "text", "title": "Intro", "text": "Hello world"},
        ])
        assert pdf[:5] == b"%PDF-"

    def test_kpi_section(self):
        pdf = generate_report_pdf("Test", [
            {
                "type": "kpi",
                "title": "KPIs",
                "kpis": [
                    {"label": "Revenue", "value": "1,000,000"},
                    {"label": "Orders", "value": "5,000"},
                ],
            },
        ])
        assert pdf[:5] == b"%PDF-"

    def test_table_section(self):
        pdf = generate_report_pdf("Test", [
            {
                "type": "table",
                "title": "Products",
                "headers": ["Name", "Revenue", "Qty"],
                "rows": [
                    ["Widget A", 50000, 100],
                    ["Widget B", 30000, 75],
                ],
            },
        ])
        assert pdf[:5] == b"%PDF-"

    def test_mixed_sections(self):
        pdf = generate_report_pdf("Full Report", [
            {"type": "text", "title": "Summary", "text": "Q1 2025 Report"},
            {
                "type": "kpi",
                "title": "Overview",
                "kpis": [
                    {"label": "Revenue", "value": "$1M"},
                    {"label": "Growth", "value": "+15%"},
                ],
            },
            {
                "type": "table",
                "title": "Details",
                "headers": ["Item", "Amount"],
                "rows": [["A", 100], ["B", 200]],
            },
        ])
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 500

    def test_empty_table(self):
        pdf = generate_report_pdf("Test", [
            {"type": "table", "title": "Empty", "headers": [], "rows": []},
        ])
        assert pdf[:5] == b"%PDF-"


class TestGenerateDashboardPdf:
    def test_with_all_data(self):
        pdf = generate_dashboard_pdf(
            summary={
                "total_revenue": 1000000,
                "total_orders": 5000,
                "avg_order_value": 200,
                "unique_customers": 1200,
                "revenue_growth_pct": 15.5,
            },
            top_products=[
                {"product_name": "Widget A", "total_revenue": 50000, "total_quantity": 100, "total_orders": 50},
                {"product_name": "Widget B", "total_revenue": 30000, "total_quantity": 75, "total_orders": 30},
            ],
            top_customers=[
                {"customer_name": "Acme Corp", "total_revenue": 80000, "total_orders": 40, "avg_order_value": 2000},
            ],
            top_staff=[
                {"staff_name": "Ahmed", "total_revenue": 120000, "total_orders": 60, "unique_customers": 25},
            ],
        )
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 1000

    def test_empty_data(self):
        pdf = generate_dashboard_pdf(
            summary={},
            top_products=[],
            top_customers=[],
            top_staff=[],
        )
        assert pdf[:5] == b"%PDF-"

    def test_partial_data(self):
        pdf = generate_dashboard_pdf(
            summary={"total_revenue": 500000},
            top_products=[{"material_name": "X", "revenue": 100}],
            top_customers=[],
            top_staff=[],
        )
        assert pdf[:5] == b"%PDF-"
