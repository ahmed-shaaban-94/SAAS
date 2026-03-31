"""Report template engine — renders parameterized reports.

Substitutes parameters into SQL queries, executes them, and assembles
the results into a RenderedReport.
"""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.reports.models import (
    RenderedReport,
    RenderedSection,
    ReportTemplate,
    SectionType,
)

log = get_logger(__name__)

# Parameter substitution pattern: :param_name
_PARAM_PATTERN = re.compile(r":(\w+)")

# Built-in report templates
BUILTIN_TEMPLATES: list[ReportTemplate] = [
    ReportTemplate(
        id="monthly-overview",
        name="Monthly Sales Overview",
        description="Sales performance summary for a given month",
        parameters=[
            {"name": "year", "label": "Year", "param_type": "number", "default": 2025},
            {
                "name": "month",
                "label": "Month",
                "param_type": "select",
                "default": "1",
                "options": [str(i) for i in range(1, 13)],
            },
        ],
        sections=[
            {
                "section_type": "text",
                "title": "Report Period",
                "text": "Monthly overview for :year-:month",
            },
            {
                "section_type": "query",
                "title": "Monthly KPIs",
                "sql": """
                    SELECT total_net_amount, transaction_count, unique_customers,
                           unique_products, return_rate, mom_growth_pct, yoy_growth_pct
                    FROM public_marts.agg_sales_monthly
                    WHERE year = :year AND month = :month
                """,
                "chart_type": "table",
            },
            {
                "section_type": "query",
                "title": "Top 10 Products",
                "sql": """
                    SELECT drug_name, total_net_amount, transaction_count, unique_customers
                    FROM public_marts.agg_sales_by_product
                    WHERE year = :year AND month = :month
                    ORDER BY total_net_amount DESC
                    LIMIT 10
                """,
                "chart_type": "horizontal-bar",
            },
            {
                "section_type": "query",
                "title": "Top 10 Customers",
                "sql": """
                    SELECT customer_name, total_net_amount, transaction_count
                    FROM public_marts.agg_sales_by_customer
                    WHERE year = :year AND month = :month
                    ORDER BY total_net_amount DESC
                    LIMIT 10
                """,
                "chart_type": "bar",
            },
        ],
    ),
    ReportTemplate(
        id="product-deep-dive",
        name="Product Deep Dive",
        description="Detailed analysis of a specific product over time",
        parameters=[
            {"name": "drug_name", "label": "Product Name", "param_type": "text", "default": ""},
        ],
        sections=[
            {
                "section_type": "text",
                "title": "Product Analysis",
                "text": "Deep dive for product: :drug_name",
            },
            {
                "section_type": "query",
                "title": "Monthly Trend",
                "sql": """
                    SELECT year, month, month_name, total_net_amount,
                           transaction_count, unique_customers, return_rate
                    FROM public_marts.agg_sales_by_product
                    WHERE drug_name ILIKE :drug_name
                    ORDER BY year, month
                """,
                "chart_type": "line",
            },
        ],
    ),
    ReportTemplate(
        id="returns-analysis",
        name="Returns Analysis",
        description="Top returns by product and customer",
        parameters=[
            {"name": "year", "label": "Year", "param_type": "number", "default": 2025},
        ],
        sections=[
            {
                "section_type": "query",
                "title": "Top Returns by Product",
                "sql": """
                    SELECT drug_name, SUM(return_amount) as total_return_amount,
                           SUM(return_count) as total_returns
                    FROM public_marts.agg_returns
                    WHERE year = :year
                    GROUP BY drug_name
                    ORDER BY total_return_amount DESC
                    LIMIT 15
                """,
                "chart_type": "horizontal-bar",
            },
            {
                "section_type": "query",
                "title": "Top Returns by Customer",
                "sql": """
                    SELECT customer_name, SUM(return_amount) as total_return_amount,
                           SUM(return_count) as total_returns
                    FROM public_marts.agg_returns
                    WHERE year = :year
                    GROUP BY customer_name
                    ORDER BY total_return_amount DESC
                    LIMIT 15
                """,
                "chart_type": "bar",
            },
        ],
    ),
]


def get_templates() -> list[ReportTemplate]:
    """Return all available report templates."""
    return BUILTIN_TEMPLATES


def get_template(template_id: str) -> ReportTemplate | None:
    """Return a template by ID."""
    for t in BUILTIN_TEMPLATES:
        if t.id == template_id:
            return t
    return None


def render_report(
    template: ReportTemplate,
    params: dict[str, str | int | float],
    session: Session,
) -> RenderedReport:
    """Execute a report template with the given parameters.

    Substitutes :param_name placeholders in SQL and text sections,
    executes queries, and assembles the rendered report.
    """
    rendered_sections: list[RenderedSection] = []

    for section in template.sections:
        if section.section_type == SectionType.text:
            # Substitute params in text
            rendered_text = section.text
            for key, value in params.items():
                rendered_text = rendered_text.replace(f":{key}", str(value))

            rendered_sections.append(
                RenderedSection(
                    section_type=SectionType.text,
                    title=section.title,
                    text=rendered_text,
                )
            )

        elif section.section_type in (SectionType.query, SectionType.kpi):
            try:
                result = session.execute(text(section.sql), params)
                columns = list(result.keys())
                rows = [[_serialise(v) for v in row] for row in result]

                rendered_sections.append(
                    RenderedSection(
                        section_type=section.section_type,
                        title=section.title,
                        columns=columns,
                        rows=rows,
                        row_count=len(rows),
                        chart_type=section.chart_type,
                    )
                )
            except Exception as exc:
                log.error(
                    "report_section_failed",
                    title=section.title,
                    error=str(exc),
                )
                rendered_sections.append(
                    RenderedSection(
                        section_type=SectionType.text,
                        title=section.title,
                        text=f"Error executing query: {exc}",
                    )
                )

    return RenderedReport(
        template_id=template.id,
        template_name=template.name,
        parameters=params,
        sections=rendered_sections,
    )


def _serialise(value) -> str | int | float | bool | None:
    """Convert a DB value to a JSON-safe primitive."""
    if value is None:
        return None
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)
