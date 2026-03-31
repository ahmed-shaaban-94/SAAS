"""Report API endpoints — templated report generation.

Provides endpoints for listing templates, getting template details,
and rendering reports with user-supplied parameters.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.logging import get_logger
from datapulse.reports.models import RenderedReport, ReportTemplate
from datapulse.reports.template_engine import get_template, get_templates, render_report

log = get_logger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


class RenderRequest(BaseModel):
    """Request body for rendering a report."""

    parameters: dict[str, str | int | float] = Field(
        default_factory=dict, description="Template parameter values"
    )


@router.get("", response_model=list[ReportTemplate])
@limiter.limit("60/minute")
def list_templates(request: Request) -> list[ReportTemplate]:
    """List all available report templates."""
    return get_templates()


@router.get("/{template_id}", response_model=ReportTemplate)
@limiter.limit("60/minute")
def get_template_detail(request: Request, template_id: str) -> ReportTemplate:
    """Get a report template with its parameter definitions."""
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return template


@router.post("/{template_id}/render", response_model=RenderedReport)
@limiter.limit("20/minute")
def render_report_endpoint(
    request: Request,
    template_id: str,
    body: RenderRequest,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> RenderedReport:
    """Render a report with the supplied parameters."""
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    log.info("render_report", template_id=template_id, params=body.parameters)
    return render_report(template, body.parameters, session)
