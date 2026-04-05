"""Dashboard layout persistence API."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import CurrentUser, get_tenant_session
from datapulse.api.limiter import limiter

router = APIRouter(
    prefix="/dashboard/layout",
    tags=["dashboard-layout"],
    dependencies=[Depends(get_current_user)],
)

SessionDep = Annotated[Session, Depends(get_tenant_session)]


@router.get("")
@limiter.limit("30/minute")
def get_layout(request: Request, session: SessionDep, user: CurrentUser):
    sql = text("SELECT layout FROM public.dashboard_layouts WHERE user_id = :uid")
    row = session.execute(sql, {"uid": user["sub"]}).scalar()
    return {"layout": row if row else []}


@router.put("")
@limiter.limit("10/minute")
def save_layout(request: Request, session: SessionDep, user: CurrentUser, body: dict):
    layout = body.get("layout", [])
    tenant_id = int(user.get("tenant_id", "1"))
    sql = text("""
        INSERT INTO public.dashboard_layouts (tenant_id, user_id, layout, updated_at)
        VALUES (:tid, :uid, :layout, now())
        ON CONFLICT (tenant_id, user_id) DO UPDATE SET layout = :layout, updated_at = now()
    """)
    session.execute(sql, {"tid": tenant_id, "uid": user["sub"], "layout": json.dumps(layout)})
    session.flush()
    return {"layout": layout}
