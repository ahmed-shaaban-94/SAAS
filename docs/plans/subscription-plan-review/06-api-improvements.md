# Track 6 — API Improvements

> **Status**: PLANNED
> **Priority**: MEDIUM
> **Current State**: 79 endpoints, limit-based pagination (max 100), basic query params, no export, no advanced filtering

---

## Objective

Upgrade the API layer with **cursor-based pagination** for large datasets, an **advanced filtering DSL** for flexible queries, **data export** (CSV/Excel), **API versioning strategy**, and **OpenAPI documentation** — making the API enterprise-grade.

---

## Why This Matters

- Cursor pagination is the standard for modern APIs (Slack, Stripe, GitHub all use it)
- Data export is the #1 requested feature in any analytics product
- Advanced filtering shows understanding of API design beyond CRUD
- Good API documentation separates professional APIs from hobby projects
- Interviewers specifically ask about pagination strategies and their trade-offs

---

## Scope

- Cursor-based pagination with keyset approach
- Advanced filter DSL (field operators: eq, gt, lt, in, between, like)
- Data export endpoints (CSV, Excel) with streaming response
- Sorting API (multi-field, configurable direction)
- OpenAPI/Swagger documentation with examples
- Rate limiting refinements per endpoint tier
- 25+ tests

---

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Cursor pagination | Keyset-based pagination with `next_cursor` / `prev_cursor` tokens |
| Pagination response model | Standardized `PaginatedResponse[T]` wrapper |
| Filter DSL | Query parameter syntax: `?filter[field][op]=value` |
| Filter parser | Pydantic model that parses filter params into SQLAlchemy conditions |
| CSV export | `GET /api/v1/analytics/{entity}/export?format=csv` with streaming |
| Excel export | `GET /api/v1/analytics/{entity}/export?format=xlsx` with streaming |
| Multi-field sorting | `?sort=field1:asc,field2:desc` parameter |
| OpenAPI docs | Auto-generated Swagger UI at `/docs` with examples and descriptions |
| Versioning strategy | URL-based `/api/v1/` with deprecation headers for future `/api/v2/` |
| Tests | 25+ tests covering pagination, filtering, export, sorting |

---

## Technical Details

### Cursor-Based Pagination

```python
# src/datapulse/api/pagination.py

import base64
import json
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


def encode_cursor(values: dict) -> str:
    """Encode sort key values into an opaque cursor string."""
    return base64.urlsafe_b64encode(json.dumps(values).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode an opaque cursor string back to sort key values."""
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


class CursorPage(BaseModel, Generic[T]):
    """Standardized paginated response."""
    items: list[T]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool
    has_prev: bool
    total_count: int | None = None  # Optional, expensive for large tables


# Usage in endpoint:
# GET /api/v1/analytics/products/top?limit=20&cursor=eyJuZXRfc2FsZXMiOiAxMjM0NTZ9

# Keyset approach (faster than OFFSET for large datasets):
# SELECT * FROM agg_sales_by_product
# WHERE (net_sales, product_key) < (:last_net_sales, :last_product_key)
# ORDER BY net_sales DESC, product_key DESC
# LIMIT :limit + 1  -- fetch one extra to detect has_next
```

### Why Keyset > Offset

```
Offset pagination:  O(n) — database scans and discards n rows
Keyset pagination:  O(1) — database seeks directly to cursor position

Page 1:     Offset = 0ms,   Keyset = 0ms     (same)
Page 10:    Offset = 5ms,   Keyset = 0ms     (keyset wins)
Page 1000:  Offset = 500ms, Keyset = 0ms     (keyset dominates)
Page 10000: Offset = 5000ms, Keyset = 0ms    (offset unusable)
```

### Advanced Filter DSL

```python
# src/datapulse/api/filters.py

from enum import Enum
from typing import Any
from pydantic import BaseModel, field_validator
from sqlalchemy import Column, and_


class FilterOp(str, Enum):
    EQ = "eq"           # field = value
    NEQ = "neq"         # field != value
    GT = "gt"           # field > value
    GTE = "gte"         # field >= value
    LT = "lt"           # field < value
    LTE = "lte"         # field <= value
    IN = "in"           # field IN (v1, v2, v3)
    BETWEEN = "between" # field BETWEEN v1 AND v2
    LIKE = "like"       # field LIKE '%value%'
    IS_NULL = "is_null" # field IS NULL / IS NOT NULL


class FilterCondition(BaseModel):
    field: str
    op: FilterOp
    value: Any

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        """Whitelist allowed fields to prevent SQL injection."""
        ALLOWED_FIELDS = {
            "date", "category", "brand", "site_name", "staff_name",
            "customer_name", "net_sales", "quantity", "product_name",
            "billing_type", "return_rate", "revenue",
        }
        if v not in ALLOWED_FIELDS:
            raise ValueError(f"Field '{v}' not allowed. Allowed: {ALLOWED_FIELDS}")
        return v


def parse_filters(query_params: dict) -> list[FilterCondition]:
    """Parse URL query params into filter conditions.

    Format: ?filter[field][op]=value
    Examples:
        ?filter[net_sales][gte]=10000
        ?filter[category][in]=Pharma,OTC
        ?filter[date][between]=2024-01-01,2024-12-31
        ?filter[brand][like]=aspirin
    """
    filters = []
    for key, value in query_params.items():
        if not key.startswith("filter["):
            continue
        # Parse filter[field][op] format
        parts = key.replace("filter[", "").rstrip("]").split("][")
        if len(parts) == 2:
            field, op = parts
            filters.append(FilterCondition(field=field, op=FilterOp(op), value=value))
    return filters


def apply_filters(query, filters: list[FilterCondition], column_map: dict[str, Column]):
    """Apply parsed filters to SQLAlchemy query."""
    conditions = []
    for f in filters:
        col = column_map.get(f.field)
        if col is None:
            continue

        match f.op:
            case FilterOp.EQ:
                conditions.append(col == f.value)
            case FilterOp.NEQ:
                conditions.append(col != f.value)
            case FilterOp.GT:
                conditions.append(col > f.value)
            case FilterOp.GTE:
                conditions.append(col >= f.value)
            case FilterOp.LT:
                conditions.append(col < f.value)
            case FilterOp.LTE:
                conditions.append(col <= f.value)
            case FilterOp.IN:
                values = [v.strip() for v in f.value.split(",")]
                conditions.append(col.in_(values))
            case FilterOp.BETWEEN:
                low, high = f.value.split(",", 1)
                conditions.append(col.between(low.strip(), high.strip()))
            case FilterOp.LIKE:
                conditions.append(col.ilike(f"%{f.value}%"))
            case FilterOp.IS_NULL:
                if f.value.lower() == "true":
                    conditions.append(col.is_(None))
                else:
                    conditions.append(col.isnot(None))

    if conditions:
        query = query.where(and_(*conditions))
    return query
```

### Data Export (CSV/Excel)

```python
# src/datapulse/api/routes/export.py

import csv
import io
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/products")
async def export_products(
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    # ... same filters as analytics endpoints
):
    """Export product analytics data as CSV or Excel."""
    data = await analytics_service.get_products(filters)

    if format == "csv":
        return _stream_csv(data, filename="products_export.csv")
    else:
        return _stream_xlsx(data, filename="products_export.xlsx")


def _stream_csv(data: list[dict], filename: str) -> StreamingResponse:
    """Stream CSV response without loading entire file into memory."""
    def generate():
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
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
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _stream_xlsx(data: list[dict], filename: str) -> StreamingResponse:
    """Generate Excel file using openpyxl (streaming not possible, but chunked)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    if data:
        ws.append(list(data[0].keys()))
        for row in data:
            ws.append(list(row.values()))

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

### Multi-Field Sorting

```python
# src/datapulse/api/sorting.py

from dataclasses import dataclass
from sqlalchemy import asc, desc


@dataclass
class SortField:
    field: str
    direction: str  # "asc" or "desc"


def parse_sort(sort_param: str | None) -> list[SortField]:
    """Parse sort parameter: ?sort=net_sales:desc,customer_name:asc"""
    if not sort_param:
        return []
    fields = []
    for part in sort_param.split(","):
        if ":" in part:
            field, direction = part.split(":", 1)
            fields.append(SortField(field=field.strip(), direction=direction.strip()))
        else:
            fields.append(SortField(field=part.strip(), direction="asc"))
    return fields


def apply_sort(query, sort_fields: list[SortField], column_map: dict):
    """Apply multi-field sorting to SQLAlchemy query."""
    ALLOWED_FIELDS = set(column_map.keys())
    for sf in sort_fields:
        if sf.field not in ALLOWED_FIELDS:
            continue
        col = column_map[sf.field]
        order_fn = desc if sf.direction == "desc" else asc
        query = query.order_by(order_fn(col))
    return query
```

### OpenAPI Documentation Enhancement

```python
# src/datapulse/api/app.py — enhanced app factory

app = FastAPI(
    title="DataPulse Analytics API",
    description="""
    ## DataPulse — Business/Sales Analytics Platform

    ### Authentication
    All endpoints require a valid JWT token in the `Authorization: Bearer <token>` header.

    ### Pagination
    List endpoints support cursor-based pagination:
    - `limit`: Number of items per page (default: 20, max: 100)
    - `cursor`: Opaque cursor from previous response's `next_cursor`

    ### Filtering
    Use the filter DSL: `?filter[field][operator]=value`
    - Operators: eq, neq, gt, gte, lt, lte, in, between, like, is_null
    - Example: `?filter[net_sales][gte]=10000&filter[category][eq]=Pharma`

    ### Sorting
    Use the sort parameter: `?sort=field1:asc,field2:desc`

    ### Export
    Add `?format=csv` or `?format=xlsx` to export endpoints.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

### API Endpoints (New/Modified)

| Method | Path | Change |
|--------|------|--------|
| GET | `/api/v1/analytics/products/top` | Add cursor pagination + filter DSL + sort |
| GET | `/api/v1/analytics/customers/top` | Add cursor pagination + filter DSL + sort |
| GET | `/api/v1/analytics/staff/top` | Add cursor pagination + filter DSL + sort |
| GET | `/api/v1/export/products` | NEW: CSV/Excel export |
| GET | `/api/v1/export/customers` | NEW: CSV/Excel export |
| GET | `/api/v1/export/staff` | NEW: CSV/Excel export |
| GET | `/api/v1/export/sites` | NEW: CSV/Excel export |
| GET | `/api/v1/export/returns` | NEW: CSV/Excel export |
| GET | `/api/v1/export/daily-trends` | NEW: CSV/Excel export |
| GET | `/docs` | OpenAPI Swagger UI |
| GET | `/redoc` | ReDoc alternative docs |

---

## Module Structure

```
src/datapulse/api/
├── pagination.py          # NEW: cursor encode/decode, CursorPage model
├── filters.py             # NEW: FilterDSL parser + SQLAlchemy applier
├── sorting.py             # NEW: sort param parser + SQLAlchemy applier
├── routes/
│   ├── analytics.py       # MODIFIED: use cursor pagination + filters + sort
│   └── export.py          # NEW: CSV/Excel export endpoints
└── app.py                 # MODIFIED: enhanced OpenAPI metadata
```

---

## New Dependencies

| Package | Purpose |
|---------|---------|
| `openpyxl` | Excel file generation for XLSX export |

---

## Backward Compatibility

The existing `limit` parameter continues to work. Cursor pagination is **opt-in**: if no `cursor` param is provided, the endpoint returns results with offset-style (but includes `next_cursor` in response for clients ready to adopt).

```json
// Old response (still works):
[{"product": "A", "revenue": 1000}, ...]

// New response (opt-in via Accept header or query param):
{
    "items": [{"product": "A", "revenue": 1000}, ...],
    "next_cursor": "eyJuZXRfc2FsZXMiOiAxMjM0NTZ9",
    "has_next": true,
    "has_prev": false,
    "total_count": 17803
}
```

---

## Dependencies (Project)

- Existing analytics module
- Existing API routes
- Track 1 (Frontend Testing) — test the new pagination in E2E
