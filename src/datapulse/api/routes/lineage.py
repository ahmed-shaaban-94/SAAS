"""Data lineage API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.lineage.models import LineageGraph
from datapulse.lineage.parser import get_model_lineage, parse_lineage

router = APIRouter(
    prefix="/lineage",
    tags=["lineage"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/graph", response_model=LineageGraph)
@limiter.limit("10/minute")
def get_full_lineage(request: Request) -> LineageGraph:
    """Full dbt model lineage graph."""
    return parse_lineage()


@router.get("/graph/{model_name}", response_model=LineageGraph)
@limiter.limit("10/minute")
def get_model_graph(request: Request, model_name: str) -> LineageGraph:
    """Upstream and downstream lineage for a specific model."""
    return get_model_lineage(model_name)
