"""Tests for RBACRepository with mocked DB sessions."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, call

from datapulse.rbac.repository import RBACRepository


def _mock_session():
    return MagicMock()


def _make_role(**overrides):
    base = {
        "role_id": 1,
        "role_key": "viewer",
        "role_name": "Viewer",
        "description": "Read-only",
        "is_system": True,
    }
    base.update(overrides)
    return base


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


def _make_sector(**overrides):
    base = {
        "sector_id": 1,
        "tenant_id": 1,
        "sector_key": "sales-north",
        "sector_name": "Sales North",
        "description": "",
        "site_codes": ["S1", "S2"],
        "is_active": True,
        "created_at": datetime.now(UTC),
        "member_count": 3,
    }
    base.update(overrides)
    return base


class TestListRoles:
    def test_returns_roles(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.all.return_value = [
            _make_role(),
            _make_role(role_id=2, role_key="admin", role_name="Admin"),
        ]
        repo = RBACRepository(session)
        roles = repo.list_roles()
        assert len(roles) == 2
        assert roles[0]["role_key"] == "viewer"

    def test_empty_roles(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.all.return_value = []
        repo = RBACRepository(session)
        assert repo.list_roles() == []


class TestGetRoleByKey:
    def test_found(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = _make_role()
        repo = RBACRepository(session)
        role = repo.get_role_by_key("viewer")
        assert role is not None
        assert role["role_key"] == "viewer"

    def test_not_found(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = None
        repo = RBACRepository(session)
        assert repo.get_role_by_key("nonexistent") is None


class TestGetRolePermissions:
    def test_returns_permissions(self):
        session = _mock_session()
        session.execute.return_value.scalars.return_value.all.return_value = [
            "analytics:view",
            "reports:view",
        ]
        repo = RBACRepository(session)
        perms = repo.get_role_permissions("viewer")
        assert perms == ["analytics:view", "reports:view"]


class TestMembers:
    def test_count_members(self):
        session = _mock_session()
        session.execute.return_value.scalar.return_value = 5
        repo = RBACRepository(session)
        assert repo.count_members(1) == 5

    def test_list_members(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.all.return_value = [
            _make_member(),
            _make_member(member_id=2, email="other@test.com"),
        ]
        repo = RBACRepository(session)
        members = repo.list_members(1)
        assert len(members) == 2

    def test_get_member_by_user_id(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = _make_member()
        repo = RBACRepository(session)
        m = repo.get_member_by_user_id(1, "auth0|123")
        assert m is not None
        assert m["email"] == "test@example.com"

    def test_get_member_by_email(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = _make_member()
        repo = RBACRepository(session)
        m = repo.get_member_by_email(1, "test@example.com")
        assert m is not None

    def test_get_member_by_email_not_found(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = None
        repo = RBACRepository(session)
        assert repo.get_member_by_email(1, "nope@test.com") is None

    def test_delete_member(self):
        session = _mock_session()
        session.execute.return_value.rowcount = 1
        repo = RBACRepository(session)
        assert repo.delete_member(1) is True

    def test_delete_member_not_found(self):
        session = _mock_session()
        session.execute.return_value.rowcount = 0
        repo = RBACRepository(session)
        assert repo.delete_member(999) is False


class TestSectors:
    def test_count_sectors(self):
        session = _mock_session()
        session.execute.return_value.scalar.return_value = 3
        repo = RBACRepository(session)
        assert repo.count_sectors(1) == 3

    def test_list_sectors(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.all.return_value = [
            _make_sector(),
        ]
        repo = RBACRepository(session)
        sectors = repo.list_sectors(1)
        assert len(sectors) == 1
        assert sectors[0]["sector_key"] == "sales-north"

    def test_get_sector(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = _make_sector()
        repo = RBACRepository(session)
        s = repo.get_sector(1)
        assert s is not None
        assert s["site_codes"] == ["S1", "S2"]

    def test_get_sector_not_found(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.first.return_value = None
        repo = RBACRepository(session)
        assert repo.get_sector(999) is None

    def test_delete_sector(self):
        session = _mock_session()
        session.execute.return_value.rowcount = 1
        repo = RBACRepository(session)
        assert repo.delete_sector(1) is True


class TestSectorAccess:
    def test_get_member_sectors(self):
        session = _mock_session()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {"sector_id": 1, "sector_key": "north", "sector_name": "North"},
        ]
        repo = RBACRepository(session)
        sectors = repo.get_member_sectors(1)
        assert len(sectors) == 1
        assert sectors[0]["sector_key"] == "north"

    def test_get_member_site_codes(self):
        session = _mock_session()
        session.execute.return_value.scalars.return_value.all.return_value = ["S1", "S2"]
        repo = RBACRepository(session)
        codes = repo.get_member_site_codes(1)
        assert codes == ["S1", "S2"]

    def test_set_member_sectors(self):
        session = _mock_session()
        repo = RBACRepository(session)
        repo.set_member_sectors(1, [10, 20], granted_by="admin-user")
        # Should call DELETE once, then INSERT twice
        assert session.execute.call_count == 3
