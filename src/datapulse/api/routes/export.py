"""Data export endpoints (CSV/Excel).

Provides streaming CSV and Excel export for analytics data.
Uses streaming responses to avoid loading entire datasets into memory.
"""

from __future__ import annotations

import csv
import io
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from datapulse.analytics.service import AnalyticsService
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_analytics_service
from datapulse.logging import get_logger

log = get_logger(__name__)

router = APIRouter(
    prefix="/export",
    tags=["export"],
    dependencies=[Depends(get_current_user)],
)

ServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


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


@router.get("/products")
def export_products(
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    category: str | None = None,
    limit: int = 100,
) -> StreamingResponse:
    """Export top products data as CSV or Excel."""
    from datapulse.analytics.models import AnalyticsFilter

    f = AnalyticsFilter(
        date_range=(start_date, end_date) if start_date else None,
        category=category,
        limit=limit,
    )
    result = service.get_product_insights(f)
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "products", format)


@router.get("/customers")
def export_customers(
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> StreamingResponse:
    """Export top customers data as CSV or Excel."""
    from datapulse.analytics.models import AnalyticsFilter

    f = AnalyticsFilter(date_range=(start_date, end_date) if start_date else None, limit=limit)
    result = service.get_customer_insights(f)
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "customers", format)


@router.get("/staff")
def export_staff(
    service: ServiceDep,
    format: Annotated[str, Query(pattern="^(csv|xlsx)$")] = "csv",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> StreamingResponse:
    """Export staff performance data as CSV or Excel."""
    from datapulse.analytics.models import AnalyticsFilter

    f = AnalyticsFilter(date_range=(start_date, end_date) if start_date else None, limit=limit)
    result = service.get_staff_leaderboard(f)
    data = [item.model_dump() for item in result.items] if hasattr(result, "items") else []
    return _export_response(data, "staff", format)
