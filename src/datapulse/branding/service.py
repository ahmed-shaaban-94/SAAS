"""Business logic layer for tenant branding."""

from __future__ import annotations

import re

from datapulse.branding.models import (
    BrandingResponse,
    BrandingUpdate,
    PublicBrandingResponse,
)
from datapulse.branding.repository import BrandingRepository
from datapulse.logging import get_logger

log = get_logger(__name__)

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_SUBDOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


class BrandingService:
    """Orchestrates branding operations with validation."""

    def __init__(self, repo: BrandingRepository) -> None:
        self._repo = repo

    def get_branding(self, tenant_id: int) -> BrandingResponse:
        """Get the current branding configuration."""
        return self._repo.get_branding(tenant_id)

    def update_branding(self, tenant_id: int, data: BrandingUpdate) -> BrandingResponse:
        """Update branding with validation."""
        log.info("service_update_branding", tenant_id=tenant_id)

        if data.primary_color and not _HEX_COLOR_RE.match(data.primary_color):
            raise ValueError(f"Invalid primary_color: {data.primary_color}")
        if data.accent_color and not _HEX_COLOR_RE.match(data.accent_color):
            raise ValueError(f"Invalid accent_color: {data.accent_color}")
        if data.sidebar_bg and not _HEX_COLOR_RE.match(data.sidebar_bg):
            raise ValueError(f"Invalid sidebar_bg: {data.sidebar_bg}")

        if data.subdomain and not _SUBDOMAIN_RE.match(data.subdomain):
            raise ValueError(
                f"Invalid subdomain: {data.subdomain}. "
                "Must be lowercase alphanumeric with optional hyphens."
            )

        return self._repo.update_branding(tenant_id, data)

    def update_logo(self, tenant_id: int, logo_url: str) -> BrandingResponse:
        """Update logo URL and return updated branding."""
        self._repo.update_logo_url(tenant_id, logo_url)
        return self._repo.get_branding(tenant_id)

    def delete_logo(self, tenant_id: int) -> BrandingResponse:
        """Remove logo and return updated branding."""
        self._repo.update_logo_url(tenant_id, None)
        return self._repo.get_branding(tenant_id)

    def update_favicon(self, tenant_id: int, favicon_url: str) -> BrandingResponse:
        """Update favicon URL and return updated branding."""
        self._repo.update_favicon_url(tenant_id, favicon_url)
        return self._repo.get_branding(tenant_id)

    def get_public_branding(self, domain: str) -> PublicBrandingResponse:
        """Get public branding by domain (no auth required)."""
        result = self._repo.get_public_branding_by_domain(domain)
        if result is None:
            return PublicBrandingResponse()
        return result

    def resolve_tenant(self, domain: str) -> int | None:
        """Resolve a domain to a tenant_id."""
        return self._repo.resolve_tenant_by_domain(domain)
