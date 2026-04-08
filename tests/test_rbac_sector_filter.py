"""Tests for sector-based data filtering."""

from datapulse.rbac.models import AccessContext
from datapulse.rbac.sector_filter import build_sector_filter, get_accessible_site_codes


def _ctx(role_key="viewer", site_codes=None, **kw):
    return AccessContext(
        member_id=1,
        tenant_id=1,
        user_id="u1",
        role_key=role_key,
        permissions=set(),
        sector_ids=[1] if site_codes else [],
        site_codes=site_codes or [],
        is_admin=role_key in ("owner", "admin"),
        **kw,
    )


class TestBuildSectorFilter:
    def test_owner_no_filter(self):
        ctx = _ctx("owner")
        sql, params = build_sector_filter(ctx)
        assert sql == ""
        assert params == {}

    def test_admin_no_filter(self):
        ctx = _ctx("admin")
        sql, params = build_sector_filter(ctx)
        assert sql == ""
        assert params == {}

    def test_viewer_with_sites(self):
        ctx = _ctx("viewer", site_codes=["S1", "S2"])
        sql, params = build_sector_filter(ctx)
        assert "ANY" in sql
        assert params["sector_sites"] == ["S1", "S2"]

    def test_viewer_no_sites_blocks_all(self):
        ctx = _ctx("viewer", site_codes=[])
        sql, params = build_sector_filter(ctx)
        assert "FALSE" in sql

    def test_custom_column(self):
        ctx = _ctx("editor", site_codes=["S1"])
        sql, params = build_sector_filter(ctx, site_column="s.site_code")
        assert "s.site_code" in sql

    def test_custom_param_prefix(self):
        ctx = _ctx("editor", site_codes=["S1"])
        sql, params = build_sector_filter(ctx, param_prefix="my_filter")
        assert "my_filter_sites" in params


class TestGetAccessibleSiteCodes:
    def test_admin_returns_none(self):
        ctx = _ctx("admin")
        assert get_accessible_site_codes(ctx) is None

    def test_owner_returns_none(self):
        ctx = _ctx("owner")
        assert get_accessible_site_codes(ctx) is None

    def test_viewer_returns_codes(self):
        ctx = _ctx("viewer", site_codes=["S1", "S2"])
        result = get_accessible_site_codes(ctx)
        assert result == ["S1", "S2"]

    def test_viewer_no_codes_returns_empty(self):
        ctx = _ctx("viewer")
        result = get_accessible_site_codes(ctx)
        assert result == []
