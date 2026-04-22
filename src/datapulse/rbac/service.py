"""Service layer for RBAC — business logic for members, roles, sectors."""

from __future__ import annotations

import structlog

from datapulse.rbac.models import (
    AccessContext,
    MemberInvite,
    MemberResponse,
    MemberUpdate,
    RoleKey,
    RoleWithPermissions,
    SectorBrief,
    SectorCreate,
    SectorResponse,
    SectorUpdate,
)
from datapulse.rbac.repository import RBACRepository

logger = structlog.get_logger()


class RBACService:
    """Business logic for RBAC operations."""

    def __init__(
        self,
        repo: RBACRepository,
        owner_emails: list[str] | None = None,
        admin_emails: list[str] | None = None,
    ) -> None:
        self._repo = repo
        self._owner_emails = {e.lower() for e in (owner_emails or [])}
        self._admin_emails = {e.lower() for e in (admin_emails or [])}

    # ── Access Context ───────────────────────────────────────

    def resolve_access(self, tenant_id: int, user_id: str) -> AccessContext:
        """Resolve the full access context for a user within a tenant.

        Returns permissions, role, and accessible sectors/site_codes.
        If user is not a member, raises ValueError.
        """
        member = self._repo.get_member_by_user_id(tenant_id, user_id)
        if not member:
            raise ValueError(f"User {user_id} is not a member of tenant {tenant_id}")

        if not member["is_active"]:
            raise ValueError(f"User {user_id} is deactivated in tenant {tenant_id}")

        role_key: RoleKey = member["role_key"]
        permissions = set(self._repo.get_role_permissions(role_key))
        sectors = self._repo.get_member_sectors(member["member_id"])
        site_codes = self._repo.get_member_site_codes(member["member_id"])

        return AccessContext(
            member_id=member["member_id"],
            tenant_id=tenant_id,
            user_id=user_id,
            role_key=role_key,
            permissions=permissions,
            sector_ids=[s["sector_id"] for s in sectors],
            site_codes=site_codes,
            is_admin=role_key in ("owner", "admin"),
        )

    def _resolve_auto_role(self, email: str) -> RoleKey:
        """Determine the role for a new user based on configured email lists.

        Priority:
        1. Email in OWNER_EMAILS → "owner"
        2. Email in ADMIN_EMAILS → "admin"
        3. Otherwise → "viewer"
        """
        lower = email.lower()
        if lower in self._owner_emails:
            return "owner"
        if lower in self._admin_emails:
            return "admin"
        return "viewer"

    def ensure_member_exists(self, tenant_id: int, user_id: str, email: str, name: str) -> dict:
        """Auto-register a user as a member on first login.

        Role is determined by OWNER_EMAILS / ADMIN_EMAILS env variables.
        If the user's email isn't in either list, they get "viewer" role.
        Called from the auth dependency to ensure every authenticated user
        has a tenant_members record. Returns the member dict.

        Refuses empty emails: the ``(tenant_id, email)`` unique index would
        collide the moment two emailless callers tried to auto-register.
        """
        member = self._repo.get_member_by_user_id(tenant_id, user_id)
        if member:
            return member

        if not email:
            raise ValueError(
                f"User {user_id} has no email claim; cannot auto-register as a tenant member"
            )

        # Check if invited by email (pending invite)
        invited = self._repo.get_member_by_email(tenant_id, email)
        if invited and not invited.get("accepted_at"):
            return self._repo.accept_invite(invited["member_id"], user_id) or invited

        # Determine role from config
        role = self._resolve_auto_role(email)
        logger.info(
            "auto_register_member",
            tenant_id=tenant_id,
            user_id=user_id,
            email=email,
            role=role,
            reason="owner_emails"
            if role == "owner"
            else ("admin_emails" if role == "admin" else "default"),
        )
        return self._repo.create_member(
            tenant_id=tenant_id,
            user_id=user_id,
            email=email,
            display_name=name,
            role_key=role,
        )

    # ── Roles ────────────────────────────────────────────────

    def list_roles(self) -> list[RoleWithPermissions]:
        roles = self._repo.list_roles()
        result = []
        for r in roles:
            perms = self._repo.get_role_permissions(r["role_key"])
            result.append(RoleWithPermissions(**r, permissions=perms))
        return result

    # ── Members ──────────────────────────────────────────────

    def list_members(self, tenant_id: int) -> list[MemberResponse]:
        members = self._repo.list_members(tenant_id)
        result = []
        for m in members:
            sectors = self._repo.get_member_sectors(m["member_id"])
            result.append(
                MemberResponse(
                    **m,
                    sectors=[SectorBrief(**s) for s in sectors],
                )
            )
        return result

    def invite_member(
        self, tenant_id: int, invite: MemberInvite, invited_by: str
    ) -> MemberResponse:
        # Check limits
        count = self._repo.count_members(tenant_id)
        if count >= self._repo.MAX_MEMBERS_PER_TENANT:
            raise ValueError(
                f"Tenant has reached the maximum of {self._repo.MAX_MEMBERS_PER_TENANT} members"
            )

        # Check duplicate
        existing = self._repo.get_member_by_email(tenant_id, invite.email)
        if existing:
            raise ValueError(f"Member with email {invite.email} already exists")

        # Create with placeholder user_id (will be set on accept)
        member = self._repo.create_member(
            tenant_id=tenant_id,
            user_id=f"pending:{invite.email}",
            email=invite.email,
            display_name=invite.display_name or invite.email.split("@")[0],
            role_key=invite.role_key,
            invited_by=invited_by,
        )

        # Assign sectors
        if invite.sector_ids:
            self._repo.set_member_sectors(
                member["member_id"], invite.sector_ids, granted_by=invited_by
            )

        sectors = self._repo.get_member_sectors(member["member_id"])
        return MemberResponse(**member, sectors=[SectorBrief(**s) for s in sectors])

    def update_member(
        self,
        member_id: int,
        update: MemberUpdate,
        actor_role: RoleKey,
    ) -> MemberResponse:
        member = self._repo.get_member_by_id(member_id)
        if not member:
            raise ValueError("Member not found")

        # Only owner can change roles to owner or admin
        if update.role_key in ("owner", "admin") and actor_role != "owner":
            raise ValueError("Only the owner can assign the owner or admin role")

        # Cannot demote the current owner (owner self-demote not supported)
        if member["role_key"] == "owner" and update.role_key and update.role_key != "owner":
            raise ValueError("Cannot change the owner's role directly")

        fields = update.model_dump(exclude_none=True)
        sector_ids = fields.pop("sector_ids", None)

        updated = self._repo.update_member(member_id, **fields)
        if not updated:
            raise ValueError("Member not found")

        if sector_ids is not None:
            self._repo.set_member_sectors(member_id, sector_ids)

        sectors = self._repo.get_member_sectors(member_id)
        return MemberResponse(**updated, sectors=[SectorBrief(**s) for s in sectors])

    def remove_member(self, member_id: int, actor_member_id: int) -> bool:
        member = self._repo.get_member_by_id(member_id)
        if not member:
            raise ValueError("Member not found")

        if member["role_key"] == "owner":
            raise ValueError("Cannot remove the tenant owner")

        if member["member_id"] == actor_member_id:
            raise ValueError("Cannot remove yourself")

        return self._repo.delete_member(member_id)

    # ── Sectors ──────────────────────────────────────────────

    def list_sectors(self, tenant_id: int) -> list[SectorResponse]:
        sectors = self._repo.list_sectors(tenant_id)
        return [SectorResponse(**s) for s in sectors]

    def create_sector(self, tenant_id: int, data: SectorCreate) -> SectorResponse:
        count = self._repo.count_sectors(tenant_id)
        if count >= self._repo.MAX_SECTORS_PER_TENANT:
            raise ValueError(
                f"Tenant has reached the maximum of {self._repo.MAX_SECTORS_PER_TENANT} sectors"
            )
        sector = self._repo.create_sector(
            tenant_id=tenant_id,
            sector_key=data.sector_key,
            sector_name=data.sector_name,
            description=data.description,
            site_codes=data.site_codes,
        )
        return SectorResponse(**sector)

    def update_sector(self, sector_id: int, data: SectorUpdate) -> SectorResponse:
        fields = data.model_dump(exclude_none=True)
        updated = self._repo.update_sector(sector_id, **fields)
        if not updated:
            raise ValueError("Sector not found")
        return SectorResponse(**updated)

    def delete_sector(self, sector_id: int) -> bool:
        return self._repo.delete_sector(sector_id)

    def get_sector_members(self, sector_id: int) -> list[dict]:
        return self._repo.get_sector_members(sector_id)
