"""Tests for the reports module — models and template engine."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.reports.models import (
    ParameterType,
    RenderedReport,
    RenderedSection,
    ReportParameter,
    ReportSection,
    ReportTemplate,
    SectionType,
)
from datapulse.reports.template_engine import (
    BUILTIN_TEMPLATES,
    _serialise,
    get_template,
    get_templates,
    render_report,
)

# ---------------------------------------------------------------------------
# 1. ParameterType enum values
# ---------------------------------------------------------------------------


class TestParameterType:
    def test_values(self):
        assert ParameterType.text == "text"
        assert ParameterType.number == "number"
        assert ParameterType.date == "date"
        assert ParameterType.select == "select"

    def test_member_count(self):
        assert len(ParameterType) == 4


# ---------------------------------------------------------------------------
# 2. SectionType enum values
# ---------------------------------------------------------------------------


class TestSectionType:
    def test_values(self):
        assert SectionType.text == "text"
        assert SectionType.query == "query"
        assert SectionType.kpi == "kpi"

    def test_member_count(self):
        assert len(SectionType) == 3


# ---------------------------------------------------------------------------
# 3-4. ReportParameter creation
# ---------------------------------------------------------------------------


class TestReportParameter:
    def test_creation_all_fields(self):
        param = ReportParameter(
            name="year",
            label="Year",
            param_type=ParameterType.number,
            default=2025,
            required=True,
        )
        assert param.name == "year"
        assert param.label == "Year"
        assert param.param_type == ParameterType.number
        assert param.default == 2025
        assert param.required is True
        assert param.options == []

    def test_select_with_options(self):
        param = ReportParameter(
            name="month",
            label="Month",
            param_type=ParameterType.select,
            default="1",
            options=["1", "2", "3"],
        )
        assert param.param_type == ParameterType.select
        assert param.options == ["1", "2", "3"]
        assert param.default == "1"

    def test_defaults(self):
        param = ReportParameter(
            name="q",
            label="Search",
            param_type=ParameterType.text,
        )
        assert param.default is None
        assert param.options == []
        assert param.required is True


# ---------------------------------------------------------------------------
# 5. ReportSection creation
# ---------------------------------------------------------------------------


class TestReportSection:
    def test_text_section(self):
        section = ReportSection(
            section_type=SectionType.text,
            title="Intro",
            text="Hello :name",
        )
        assert section.section_type == SectionType.text
        assert section.title == "Intro"
        assert section.text == "Hello :name"
        assert section.sql == ""
        assert section.chart_type == "table"

    def test_query_section(self):
        section = ReportSection(
            section_type=SectionType.query,
            title="Sales",
            sql="SELECT * FROM sales",
            chart_type="bar",
        )
        assert section.section_type == SectionType.query
        assert section.sql == "SELECT * FROM sales"
        assert section.chart_type == "bar"


# ---------------------------------------------------------------------------
# 6. ReportTemplate creation
# ---------------------------------------------------------------------------


class TestReportTemplate:
    def test_creation_with_parameters_and_sections(self):
        param = ReportParameter(
            name="year",
            label="Year",
            param_type=ParameterType.number,
            default=2025,
        )
        section = ReportSection(
            section_type=SectionType.text,
            title="Period",
            text="Year: :year",
        )
        template = ReportTemplate(
            id="test-report",
            name="Test Report",
            description="A test report",
            parameters=[param],
            sections=[section],
        )
        assert template.id == "test-report"
        assert template.name == "Test Report"
        assert template.description == "A test report"
        assert len(template.parameters) == 1
        assert len(template.sections) == 1

    def test_defaults(self):
        template = ReportTemplate(id="empty", name="Empty")
        assert template.description == ""
        assert template.parameters == []
        assert template.sections == []


# ---------------------------------------------------------------------------
# 7. RenderedSection creation
# ---------------------------------------------------------------------------


class TestRenderedSection:
    def test_creation_with_columns_and_rows(self):
        rs = RenderedSection(
            section_type=SectionType.query,
            title="Results",
            columns=["name", "value"],
            rows=[["A", 100], ["B", 200]],
            row_count=2,
            chart_type="bar",
        )
        assert rs.columns == ["name", "value"]
        assert rs.rows == [["A", 100], ["B", 200]]
        assert rs.row_count == 2
        assert rs.chart_type == "bar"

    def test_defaults(self):
        rs = RenderedSection(section_type=SectionType.text)
        assert rs.title == ""
        assert rs.text == ""
        assert rs.columns == []
        assert rs.rows == []
        assert rs.row_count == 0
        assert rs.chart_type == "table"


# ---------------------------------------------------------------------------
# 8. RenderedReport creation
# ---------------------------------------------------------------------------


class TestRenderedReport:
    def test_creation(self):
        section = RenderedSection(
            section_type=SectionType.text,
            title="Hi",
            text="Hello world",
        )
        report = RenderedReport(
            template_id="test",
            template_name="Test Report",
            parameters={"year": 2025},
            sections=[section],
        )
        assert report.template_id == "test"
        assert report.template_name == "Test Report"
        assert report.parameters == {"year": 2025}
        assert len(report.sections) == 1

    def test_defaults(self):
        report = RenderedReport(template_id="x", template_name="X")
        assert report.parameters == {}
        assert report.sections == []


# ---------------------------------------------------------------------------
# 9-11. get_templates / get_template
# ---------------------------------------------------------------------------


class TestGetTemplates:
    def test_returns_list(self):
        templates = get_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert all(isinstance(t, ReportTemplate) for t in templates)

    def test_get_template_monthly_overview(self):
        t = get_template("monthly-overview")
        assert t is not None
        assert t.id == "monthly-overview"
        assert t.name == "Monthly Sales Overview"

    def test_get_template_nonexistent_returns_none(self):
        assert get_template("nonexistent") is None


# ---------------------------------------------------------------------------
# 12-14. render_report
# ---------------------------------------------------------------------------


def _make_mock_session(columns, rows):
    """Create a mock session whose execute() returns columns and rows."""
    mock_result = MagicMock()
    mock_result.keys.return_value = columns
    mock_result.__iter__ = MagicMock(return_value=iter(rows))

    session = MagicMock()
    session.execute.return_value = mock_result
    return session


class TestRenderReport:
    def test_text_section_substitutes_parameters(self):
        template = ReportTemplate(
            id="t",
            name="T",
            sections=[
                ReportSection(
                    section_type=SectionType.text,
                    title="Period",
                    text="Report for :year-:month",
                ),
            ],
        )
        session = MagicMock()
        report = render_report(template, {"year": 2025, "month": 3}, session)

        assert len(report.sections) == 1
        assert report.sections[0].section_type == SectionType.text
        assert report.sections[0].text == "Report for 2025-3"

    def test_query_section_executes_sql(self):
        session = _make_mock_session(
            columns=["name", "amount"],
            rows=[("Widget", Decimal("99.50")), ("Gadget", Decimal("200"))],
        )
        template = ReportTemplate(
            id="t",
            name="T",
            sections=[
                ReportSection(
                    section_type=SectionType.query,
                    title="Top Items",
                    sql="SELECT name, amount FROM items WHERE year = :year",
                    chart_type="bar",
                ),
            ],
        )
        report = render_report(template, {"year": 2025}, session)

        section = report.sections[0]
        assert section.section_type == SectionType.query
        assert section.columns == ["name", "amount"]
        assert section.rows == [["Widget", 99.50], ["Gadget", 200.0]]
        assert section.row_count == 2
        assert section.chart_type == "bar"
        session.execute.assert_called_once()

    def test_query_error_handled_gracefully(self):
        session = MagicMock()
        session.execute.side_effect = RuntimeError("DB connection lost")

        template = ReportTemplate(
            id="t",
            name="T",
            sections=[
                ReportSection(
                    section_type=SectionType.query,
                    title="Broken",
                    sql="SELECT 1",
                ),
            ],
        )
        report = render_report(template, {}, session)

        section = report.sections[0]
        # Error sections are rendered as text type
        assert section.section_type == SectionType.text
        assert "Error executing report section" in section.text
        # Error details should NOT be exposed to the client
        assert "DB connection lost" not in section.text

    def test_kpi_section_executes_like_query(self):
        session = _make_mock_session(
            columns=["total"],
            rows=[(Decimal("1000"),)],
        )
        template = ReportTemplate(
            id="t",
            name="T",
            sections=[
                ReportSection(
                    section_type=SectionType.kpi,
                    title="KPI",
                    sql="SELECT SUM(amount) as total FROM sales",
                ),
            ],
        )
        report = render_report(template, {}, session)
        assert report.sections[0].section_type == SectionType.kpi
        assert report.sections[0].rows == [[1000.0]]

    def test_report_metadata(self):
        template = ReportTemplate(id="my-id", name="My Report")
        session = MagicMock()
        report = render_report(template, {"x": 1}, session)
        assert report.template_id == "my-id"
        assert report.template_name == "My Report"
        assert report.parameters == {"x": 1}


# ---------------------------------------------------------------------------
# 15-19. _serialise
# ---------------------------------------------------------------------------


class TestSerialise:
    def test_decimal_to_float(self):
        assert _serialise(Decimal("3.14")) == pytest.approx(3.14)
        assert isinstance(_serialise(Decimal("3.14")), float)

    def test_datetime_to_isoformat(self):
        dt = datetime(2025, 6, 15, 10, 30, 0)
        assert _serialise(dt) == "2025-06-15T10:30:00"

    def test_date_to_isoformat(self):
        d = date(2025, 6, 15)
        assert _serialise(d) == "2025-06-15"

    def test_none_returns_none(self):
        assert _serialise(None) is None

    def test_int_passthrough(self):
        assert _serialise(42) == 42
        assert isinstance(_serialise(42), int)

    def test_float_passthrough(self):
        assert _serialise(3.14) == pytest.approx(3.14)
        assert isinstance(_serialise(3.14), float)

    def test_str_passthrough(self):
        assert _serialise("hello") == "hello"

    def test_bool_passthrough(self):
        assert _serialise(True) is True
        assert _serialise(False) is False

    def test_unknown_type_falls_back_to_str(self):
        assert _serialise([1, 2, 3]) == "[1, 2, 3]"


# ---------------------------------------------------------------------------
# 20. BUILTIN_TEMPLATES has expected template IDs
# ---------------------------------------------------------------------------


class TestBuiltinTemplates:
    def test_expected_ids(self):
        ids = {t.id for t in BUILTIN_TEMPLATES}
        assert "monthly-overview" in ids
        assert "product-deep-dive" in ids
        assert "returns-analysis" in ids

    def test_all_are_report_templates(self):
        assert all(isinstance(t, ReportTemplate) for t in BUILTIN_TEMPLATES)

    def test_count(self):
        assert len(BUILTIN_TEMPLATES) == 3
