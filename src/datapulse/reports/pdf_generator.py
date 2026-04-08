"""PDF report generator using reportlab.

Generates professional PDF reports from analytics data with
tables, KPI summaries, and styled headers.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand colors
_ACCENT = colors.HexColor("#4F46E5")
_ACCENT_LIGHT = colors.HexColor("#E0E7FF")
_GRAY_50 = colors.HexColor("#F9FAFB")
_GRAY_200 = colors.HexColor("#E5E7EB")
_GRAY_700 = colors.HexColor("#374151")
_WHITE = colors.white


def _styles():
    ss = getSampleStyleSheet()
    ss.add(
        ParagraphStyle(
            "ReportTitle",
            parent=ss["Title"],
            fontSize=22,
            textColor=_ACCENT,
            spaceAfter=4 * mm,
        )
    )
    ss.add(
        ParagraphStyle(
            "SectionHeading",
            parent=ss["Heading2"],
            fontSize=14,
            textColor=_GRAY_700,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
        )
    )
    ss.add(
        ParagraphStyle(
            "SubText",
            parent=ss["Normal"],
            fontSize=9,
            textColor=colors.gray,
        )
    )
    ss.add(
        ParagraphStyle(
            "KPIValue",
            parent=ss["Normal"],
            fontSize=16,
            textColor=_ACCENT,
            alignment=1,  # center
        )
    )
    ss.add(
        ParagraphStyle(
            "KPILabel",
            parent=ss["Normal"],
            fontSize=8,
            textColor=colors.gray,
            alignment=1,
        )
    )
    return ss


def _build_table(headers: list[str], rows: list[list[str]], col_widths=None) -> Table:
    """Build a styled table with alternating row colors."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 1, _ACCENT),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, _GRAY_200),
        ("LINEBELOW", (0, -1), (-1, -1), 1, _GRAY_200),
        # Alignment
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    # Alternating rows
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), _GRAY_50))
    t.setStyle(TableStyle(style))
    return t


def _build_kpi_row(kpis: list[dict[str, str]]) -> Table:
    """Build a horizontal KPI cards row."""
    if not kpis:
        return Spacer(1, 0)

    ss = _styles()
    cells = []
    for kpi in kpis[:6]:  # max 6 KPIs
        cells.append(
            [
                Paragraph(str(kpi.get("value", "")), ss["KPIValue"]),
                Paragraph(str(kpi.get("label", "")), ss["KPILabel"]),
            ]
        )

    # Transpose to rows
    data = [
        [c[0] for c in cells],
        [c[1] for c in cells],
    ]
    col_w = (A4[0] - 4 * cm) / len(cells)
    t = Table(data, colWidths=[col_w] * len(cells))
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, _GRAY_200),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.5, _GRAY_200),
                ("BACKGROUND", (0, 0), (-1, -1), _ACCENT_LIGHT),
            ]
        )
    )
    return t


def _fmt(val: Any) -> str:
    """Format a value for display in PDF."""
    if val is None:
        return "—"
    if isinstance(val, float):
        if abs(val) >= 1000:
            return f"{val:,.0f}"
        return f"{val:,.2f}"
    if isinstance(val, int):
        return f"{val:,}"
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    return str(val)


def generate_report_pdf(
    title: str,
    sections: list[dict[str, Any]],
    generated_at: str | None = None,
) -> bytes:
    """Generate a PDF report.

    Args:
        title: Report title.
        sections: List of section dicts, each with:
            - type: "kpi" | "table" | "text"
            - title: Section heading
            - For "kpi": kpis: [{label, value}, ...]
            - For "table": headers: [str], rows: [[str]]
            - For "text": text: str
        generated_at: Timestamp string for the header.

    Returns:
        PDF content as bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    ss = _styles()
    story: list = []

    # Title
    story.append(Paragraph(title, ss["ReportTitle"]))
    ts = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"Generated: {ts}", ss["SubText"]))
    story.append(Spacer(1, 6 * mm))

    for section in sections:
        sec_type = section.get("type", "text")
        sec_title = section.get("title", "")

        if sec_title:
            story.append(Paragraph(sec_title, ss["SectionHeading"]))

        if sec_type == "kpi":
            kpis = section.get("kpis", [])
            story.append(_build_kpi_row(kpis))
            story.append(Spacer(1, 4 * mm))

        elif sec_type == "table":
            headers = section.get("headers", [])
            raw_rows = section.get("rows", [])
            rows = [[_fmt(c) for c in row] for row in raw_rows]
            if headers and rows:
                avail = A4[0] - 4 * cm
                col_w = avail / max(len(headers), 1)
                t = _build_table(headers, rows, col_widths=[col_w] * len(headers))
                story.append(t)
                story.append(Spacer(1, 4 * mm))

        elif sec_type == "text":
            txt = section.get("text", "")
            if txt:
                story.append(Paragraph(txt, ss["Normal"]))
                story.append(Spacer(1, 3 * mm))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def generate_dashboard_pdf(
    summary: dict[str, Any],
    top_products: list[dict],
    top_customers: list[dict],
    top_staff: list[dict],
) -> bytes:
    """Generate a dashboard overview PDF with KPIs and top-N tables."""
    sections = []

    # KPI Summary
    if summary:
        sections.append(
            {
                "type": "kpi",
                "title": "Key Performance Indicators",
                "kpis": [
                    {"label": "Total Revenue", "value": _fmt(summary.get("total_revenue"))},
                    {"label": "Total Orders", "value": _fmt(summary.get("total_orders"))},
                    {"label": "Avg Order Value", "value": _fmt(summary.get("avg_order_value"))},
                    {"label": "Unique Customers", "value": _fmt(summary.get("unique_customers"))},
                    {"label": "Growth %", "value": _fmt(summary.get("revenue_growth_pct"))},
                ],
            }
        )

    # Top Products
    if top_products:
        sections.append(
            {
                "type": "table",
                "title": f"Top {len(top_products)} Products",
                "headers": ["Product", "Revenue", "Quantity", "Orders"],
                "rows": [
                    [
                        p.get("product_name", p.get("material_name", ""))[:40],
                        p.get("total_revenue", p.get("revenue", 0)),
                        p.get("total_quantity", p.get("quantity", 0)),
                        p.get("total_orders", p.get("orders", 0)),
                    ]
                    for p in top_products[:20]
                ],
            }
        )

    # Top Customers
    if top_customers:
        sections.append(
            {
                "type": "table",
                "title": f"Top {len(top_customers)} Customers",
                "headers": ["Customer", "Revenue", "Orders", "Avg Order"],
                "rows": [
                    [
                        c.get("customer_name", c.get("customer", ""))[:40],
                        c.get("total_revenue", c.get("revenue", 0)),
                        c.get("total_orders", c.get("orders", 0)),
                        c.get("avg_order_value", c.get("avg_order", 0)),
                    ]
                    for c in top_customers[:20]
                ],
            }
        )

    # Top Staff
    if top_staff:
        sections.append(
            {
                "type": "table",
                "title": f"Top {len(top_staff)} Staff",
                "headers": ["Staff", "Revenue", "Orders", "Customers"],
                "rows": [
                    [
                        s.get("staff_name", s.get("salesperson", ""))[:40],
                        s.get("total_revenue", s.get("revenue", 0)),
                        s.get("total_orders", s.get("orders", 0)),
                        s.get("unique_customers", s.get("customers", 0)),
                    ]
                    for s in top_staff[:20]
                ],
            }
        )

    return generate_report_pdf("DataPulse Sales Report", sections)
