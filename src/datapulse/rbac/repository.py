"""Repository layer for RBAC — tenant_members, roles, sectors, permissions."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.core.sql import build_set_eq

logger = structlog.get_logger()


class RBACRepository:
    """CRUD operations for RBAC tables."""

    MAX_MEMBERS_PER_TENANT = 100
    MAX_SECTORS_PER_TENANT = 50

    def __init__(self, session: Session) -> None:
        self._s = session

    # ── Roles ────────────────────────────────────────────────

    def list_roles(self) -> list[dict]:
        rows = (
            self._s.execute(
                text(
                    "SELECT role_id, role_key, role_name, description, is_system"
                    " FROM public.roles ORDER BY role_id"
                )
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_role_by_key(self, role_key: str) -> dict | None:
        row = (
            self._s.execute(
                text(
                    "SELECT role_id, role_key, role_name, description, is_system"
                    " FROM public.roles WHERE role_key = :rk"
                ),
                {"rk": role_key},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_role_permissions(self, role_key: str) -> list[str]:
        rows = (
            self._s.execute(
                text("""
                SELECT p.permission_key
                FROM public.role_permissions rp
                JOIN public.roles r ON r.role_id = rp.role_id
                JOIN public.permissions p ON p.permission_id = rp.permission_id
                WHERE r.role_key = :rk
                ORDER BY p.permission_key
            """),
                {"rk": role_key},
            )
            .scalars()
            .all()
        )
        return list(rows)

    def list_permissions(self) -> list[dict]:
        rows = (
            self._s.execute(
                text(
                    "SELECT permission_key, category, description"
                    " FROM public.permissions ORDER BY category, permission_key"
                )
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    # ── Members ──────────────────────────────────────────────

    def count_members(self, tenant_id: int) -> int:
        return (
            self._s.execute(
                text("SELECT COUNT(*) FROM public.tenant_members WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            ).scalar()
            or 0
        )

    def list_members(self, tenant_id: int) -> list[dict]:
        rows = (
            self._s.execute(
                text("""
                SELECT m.member_id, m.tenant_id, m.user_id, m.email, m.display_name,
                       r.role_key, r.role_name, m.is_active,
                       m.invited_by, m.invited_at, m.accepted_at, m.created_at, m.updated_at
                FROM public.tenant_members m
                JOIN public.roles r ON r.role_id = m.role_id
                WHERE m.tenant_id = :tid
                ORDER BY m.created_at
            """),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_member_by_user_id(self, tenant_id: int, user_id: str) -> dict | None:
        row = (
            self._s.execute(
                text("""
                SELECT m.member_id, m.tenant_id, m.user_id, m.email, m.display_name,
                       r.role_key, r.role_name, m.is_active,
                       m.invited_by, m.invited_at, m.accepted_at, m.created_at, m.updated_at
                FROM public.tenant_members m
                JOIN public.roles r ON r.role_id = m.role_id
                WHERE m.tenant_id = :tid AND m.user_id = :uid
            """),
                {"tid": tenant_id, "uid": user_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_member_by_email(self, tenant_id: int, email: str) -> dict | None:
        row = (
            self._s.execute(
                text("""
                SELECT m.member_id, m.tenant_id, m.user_id, m.email, m.display_name,
                       r.role_key, r.role_name, m.is_active,
                       m.invited_by, m.invited_at, m.accepted_at, m.created_at, m.updated_at
                FROM public.tenant_members m
                JOIN public.roles r ON r.role_id = m.role_id
                WHERE m.tenant_id = :tid AND LOWER(m.email) = LOWER(:email)
            """),
                {"tid": tenant_id, "email": email},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_member_by_id(self, member_id: int) -> dict | None:
        row = (
            self._s.execute(
                text("""
                SELECT m.member_id, m.tenant_id, m.user_id, m.email, m.display_name,
                       r.role_key, r.role_name, m.is_active,
                       m.invited_by, m.invited_at, m.accepted_at, m.created_at, m.updated_at
                FROM public.tenant_members m
                JOIN public.roles r ON r.role_id = m.role_id
                WHERE m.member_id = :mid
            """),
                {"mid": member_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def create_member(
        self,
        tenant_id: int,
        user_id: str,
        email: str,
        display_name: str,
        role_key: str,
        invited_by: str | None = None,
    ) -> dict:
        role = self.get_role_by_key(role_key)
        if not role:
            raise ValueError(f"Unknown role: {role_key}")

        row = (
            self._s.execute(
                text("""
                INSERT INTO public.tenant_members
                    (tenant_id, user_id, email, display_name, role_id, invited_by)
                VALUES (:tid, :uid, :email, :name, :rid, :inv)
                RETURNING member_id, tenant_id, user_id, email, display_name,
                          invited_by, invited_at, accepted_at, created_at, updated_at
            """),
                {
                    "tid": tenant_id,
                    "uid": user_id,
                    "email": email,
                    "name": display_name,
                    "rid": role["role_id"],
                    "inv": invited_by,
                },
            )
            .mappings()
            .first()
        )
        result = dict(row) if row else {}
        result["role_key"] = role_key
        result["role_name"] = role["role_name"]
        result["is_active"] = True
        return result

    def update_member(self, member_id: int, **fields) -> dict | None:
        # role_key is validated + mapped to role_id before reaching build_set_eq
        # so build_set_eq only sees literal column names at the call site.
        role_id: int | None = None
        if fields.get("role_key") is not None:
            role = self.get_role_by_key(fields["role_key"])
            if not role:
                raise ValueError(f"Unknown role: {fields['role_key']}")
            role_id = role["role_id"]

        body, set_params = build_set_eq(
            [
                ("role_id", "rid", role_id),
                ("display_name", "name", fields.get("display_name")),
                ("is_active", "active", fields.get("is_active")),
            ]
        )
        if not body:
            return self.get_member_by_id(member_id)

        body += ", updated_at = :now"
        set_params["now"] = datetime.now(UTC)
        set_params["mid"] = member_id

        self._s.execute(
            text(f"UPDATE public.tenant_members SET {body} WHERE member_id = :mid"),
            set_params,
        )
        return self.get_member_by_id(member_id)

    def delete_member(self, member_id: int) -> bool:
        result = self._s.execute(
            text("DELETE FROM public.tenant_members WHERE member_id = :mid"),
            {"mid": member_id},
        )
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    def accept_invite(self, member_id: int, user_id: str) -> dict | None:
        self._s.execute(
            text("""
                UPDATE public.tenant_members
                SET user_id = :uid, accepted_at = :now, updated_at = :now
                WHERE member_id = :mid AND accepted_at IS NULL
            """),
            {"mid": member_id, "uid": user_id, "now": datetime.now(UTC)},
        )
        return self.get_member_by_id(member_id)

    def relink_member_user_id(self, member_id: int, user_id: str) -> dict | None:
        """Update an existing accepted member's user_id to a new IdP id.

        Used when Clerk reissues a `user_*` id for the same email (e.g. user
        cleared session, dev environment reset, account migration) — the
        unique `(tenant_id, email)` row exists but the new sign-in carries a
        different `user_id`, so a blind INSERT would raise IntegrityError.
        """
        self._s.execute(
            text("""
                UPDATE public.tenant_members
                SET user_id = :uid, updated_at = :now,
                    accepted_at = COALESCE(accepted_at, :now)
                WHERE member_id = :mid
            """),
            {"mid": member_id, "uid": user_id, "now": datetime.now(UTC)},
        )
        return self.get_member_by_id(member_id)

    # ── Sectors ──────────────────────────────────────────────

    def count_sectors(self, tenant_id: int) -> int:
        return (
            self._s.execute(
                text("SELECT COUNT(*) FROM public.sectors WHERE tenant_id = :tid"),
                {"tid": tenant_id},
            ).scalar()
            or 0
        )

    def list_sectors(self, tenant_id: int) -> list[dict]:
        rows = (
            self._s.execute(
                text("""
                SELECT s.sector_id, s.tenant_id, s.sector_key, s.sector_name,
                       s.description, s.site_codes, s.is_active, s.created_at,
                       (SELECT COUNT(*) FROM public.member_sector_access msa
                        WHERE msa.sector_id = s.sector_id) AS member_count
                FROM public.sectors s
                WHERE s.tenant_id = :tid
                ORDER BY s.created_at
            """),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_sector(self, sector_id: int) -> dict | None:
        row = (
            self._s.execute(
                text("""
                SELECT s.sector_id, s.tenant_id, s.sector_key, s.sector_name,
                       s.description, s.site_codes, s.is_active, s.created_at,
                       (SELECT COUNT(*) FROM public.member_sector_access msa
                        WHERE msa.sector_id = s.sector_id) AS member_count
                FROM public.sectors s
                WHERE s.sector_id = :sid
            """),
                {"sid": sector_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def create_sector(
        self,
        tenant_id: int,
        sector_key: str,
        sector_name: str,
        description: str = "",
        site_codes: list[str] | None = None,
    ) -> dict:
        row = (
            self._s.execute(
                text("""
                INSERT INTO public.sectors
                    (tenant_id, sector_key, sector_name, description, site_codes)
                VALUES (:tid, :key, :name, :desc, :codes)
                RETURNING sector_id, tenant_id, sector_key, sector_name,
                          description, site_codes, is_active, created_at
            """),
                {
                    "tid": tenant_id,
                    "key": sector_key,
                    "name": sector_name,
                    "desc": description,
                    "codes": site_codes or [],
                },
            )
            .mappings()
            .first()
        )
        result = dict(row) if row else {}
        result["member_count"] = 0
        return result

    def update_sector(self, sector_id: int, **fields) -> dict | None:
        body, params = build_set_eq(
            [
                ("sector_name", "name", fields.get("sector_name")),
                ("description", "desc", fields.get("description")),
                ("site_codes", "codes", fields.get("site_codes")),
                ("is_active", "active", fields.get("is_active")),
            ]
        )
        if not body:
            return self.get_sector(sector_id)

        body += ", updated_at = :now"
        params["now"] = datetime.now(UTC)
        params["sid"] = sector_id

        self._s.execute(
            text(f"UPDATE public.sectors SET {body} WHERE sector_id = :sid"),
            params,
        )
        return self.get_sector(sector_id)

    def delete_sector(self, sector_id: int) -> bool:
        result = self._s.execute(
            text("DELETE FROM public.sectors WHERE sector_id = :sid"),
            {"sid": sector_id},
        )
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    # ── Sector Access ────────────────────────────────────────

    def get_member_sectors(self, member_id: int) -> list[dict]:
        rows = (
            self._s.execute(
                text("""
                SELECT s.sector_id, s.sector_key, s.sector_name
                FROM public.member_sector_access msa
                JOIN public.sectors s ON s.sector_id = msa.sector_id
                WHERE msa.member_id = :mid
                ORDER BY s.sector_name
            """),
                {"mid": member_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_member_site_codes(self, member_id: int) -> list[str]:
        """Get all site_codes from all sectors assigned to a member."""
        rows = (
            self._s.execute(
                text("""
                SELECT DISTINCT unnest(s.site_codes) AS code
                FROM public.member_sector_access msa
                JOIN public.sectors s ON s.sector_id = msa.sector_id
                WHERE msa.member_id = :mid AND s.is_active = TRUE
                ORDER BY code
            """),
                {"mid": member_id},
            )
            .scalars()
            .all()
        )
        return list(rows)

    def set_member_sectors(
        self, member_id: int, sector_ids: list[int], granted_by: str | None = None
    ) -> None:
        # Remove existing
        self._s.execute(
            text("DELETE FROM public.member_sector_access WHERE member_id = :mid"),
            {"mid": member_id},
        )
        # Insert new
        for sid in sector_ids:
            self._s.execute(
                text("""
                    INSERT INTO public.member_sector_access (member_id, sector_id, granted_by)
                    VALUES (:mid, :sid, :by)
                    ON CONFLICT DO NOTHING
                """),
                {"mid": member_id, "sid": sid, "by": granted_by},
            )

    def get_sector_members(self, sector_id: int) -> list[dict]:
        rows = (
            self._s.execute(
                text("""
                SELECT m.member_id, m.email, m.display_name, r.role_key, m.is_active
                FROM public.member_sector_access msa
                JOIN public.tenant_members m ON m.member_id = msa.member_id
                JOIN public.roles r ON r.role_id = m.role_id
                WHERE msa.sector_id = :sid
                ORDER BY m.display_name
            """),
                {"sid": sector_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]
