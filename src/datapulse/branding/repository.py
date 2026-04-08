"""Repository for tenant branding — raw SQL via SQLAlchemy text().

All queries use parameterized placeholders to prevent SQL injection.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.branding.models import (
    BrandingResponse,
    BrandingUpdate,
    PublicBrandingResponse,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_DEFAULT_BRANDING = BrandingResponse(tenant_id=0)


class BrandingRepository:
    """Data-access layer for tenant branding configuration."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_branding(self, tenant_id: int) -> BrandingResponse:
        """Get branding config for a tenant, returning defaults if not set."""
        row = self._session.execute(
            text("""
                SELECT tenant_id, company_name, logo_url, favicon_url,
                       primary_color, accent_color, sidebar_bg, font_family,
                       custom_domain, subdomain, email_from_name, email_logo_url,
                       footer_text, support_email, support_url,
                       hide_datapulse_branding, custom_login_bg,
                       created_at, updated_at
                FROM public.tenant_branding
                WHERE tenant_id = :tid
            """),
            {"tid": tenant_id},
        ).mappings().fetchone()

        if row is None:
            return BrandingResponse(tenant_id=tenant_id)
        return BrandingResponse(**dict(row))  # type: ignore[arg-type]

    def update_branding(self, tenant_id: int, data: BrandingUpdate) -> BrandingResponse:
        """Update branding config (upsert pattern)."""
        log.info("update_branding", tenant_id=tenant_id)

        updates = data.model_dump(exclude_none=True)
        if not updates:
            return self.get_branding(tenant_id)

        set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
        updates["tid"] = tenant_id

        cols = ", ".join(updates.keys() - {"tid"})
        vals = ", ".join(f":{k}" for k in updates if k != "tid")
        row = self._session.execute(
            text(f"""
                INSERT INTO public.tenant_branding (tenant_id, {cols})
                VALUES (:tid, {vals})
                ON CONFLICT (tenant_id) DO UPDATE SET
                    {set_clauses},
                    updated_at = NOW()
                RETURNING tenant_id, company_name, logo_url, favicon_url,
                          primary_color, accent_color, sidebar_bg, font_family,
                          custom_domain, subdomain, email_from_name, email_logo_url,
                          footer_text, support_email, support_url,
                          hide_datapulse_branding, custom_login_bg,
                          created_at, updated_at
            """),
            updates,
        ).mappings().fetchone()

        return BrandingResponse(**dict(row))  # type: ignore[arg-type]

    def update_logo_url(self, tenant_id: int, logo_url: str | None) -> None:
        """Update the logo URL for a tenant."""
        self._session.execute(
            text("""
                UPDATE public.tenant_branding
                SET logo_url = :url, updated_at = NOW()
                WHERE tenant_id = :tid
            """),
            {"tid": tenant_id, "url": logo_url},
        )

    def update_favicon_url(self, tenant_id: int, favicon_url: str | None) -> None:
        """Update the favicon URL for a tenant."""
        self._session.execute(
            text("""
                UPDATE public.tenant_branding
                SET favicon_url = :url, updated_at = NOW()
                WHERE tenant_id = :tid
            """),
            {"tid": tenant_id, "url": favicon_url},
        )

    def get_public_branding_by_domain(self, domain: str) -> PublicBrandingResponse | None:
        """Look up public branding by custom domain or subdomain (no auth)."""
        row = self._session.execute(
            text("""
                SELECT company_name, logo_url, favicon_url,
                       primary_color, accent_color, font_family,
                       hide_datapulse_branding, custom_login_bg
                FROM public.tenant_branding
                WHERE custom_domain = :domain OR subdomain = :domain
                LIMIT 1
            """),
            {"domain": domain},
        ).mappings().fetchone()

        if row is None:
            return None
        return PublicBrandingResponse(**dict(row))  # type: ignore[arg-type]

    def resolve_tenant_by_domain(self, domain: str) -> int | None:
        """Resolve a custom domain or subdomain to a tenant_id."""
        row = self._session.execute(
            text("""
                SELECT tenant_id
                FROM public.tenant_branding
                WHERE custom_domain = :domain OR subdomain = :domain
                LIMIT 1
            """),
            {"domain": domain},
        ).fetchone()
        return row[0] if row else None
