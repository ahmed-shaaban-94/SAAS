"""POS clinical panel routes — drug detail, cross-sell, alternatives (#623).

Sub-router for ``pos.py`` facade. Every endpoint is tenant-scoped via RLS
(the POS router already requires an authenticated user) and returns an empty
array rather than 404 when no suggestions exist — the frontend relies on that
contract to hide the card cleanly instead of handling an error state.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request

from datapulse.api.limiter import limiter
from datapulse.api.routes._pos_routes_deps import (
    CurrentUser,
    ServiceDep,
)
from datapulse.pos.models.clinical import (
    AlternativeItem,
    CrossSellItem,
    DrugDetail,
)

router = APIRouter()


@router.get(
    "/drugs/{drug_code}",
    response_model=DrugDetail,
    summary="Drug detail including clinical metadata",
)
@limiter.limit("120/minute")
def get_drug_detail(
    request: Request,
    drug_code: Annotated[str, Path(min_length=1, max_length=100)],
    service: ServiceDep,
    user: CurrentUser,
) -> DrugDetail:
    """Return drug detail (dim_product + POS-owned clinical metadata).

    404 when the drug_code is unknown in ``dim_product``; 200 with
    ``counseling_text=null`` when the drug exists but has no clinical entry.
    """
    _ = user
    detail = service.get_drug_detail(drug_code)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Drug {drug_code!r} not found")
    return detail


@router.get(
    "/drugs/{drug_code}/cross-sell",
    response_model=list[CrossSellItem],
    summary="AI cross-sell recommendations for a drug",
)
@limiter.limit("120/minute")
def get_cross_sell(
    request: Request,
    drug_code: Annotated[str, Path(min_length=1, max_length=100)],
    service: ServiceDep,
    user: CurrentUser,
) -> list[CrossSellItem]:
    """Return cross-sell recommendations for a primary drug.

    Empty array (not 404) when the drug has no configured suggestions — the
    clinical panel card stays hidden client-side.
    """
    _ = user
    return service.get_cross_sell(drug_code)


@router.get(
    "/drugs/{drug_code}/alternatives",
    response_model=list[AlternativeItem],
    summary="Generic alternatives with savings for a drug",
)
@limiter.limit("120/minute")
def get_alternatives(
    request: Request,
    drug_code: Annotated[str, Path(min_length=1, max_length=100)],
    service: ServiceDep,
    user: CurrentUser,
) -> list[AlternativeItem]:
    """Return generics that share the same ``active_ingredient`` and cost less.

    Empty array (not 404) when the drug has no active ingredient on file or
    when no cheaper alternatives exist.
    """
    _ = user
    return service.get_alternatives(drug_code)
