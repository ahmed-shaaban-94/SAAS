"""Release policy helpers for staged POS desktop updates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from datapulse.pos.models import (
    DesktopUpdatePolicyResponse,
    DesktopUpdateReleaseRequest,
    DesktopUpdateReleaseResponse,
)


@dataclass(frozen=True)
class CandidateRelease:
    release_id: int
    version: str
    channel: str
    platform: str
    rollout_scope: str
    active: bool
    release_notes: str | None
    min_schema_version: int | None
    max_schema_version: int | None
    min_app_version: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    target_tenant_ids: frozenset[int]


def _version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Small semver-ish sorter that keeps unknown suffixes deterministic."""

    parts: list[tuple[int, int | str]] = []
    for chunk in version.replace("-", ".").split("."):
        if chunk.isdigit():
            parts.append((0, int(chunk)))
        elif chunk:
            parts.append((1, chunk))
    return tuple(parts)


def _version_gt(left: str, right: str) -> bool:
    return _version_key(left) > _version_key(right)


def select_update_policy(
    releases: Iterable[CandidateRelease],
    *,
    tenant_id: int,
    current_version: str,
    now: datetime | None = None,
) -> DesktopUpdatePolicyResponse:
    """Pick the newest release this tenant is allowed to install."""

    now = now or datetime.now(UTC)
    eligible: list[CandidateRelease] = []

    for release in releases:
        if not release.active:
            continue
        if release.rollout_scope == "paused":
            continue
        if release.starts_at is not None and release.starts_at > now:
            continue
        if release.ends_at is not None and release.ends_at <= now:
            continue
        if not _version_gt(release.version, current_version):
            continue
        if release.rollout_scope == "selected" and tenant_id not in release.target_tenant_ids:
            continue
        eligible.append(release)

    if not eligible:
        return DesktopUpdatePolicyResponse(
            update_available=False,
            allowed=False,
            reason="no_allowed_update",
        )

    selected = max(eligible, key=lambda rel: _version_key(rel.version))
    return DesktopUpdatePolicyResponse(
        update_available=True,
        allowed=True,
        reason="allowed",
        version=selected.version,
        channel=selected.channel,
        platform=selected.platform,
        release_id=selected.release_id,
        rollout_scope=selected.rollout_scope,  # type: ignore[arg-type]
        release_notes=selected.release_notes,
    )


def _candidate_from_mapping(row: Mapping[str, Any] | RowMapping) -> CandidateRelease:
    targets = row.get("target_tenant_ids") or []
    return CandidateRelease(
        release_id=int(row["release_id"]),
        version=str(row["version"]),
        channel=str(row["channel"]),
        platform=str(row["platform"]),
        rollout_scope=str(row["rollout_scope"]),
        active=bool(row["active"]),
        release_notes=row.get("release_notes"),
        min_schema_version=row.get("min_schema_version"),
        max_schema_version=row.get("max_schema_version"),
        min_app_version=row.get("min_app_version"),
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        target_tenant_ids=frozenset(int(tid) for tid in targets),
    )


def load_candidate_releases(
    session: Session,
    *,
    channel: str,
    platform: str,
) -> list[CandidateRelease]:
    rows = (
        session.execute(
            text(
                """
                SELECT
                    r.release_id,
                    r.version,
                    r.channel,
                    r.platform,
                    r.rollout_scope,
                    r.active,
                    r.release_notes,
                    r.min_schema_version,
                    r.max_schema_version,
                    r.min_app_version,
                    r.starts_at,
                    r.ends_at,
                    COALESCE(
                        array_agg(t.tenant_id ORDER BY t.tenant_id)
                            FILTER (WHERE t.tenant_id IS NOT NULL),
                        ARRAY[]::int[]
                    ) AS target_tenant_ids
                FROM pos.desktop_update_releases r
                LEFT JOIN pos.desktop_update_release_targets t
                  ON t.release_id = r.release_id
                WHERE r.channel = :channel
                  AND r.platform = :platform
                GROUP BY r.release_id
                """
            ),
            {"channel": channel, "platform": platform},
        )
        .mappings()
        .all()
    )
    return [_candidate_from_mapping(row) for row in rows]


def get_update_policy(
    session: Session,
    *,
    tenant_id: int,
    current_version: str,
    channel: str,
    platform: str,
) -> DesktopUpdatePolicyResponse:
    return select_update_policy(
        load_candidate_releases(session, channel=channel, platform=platform),
        tenant_id=tenant_id,
        current_version=current_version,
    )


def _release_response_from_row(
    row: Mapping[str, Any] | RowMapping,
    tenant_ids: list[int],
) -> DesktopUpdateReleaseResponse:
    return DesktopUpdateReleaseResponse(
        release_id=int(row["release_id"]),
        version=str(row["version"]),
        channel=str(row["channel"]),
        platform=str(row["platform"]),
        rollout_scope=row["rollout_scope"],
        active=bool(row["active"]),
        tenant_ids=tenant_ids,
        release_notes=row.get("release_notes"),
        min_schema_version=row.get("min_schema_version"),
        max_schema_version=row.get("max_schema_version"),
        min_app_version=row.get("min_app_version"),
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def upsert_release(
    session: Session,
    payload: DesktopUpdateReleaseRequest,
) -> DesktopUpdateReleaseResponse:
    row = (
        session.execute(
            text(
                """
                INSERT INTO pos.desktop_update_releases (
                    version,
                    channel,
                    platform,
                    rollout_scope,
                    active,
                    release_notes,
                    min_schema_version,
                    max_schema_version,
                    min_app_version,
                    starts_at,
                    ends_at
                )
                VALUES (
                    :version,
                    :channel,
                    :platform,
                    :rollout_scope,
                    :active,
                    :release_notes,
                    :min_schema_version,
                    :max_schema_version,
                    :min_app_version,
                    :starts_at,
                    :ends_at
                )
                ON CONFLICT (version, channel, platform) DO UPDATE SET
                    rollout_scope = EXCLUDED.rollout_scope,
                    active = EXCLUDED.active,
                    release_notes = EXCLUDED.release_notes,
                    min_schema_version = EXCLUDED.min_schema_version,
                    max_schema_version = EXCLUDED.max_schema_version,
                    min_app_version = EXCLUDED.min_app_version,
                    starts_at = EXCLUDED.starts_at,
                    ends_at = EXCLUDED.ends_at,
                    updated_at = now()
                RETURNING *
                """
            ),
            payload.model_dump(exclude={"tenant_ids"}),
        )
        .mappings()
        .one()
    )
    release_id = int(row["release_id"])

    session.execute(
        text("DELETE FROM pos.desktop_update_release_targets WHERE release_id = :release_id"),
        {"release_id": release_id},
    )
    for tenant_id in payload.tenant_ids:
        session.execute(
            text(
                """
                INSERT INTO pos.desktop_update_release_targets (release_id, tenant_id)
                VALUES (:release_id, :tenant_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"release_id": release_id, "tenant_id": tenant_id},
        )

    return _release_response_from_row(row, payload.tenant_ids)


def list_releases(session: Session, *, limit: int = 50) -> list[DesktopUpdateReleaseResponse]:
    rows = (
        session.execute(
            text(
                """
                SELECT
                    r.*,
                    COALESCE(
                        array_agg(t.tenant_id ORDER BY t.tenant_id)
                            FILTER (WHERE t.tenant_id IS NOT NULL),
                        ARRAY[]::int[]
                    ) AS tenant_ids
                FROM pos.desktop_update_releases r
                LEFT JOIN pos.desktop_update_release_targets t
                  ON t.release_id = r.release_id
                GROUP BY r.release_id
                ORDER BY r.created_at DESC, r.release_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )
    return [
        _release_response_from_row(row, [int(tid) for tid in (row.get("tenant_ids") or [])])
        for row in rows
    ]
