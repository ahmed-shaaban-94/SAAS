---
name: add-analytics-endpoint
description: "Scaffold a complete analytics endpoint: Pydantic model → repository method → service (cached) → API route → test. Usage: /add-analytics-endpoint <name> <description>"
---

You are adding a new analytics endpoint to DataPulse. This creates 5 files/changes in order.

## Input
Parse the user's request for:
- **Endpoint name** (e.g., `top-brands`, `revenue-by-region`)
- **What it returns** (ranking, time series, summary, detail)
- **Which marts table(s)** to query

## Steps

### 1. Pydantic Response Model
Edit `src/datapulse/analytics/models.py` — add a frozen model:

```python
class <Name>Result(BaseModel):
    model_config = ConfigDict(frozen=True)
    # Use JsonDecimal for money, int for counts, str for names
```

### 2. Repository Method
Choose the right repository based on query type:
- Core rankings/trends → `repository.py`
- Detail pages → `detail_repository.py`
- Breakdowns → `breakdown_repository.py`
- Comparisons → `comparison_repository.py`
- Hierarchy → `hierarchy_repository.py`
- Advanced (ABC, movers, heatmap) → `advanced_repository.py`

Add method with **parameterized SQL**:
```python
def get_<name>(self, start_date: date, end_date: date, ...) -> <Name>Result:
    sql = text("""
        SELECT ...
        FROM public_marts.<table>
        WHERE month_start BETWEEN :start_date AND :end_date
    """)
    rows = self.session.execute(sql, {"start_date": start_date, "end_date": end_date}).mappings().all()
    return <Name>Result(items=[...])
```

Rules:
- **Always use `text()` with `:param`** — never f-strings for values
- **Whitelist table/column names** if dynamic
- Query `public_marts.*` tables only

### 3. Service Method (with caching)
Edit `src/datapulse/analytics/service.py`:

```python
@cached(ttl=600, prefix="datapulse:analytics:<name>")
def get_<name>(self, *, start_date=None, end_date=None, limit=10):
    dr = self._resolve_date_range(start_date, end_date)
    return self.<repo>.get_<name>(dr.start_date, dr.end_date, limit=limit)
```

### 4. API Route
Edit `src/datapulse/api/routes/analytics.py`:

```python
@router.get("/<url-path>")
@limiter.limit("60/minute")
async def get_<name>(
    request: Request,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=10, ge=1, le=100),
):
    return service.get_<name>(start_date=start_date, end_date=end_date, limit=limit)
```

### 5. Test
Create or append to `tests/test_analytics_endpoints.py`:

```python
def test_get_<name>_success(client, mock_analytics_service):
    mock_analytics_service.get_<name>.return_value = <Name>Result(...)
    response = client.get("/api/v1/analytics/<url-path>")
    assert response.status_code == 200

def test_get_<name>_with_dates(client, mock_analytics_service):
    mock_analytics_service.get_<name>.return_value = <Name>Result(...)
    response = client.get("/api/v1/analytics/<url-path>?start_date=2024-01-01&end_date=2024-06-30")
    assert response.status_code == 200
```

### 6. Verify
```bash
cd /home/user/SAAS && python -m pytest tests/test_analytics_endpoints.py -v -k "<name>"
```

### 7. Report
Show:
- All files modified
- Endpoint: `GET /api/v1/analytics/<path>`
- Response shape
- Test results
- Remind user to add frontend hook if needed
