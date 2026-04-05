"""Global search API endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from datapulse.analytics.search_repository import SearchRepository
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter

router = APIRouter(
    prefix="/search",
    tags=["search"],
    dependencies=[Depends(get_current_user)],
)


def get_search_repo(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> SearchRepository:
    return SearchRepository(session)


RepoDep = Annotated[SearchRepository, Depends(get_search_repo)]


_PAGES = [
    {"name": "Overview", "path": "/dashboard"},
    {"name": "Goals", "path": "/goals"},
    {"name": "Custom Report", "path": "/custom-report"},
    {"name": "Products", "path": "/products"},
    {"name": "Customers", "path": "/customers"},
    {"name": "Staff", "path": "/staff"},
    {"name": "Sites", "path": "/sites"},
    {"name": "Returns", "path": "/returns"},
    {"name": "Reports", "path": "/reports"},
    {"name": "Pipeline", "path": "/pipeline"},
    {"name": "Alerts", "path": "/alerts"},
    {"name": "Insights", "path": "/insights"},
    {"name": "Billing", "path": "/billing"},
]


def _search_pages(query: str) -> list[dict]:
    q_lower = query.lower()
    return [
        {"name": p["name"], "path": p["path"], "type": "page"}
        for p in _PAGES
        if q_lower in p["name"].lower()
    ]


@router.get("")
@limiter.limit("60/minute")
def search(
    request: Request,
    repo: RepoDep,
    q: str = Query("", min_length=0, max_length=200),
    limit: int = Query(10, ge=1, le=50),
):
    """Search across products, customers, and staff."""
    if not q.strip():
        return {"products": [], "customers": [], "staff": [], "pages": []}

    results = repo.search(q.strip(), limit)
    results["pages"] = _search_pages(q.strip())
    return results
