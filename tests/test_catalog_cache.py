"""Tests for thread-safe catalog caching in manifest_parser."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from datapulse.explore.manifest_parser import (
    get_catalog,
    invalidate_catalog,
)
from datapulse.explore.models import ExploreCatalog


@pytest.fixture(autouse=True)
def _reset_catalog():
    """Reset module-level cache before and after each test."""
    invalidate_catalog()
    yield
    invalidate_catalog()


class TestGetCatalog:
    @patch("datapulse.explore.manifest_parser.build_catalog")
    def test_builds_on_first_call(self, mock_build):
        mock_build.return_value = ExploreCatalog(models=[])
        result = get_catalog("/fake/models")
        assert isinstance(result, ExploreCatalog)
        mock_build.assert_called_once_with("/fake/models")

    @patch("datapulse.explore.manifest_parser.build_catalog")
    def test_returns_cached_on_second_call(self, mock_build):
        catalog = ExploreCatalog(models=[])
        mock_build.return_value = catalog
        first = get_catalog("/fake/models")
        second = get_catalog("/fake/models")
        assert first is second
        mock_build.assert_called_once()  # only built once

    @patch("datapulse.explore.manifest_parser.build_catalog")
    @patch("datapulse.explore.manifest_parser._CATALOG_TTL", 0)
    def test_rebuilds_after_ttl_expires(self, mock_build):
        """When TTL is 0, every call rebuilds."""
        mock_build.return_value = ExploreCatalog(models=[])
        get_catalog("/fake/models")
        get_catalog("/fake/models")
        assert mock_build.call_count == 2


class TestInvalidateCatalog:
    @patch("datapulse.explore.manifest_parser.build_catalog")
    def test_invalidate_forces_rebuild(self, mock_build):
        mock_build.return_value = ExploreCatalog(models=[])
        get_catalog("/fake/models")
        assert mock_build.call_count == 1

        invalidate_catalog()
        get_catalog("/fake/models")
        assert mock_build.call_count == 2
