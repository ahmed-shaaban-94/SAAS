"""Tests for RBACService business logic."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from datapulse.rbac.models import MemberInvite, MemberUpdate, SectorCreate
from datapulse.rbac.service import RBACService


def _make_member(**overrides):
    now = datetime.now(UTC)
    base = {
        "member_id": 1,
        "tenant_id": 1,
        "user_id": "auth0|123",
        "email": "test@example.com",
        "display_name": "Test User",
        "role_key": "viewer",
        "role_name": "Viewer",
        "is_active": True,
        "invited_by": None,
        "invited_at": now,
        "accepted_at": now,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


class TestResolveAccess:
    def test_resolve_active_member(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = _make_member(role_key="editor")
        repo.get_role_permissions.return_value = ["analytics:view", "pipeline:run"]
        repo.get_member_sectors.return_value = [
            {"sector_id": 1, "sector_key": "north", "sector_name": "North"}
        ]
        repo.get_member_site_codes.return_value = ["S1"]

        service = RBACService(repo)
        ctx = service.resolve_access(1, "auth0|123")

        assert ctx.role_key == "editor"
        assert "analytics:view" in ctx.permissions
        assert ctx.sector_ids == [1]
        assert ctx.site_codes == ["S1"]
        assert ctx.has_full_access is False

    def test_resolve_admin_has_full_access(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = _make_member(role_key="admin")
        repo.get_role_permissions.return_value = ["analytics:view", "members:manage"]
        repo.get_member_sectors.return_value = []
        repo.get_member_site_codes.return_value = []

        service = RBACService(repo)
        ctx = service.resolve_access(1, "auth0|123")
        assert ctx.has_full_access is True

    def test_resolve_nonexistent_user_raises(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None

        service = RBACService(repo)
        with pytest.raises(ValueError, match="not a member"):
            service.resolve_access(1, "unknown")

    def test_resolve_inactive_user_raises(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = _make_member(is_active=False)

        service = RBACService(repo)
        with pytest.raises(ValueError, match="deactivated"):
            service.resolve_access(1, "auth0|123")


class TestEnsureMemberExists:
    def test_existing_member_returned(self):
        repo = MagicMock()
        existing = _make_member()
        repo.get_member_by_user_id.return_value = existing

        service = RBACService(repo)
        result = service.ensure_member_exists(1, "auth0|123", "test@example.com", "Test")
        assert result == existing
        repo.create_member.assert_not_called()

    def test_pending_invite_accepted(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None
        repo.get_member_by_email.return_value = _make_member(
            user_id="pending:test@example.com", accepted_at=None
        )
        repo.accept_invite.return_value = _make_member()

        service = RBACService(repo)
        service.ensure_member_exists(1, "auth0|123", "test@example.com", "Test")
        repo.accept_invite.assert_called_once()

    def test_owner_email_gets_owner_role(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member(role_key="owner")

        service = RBACService(repo, owner_emails=["boss@company.com"])
        service.ensure_member_exists(1, "auth0|123", "boss@company.com", "Boss")
        repo.create_member.assert_called_once_with(
            tenant_id=1,
            user_id="auth0|123",
            email="boss@company.com",
            display_name="Boss",
            role_key="owner",
        )

    def test_admin_email_gets_admin_role(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member(role_key="admin")

        service = RBACService(repo, admin_emails=["manager@company.com"])
        service.ensure_member_exists(1, "auth0|123", "manager@company.com", "Manager")
        repo.create_member.assert_called_once_with(
            tenant_id=1,
            user_id="auth0|123",
            email="manager@company.com",
            display_name="Manager",
            role_key="admin",
        )

    def test_unknown_email_gets_viewer_role(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member()

        service = RBACService(repo, owner_emails=["boss@co.com"], admin_emails=["mgr@co.com"])
        service.ensure_member_exists(1, "auth0|123", "random@example.com", "Random")
        repo.create_member.assert_called_once_with(
            tenant_id=1,
            user_id="auth0|123",
            email="random@example.com",
            display_name="Random",
            role_key="viewer",
        )

    def test_email_matching_is_case_insensitive(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member(role_key="owner")

        service = RBACService(repo, owner_emails=["Boss@Company.com"])
        service.ensure_member_exists(1, "auth0|123", "boss@company.com", "Boss")
        repo.create_member.assert_called_once()
        assert repo.create_member.call_args.kwargs["role_key"] == "owner"

    def test_no_config_defaults_to_viewer(self):
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member()

        service = RBACService(repo)  # No owner_emails or admin_emails
        service.ensure_member_exists(1, "auth0|123", "test@example.com", "Test")
        repo.create_member.assert_called_once_with(
            tenant_id=1,
            user_id="auth0|123",
            email="test@example.com",
            display_name="Test",
            role_key="viewer",
        )

    def test_empty_email_refused_when_no_existing_member(self):
        # Regression: empty email + no existing user_id would previously hit
        # the (tenant_id, email) unique index with Key=(..,"") — now raises
        # a ValueError that the dependency translates to 403.
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = None

        service = RBACService(repo)
        with pytest.raises(ValueError, match="no email claim"):
            service.ensure_member_exists(1, "some-user", "", "some-name")

        repo.get_member_by_email.assert_not_called()
        repo.create_member.assert_not_called()

    def test_empty_email_returns_existing_member_without_db_write(self):
        # If a tenant_members row for this user_id already exists, empty
        # email is fine — we just return it. No INSERT happens.
        existing = _make_member(email="", user_id="some-user")
        repo = MagicMock()
        repo.get_member_by_user_id.return_value = existing

        service = RBACService(repo)
        result = service.ensure_member_exists(1, "some-user", "", "some-name")

        assert result == existing
        repo.create_member.assert_not_called()
        repo.get_member_by_email.assert_not_called()


class TestInviteMember:
    def test_invite_success(self):
        repo = MagicMock()
        repo.MAX_MEMBERS_PER_TENANT = 100
        repo.MAX_SECTORS_PER_TENANT = 50
        repo.count_members.return_value = 5
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member(
            user_id="pending:new@example.com", email="new@example.com"
        )
        repo.get_member_sectors.return_value = []

        service = RBACService(repo)
        invite = MemberInvite(email="new@example.com", role_key="editor")
        result = service.invite_member(1, invite, invited_by="admin-user")
        assert result.email == "new@example.com"

    def test_invite_duplicate_raises(self):
        repo = MagicMock()
        repo.MAX_MEMBERS_PER_TENANT = 100
        repo.count_members.return_value = 5
        repo.get_member_by_email.return_value = _make_member()

        service = RBACService(repo)
        invite = MemberInvite(email="test@example.com")
        with pytest.raises(ValueError, match="already exists"):
            service.invite_member(1, invite, invited_by="admin")

    def test_invite_as_owner_allowed(self):
        repo = MagicMock()
        repo.MAX_MEMBERS_PER_TENANT = 100
        repo.count_members.return_value = 1
        repo.get_member_by_email.return_value = None
        repo.create_member.return_value = _make_member(
            user_id="pending:new@example.com", email="new@example.com", role_key="owner"
        )
        repo.get_member_sectors.return_value = []

        service = RBACService(repo)
        invite = MemberInvite(email="new@example.com", role_key="owner")
        result = service.invite_member(1, invite, invited_by="admin")
        assert result.email == "new@example.com"

    def test_invite_over_limit_raises(self):
        repo = MagicMock()
        repo.MAX_MEMBERS_PER_TENANT = 100
        repo.count_members.return_value = 100

        service = RBACService(repo)
        invite = MemberInvite(email="new@example.com")
        with pytest.raises(ValueError, match="maximum"):
            service.invite_member(1, invite, invited_by="admin")


class TestUpdateMember:
    def test_update_role(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(role_key="viewer")
        updated = _make_member(role_key="editor")
        repo.update_member.return_value = updated
        repo.get_member_sectors.return_value = []

        service = RBACService(repo)
        update = MemberUpdate(role_key="editor")
        result = service.update_member(1, update, actor_role="admin")
        assert result.role_key == "editor"

    def test_cannot_change_owner_role(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(role_key="owner")

        service = RBACService(repo)
        update = MemberUpdate(role_key="admin")
        with pytest.raises(ValueError, match="Cannot change the owner"):
            service.update_member(1, update, actor_role="owner")

    def test_only_owner_can_assign_admin(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(role_key="viewer")

        service = RBACService(repo)
        update = MemberUpdate(role_key="admin")
        with pytest.raises(ValueError, match="Only the owner"):
            service.update_member(1, update, actor_role="admin")

    def test_only_owner_can_promote_to_owner(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(role_key="editor")

        service = RBACService(repo)
        update = MemberUpdate(role_key="owner")
        with pytest.raises(ValueError, match="Only the owner"):
            service.update_member(1, update, actor_role="admin")

    def test_owner_can_promote_to_owner(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(role_key="admin")
        updated = _make_member(role_key="owner")
        repo.update_member.return_value = updated
        repo.get_member_sectors.return_value = []

        service = RBACService(repo)
        update = MemberUpdate(role_key="owner")
        result = service.update_member(1, update, actor_role="owner")
        assert result.role_key == "owner"


class TestRemoveMember:
    def test_remove_success(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(member_id=2, role_key="viewer")
        repo.delete_member.return_value = True

        service = RBACService(repo)
        assert service.remove_member(2, actor_member_id=1) is True

    def test_cannot_remove_owner(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(role_key="owner")

        service = RBACService(repo)
        with pytest.raises(ValueError, match="Cannot remove the tenant owner"):
            service.remove_member(1, actor_member_id=2)

    def test_cannot_remove_self(self):
        repo = MagicMock()
        repo.get_member_by_id.return_value = _make_member(member_id=1, role_key="admin")

        service = RBACService(repo)
        with pytest.raises(ValueError, match="Cannot remove yourself"):
            service.remove_member(1, actor_member_id=1)


class TestSectors:
    def test_create_sector(self):
        repo = MagicMock()
        repo.MAX_SECTORS_PER_TENANT = 50
        repo.count_sectors.return_value = 0
        repo.create_sector.return_value = {
            "sector_id": 1,
            "tenant_id": 1,
            "sector_key": "north",
            "sector_name": "North",
            "description": "",
            "site_codes": ["S1"],
            "is_active": True,
            "created_at": datetime.now(UTC),
            "member_count": 0,
        }

        service = RBACService(repo)
        data = SectorCreate(sector_key="north", sector_name="North", site_codes=["S1"])
        result = service.create_sector(1, data)
        assert result.sector_key == "north"
        assert result.site_codes == ["S1"]

    def test_create_sector_over_limit(self):
        repo = MagicMock()
        repo.MAX_SECTORS_PER_TENANT = 50
        repo.count_sectors.return_value = 50

        service = RBACService(repo)
        data = SectorCreate(sector_key="new", sector_name="New")
        with pytest.raises(ValueError, match="maximum"):
            service.create_sector(1, data)

    def test_delete_sector(self):
        repo = MagicMock()
        repo.delete_sector.return_value = True

        service = RBACService(repo)
        assert service.delete_sector(1) is True
