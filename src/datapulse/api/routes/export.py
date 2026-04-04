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
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {name}: expected YYYY-MM-DD format, got '{value}'",
        )


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
    """Dispatch to CSV or Excel export."""
    if fmt == "xlsx":
        return _stream_xlsx(data, f"{entity}_export.xlsx")
    return _stream_csv(data, f"{entity}_export.csv")


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


@router.get("/products")
@limiter.limit("10/minute")
def export_products(
    request: Request,
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 100,
) -> StreamingResponse:
    """Export top products data as CSV or Excel."""
    f = _build_filter(start_date, end_date, limit, category=category)
    try:
        result = service.get_product_insights(f)
    except Exception as exc:
        log.error("export_products_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate product export.")
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "products", format)


@router.get("/customers")
@limiter.limit("10/minute")
def export_customers(
    request: Request,
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 100,
) -> StreamingResponse:
    """Export top customers data as CSV or Excel."""
    f = _build_filter(start_date, end_date, limit)
    try:
        result = service.get_customer_insights(f)
    except Exception as exc:
        log.error("export_customers_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate customer export.")
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "customers", format)


@router.get("/staff")
@limiter.limit("10/minute")
def export_staff(
    request: Request,
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: Annotated[int, Query(ge=1, le=10000)] = 100,
) -> StreamingResponse:
    """Export staff performance data as CSV or Excel."""
    f = _build_filter(start_date, end_date, limit)
    try:
        result = service.get_staff_leaderboard(f)
    except Exception as exc:
        log.error("export_staff_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate staff export.")
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "staff", format)
