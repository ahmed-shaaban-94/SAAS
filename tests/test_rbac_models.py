"""Tests for RBAC Pydantic models."""

import pytest

from datapulse.rbac.models import (
    AccessContext,
    MemberInvite,
    MemberUpdate,
    SectorCreate,
    SectorUpdate,
)


class TestAccessContext:
    def test_has_full_access_owner(self):
        ctx = AccessContext(
            member_id=1, tenant_id=1, user_id="u1", role_key="owner",
            permissions=set(), sector_ids=[], site_codes=[], is_admin=True,
        )
        assert ctx.has_full_access is True

    def test_has_full_access_admin(self):
        ctx = AccessContext(
            member_id=2, tenant_id=1, user_id="u2", role_key="admin",
            permissions=set(), sector_ids=[], site_codes=[], is_admin=True,
        )
        assert ctx.has_full_access is True

    def test_no_full_access_editor(self):
        ctx = AccessContext(
            member_id=3, tenant_id=1, user_id="u3", role_key="editor",
            permissions=set(), sector_ids=[1], site_codes=["S1"], is_admin=False,
        )
        assert ctx.has_full_access is False

    def test_no_full_access_viewer(self):
        ctx = AccessContext(
            member_id=4, tenant_id=1, user_id="u4", role_key="viewer",
            permissions=set(), sector_ids=[], site_codes=[], is_admin=False,
        )
        assert ctx.has_full_access is False


class TestMemberInvite:
    def test_valid_invite(self):
        invite = MemberInvite(email="test@example.com", role_key="editor")
        assert invite.email == "test@example.com"
        assert invite.role_key == "editor"
        assert invite.sector_ids == []

    def test_default_role(self):
        invite = MemberInvite(email="test@example.com")
        assert invite.role_key == "viewer"

    def test_with_sectors(self):
        invite = MemberInvite(email="a@b.com", sector_ids=[1, 2, 3])
        assert invite.sector_ids == [1, 2, 3]


class TestMemberUpdate:
    def test_partial_update(self):
        update = MemberUpdate(role_key="admin")
        assert update.role_key == "admin"
        assert update.display_name is None
        assert update.is_active is None

    def test_empty_update(self):
        update = MemberUpdate()
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {}


class TestSectorCreate:
    def test_valid_sector(self):
        sector = SectorCreate(sector_key="sales-north", sector_name="Sales North")
        assert sector.sector_key == "sales-north"

    def test_key_validation(self):
        with pytest.raises(Exception):
            SectorCreate(sector_key="Sales North!", sector_name="Sales North")

    def test_with_site_codes(self):
        sector = SectorCreate(
            sector_key="region-a", sector_name="Region A", site_codes=["S1", "S2"]
        )
        assert sector.site_codes == ["S1", "S2"]


class TestSectorUpdate:
    def test_partial(self):
        update = SectorUpdate(sector_name="New Name")
        assert update.sector_name == "New Name"
        assert update.site_codes is None
