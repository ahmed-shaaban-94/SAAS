"""Control Center — shared dependency factories."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from datapulse.api.deps import get_tenant_session
from datapulse.control_center.repository import (
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
    SyncScheduleRepository,
)
from datapulse.control_center.service import ControlCenterService


def get_control_center_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ControlCenterService:
    return ControlCenterService(
        session,
        connections=SourceConnectionRepository(session),
        profiles=PipelineProfileRepository(session),
        mappings=MappingTemplateRepository(session),
        releases=PipelineReleaseRepository(session),
        sync_jobs=SyncJobRepository(session),
        drafts=PipelineDraftRepository(session),
        schedules=SyncScheduleRepository(session),
    )


ServiceDep = Annotated[ControlCenterService, Depends(get_control_center_service)]
