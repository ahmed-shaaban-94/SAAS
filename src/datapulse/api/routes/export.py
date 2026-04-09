"""Data export endpoints (CSV/Excel).

Provides streaming CSV and Excel export for analytics data.
Uses streaming responses to avoid loading entire datasets into memory.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from datapulse.analytics.service import AnalyticsService
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_analytics_service
from datapulse.api.limiter import limiter
from datapulse.logging import get_logger

log = get_logger(__name__)

router = APIRouter(
    prefix="/export",
    tags=["export"],
    dependencies=[Depends(get_current_user)],
)

ServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


def _parse_date(value: str | None, name: str) -> date | None:
    """Parse a date string (YYYY-MM-DD) or raise 422."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {name}: expected YYYY-MM-DD format, got '{value}'",
        ) from exc


def _stream_csv(data: list[dict[str, Any]], filename: str) -> StreamingResponse:
    """Stream a CSV response without loading the entire file into memory."""

    def generate():
        if not data:
            yield ""
            return
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in data:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "private, no-store",
        },
    )


def _to_xlsx_bytes(data: list[dict[str, Any]], sheet_name: str = "Export") -> io.BytesIO:
    """Generate an Excel file in memory using openpyxl."""
    try:
        from openpyxl import Workbook
    except ImportError as err:
        raise ImportError(
            "openpyxl is required for Excel export. Install with: pip install openpyxl"
        ) from err

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    if data:
        headers = list(data[0].keys())
        ws.append(headers)
        for row in data:
            ws.append([row.get(h) for h in headers])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _stream_xlsx(data: list[dict[str, Any]], filename: str) -> StreamingResponse:
    """Generate and stream an Excel response."""
    buffer = _to_xlsx_bytes(data)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "private, no-store",
        },
    )


def _export_response(
    data: list[dict[str, Any]],
    entity: str,
    fmt: str,
) -> StreamingResponse:
    """Dispatch to CSV, Excel, or PDF export."""
    if fmt == "xlsx":
        return _stream_xlsx(data, f"{entity}_export.xlsx")
    if fmt == "pdf":
        return _stream_pdf_table(data, entity)
    return _stream_csv(data, f"{entity}_export.csv")


def _stream_pdf_table(data: list[dict[str, Any]], entity: str) -> StreamingResponse:
    """Generate a simple PDF table from data rows."""
    from datapulse.reports.pdf_generator import generate_report_pdf

    headers = list(data[0].keys()) if data else []
    rows = [[row.get(h) for h in headers] for row in data]
    pdf_bytes = generate_report_pdf(
        title=f"{entity.title()} Export",
        sections=[{"type": "table", "title": entity.title(), "headers": headers, "rows": rows}],
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={entity}_export.pdf",
            "Cache-Control": "private, no-store",
        },
    )


def _build_filter(
    start_date: str | None,
    end_date: str | None,
    limit: int,
    category: str | None = None,
):
    """Build an AnalyticsFilter with validated dates and bounded limit."""
    from datapulse.analytics.models import AnalyticsFilter, DateRange

    sd = _parse_date(start_date, "start_date")
    ed = _parse_date(end_date, "end_date")

    if (sd is None) != (ed is None):
        raise HTTPException(
            status_code=422,
            detail="Both start_date and end_date are required, or neither.",
        )

    if sd is not None and ed is not None and sd > ed:
        raise HTTPException(
            status_code=422,
            detail="start_date must be on or before end_date.",
        )

    dr = DateRange(start_date=sd, end_date=ed) if sd and ed else None
    return AnalyticsFilter(date_range=dr, category=category, limit=limit)


@router.get("/dashboard/pdf")
@limiter.limit("5/minute")
def export_dashboard_pdf(
    request: Request,
    service: ServiceDep,
    start_date: str | None = None,
    end_date: str | None = None,
) -> StreamingResponse:
    """Export the dashboard overview as a styled PDF report."""
    from datapulse.reports.pdf_generator import generate_dashboard_pdf

    f = _build_filter(start_date, end_date, 10)
    try:
        summary = service.get_dashboard_summary(f)
        products = service.get_product_insights(f)
        customers = service.get_customer_insights(f)
        staff = service.get_staff_leaderboard(f)
    except Exception as exc:
        log.error("export_dashboard_pdf_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate PDF.") from exc

    summary_dict = summary.model_dump() if hasattr(summary, "model_dump") else {}
    prod_list = [i.model_dump() for i in products.items] if hasattr(products, "items") else []
    cust_list = [i.model_dump() for i in customers.items] if hasattr(customers, "items") else []
    staff_list = [i.model_dump() for i in staff.items] if hasattr(staff, "items") else []

    pdf_bytes = generate_dashboard_pdf(summary_dict, prod_list, cust_list, staff_list)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=dashboard_report.pdf",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/products")
@limiter.limit("10/minute")
def export_products(
    request: Request,
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx|pdf)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100000)] = 10000,
) -> StreamingResponse:
    """Export top products data as CSV or Excel."""
    f = _build_filter(start_date, end_date, limit, category=category)
    try:
        result = service.get_product_insights(f)
    except Exception as exc:
        log.error("export_products_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate product export.") from exc
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "products", format)


@router.get("/customers")
@limiter.limit("10/minute")
def export_customers(
    request: Request,
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx|pdf)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100000)] = 10000,
) -> StreamingResponse:
    """Export top customers data as CSV or Excel."""
    f = _build_filter(start_date, end_date, limit)
    try:
        result = service.get_customer_insights(f)
    except Exception as exc:
        log.error("export_customers_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate customer export.") from exc
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "customers", format)


@router.get("/staff")
@limiter.limit("10/minute")
def export_staff(
    request: Request,
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx|pdf)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100000)] = 10000,
) -> StreamingResponse:
    """Export staff performance data as CSV or Excel."""
    f = _build_filter(start_date, end_date, limit)
    try:
        result = service.get_staff_leaderboard(f)
    except Exception as exc:
        log.error("export_staff_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate staff export.") from exc
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "staff", format)
