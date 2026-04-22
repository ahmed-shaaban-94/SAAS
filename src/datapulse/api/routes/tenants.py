"""Tenant settings API endpoints (#604 Spec 1 PR 4)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.core.auth import CurrentUser

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantPatch(BaseModel):
    locale: str | None = None
    currency: Literal["USD", "EGP"] | None = None


@router.patch("/me")
@limiter.limit("5/minute")
def patch_tenant(
    request: Request,
    body: TenantPatch,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> dict:
    """Update locale and/or currency for the calling tenant."""
    updates: list[str] = []
    params: dict[str, str | int] = {"tid": int(user["tenant_id"])}
    if body.locale is not None:
        updates.append("locale = :locale")
        params["locale"] = body.locale
    if body.currency is not None:
        updates.append("currency = :currency")
        params["currency"] = body.currency
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    session.execute(
        text(f"UPDATE bronze.tenants SET {', '.join(updates)} WHERE tenant_id = :tid"),
        params,
    )
    session.commit()
    return {"updated": list(body.model_dump(exclude_unset=True).keys())}
