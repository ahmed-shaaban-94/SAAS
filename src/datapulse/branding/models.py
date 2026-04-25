"""Pydantic models for tenant branding & white-label configuration."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrandingUpdate(BaseModel):
    """Input model for updating tenant branding."""

    company_name: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    sidebar_bg: str | None = None
    font_family: str | None = None
    custom_domain: str | None = None
    subdomain: str | None = None
    email_from_name: str | None = None
    footer_text: str | None = None
    support_email: str | None = None
    support_url: str | None = None
    hide_datapulse_branding: bool | None = None
    custom_login_bg: str | None = None
    # POS letterhead fields (added in migration 116)
    pos_branch_name: str | None = None
    pos_branch_address: str | None = None
    pos_tax_number: str | None = None
    pos_cr_number: str | None = None
    pos_invoice_label: str | None = None


class BrandingResponse(BaseModel):
    """Full branding configuration for a tenant."""

    model_config = ConfigDict(frozen=True)

    tenant_id: int
    company_name: str = "DataPulse"
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = "#4F46E5"
    accent_color: str = "#D97706"
    sidebar_bg: str | None = None
    font_family: str = "Inter"
    custom_domain: str | None = None
    subdomain: str | None = None
    email_from_name: str | None = None
    email_logo_url: str | None = None
    footer_text: str | None = None
    support_email: str | None = None
    support_url: str | None = None
    hide_datapulse_branding: bool = False
    custom_login_bg: str | None = None
    # POS letterhead fields (migration 116)
    pos_branch_name: str | None = None
    pos_branch_address: str | None = None
    pos_tax_number: str | None = None
    pos_cr_number: str | None = None
    pos_invoice_label: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PublicBrandingResponse(BaseModel):
    """Public branding info (used on login page, no auth required)."""

    model_config = ConfigDict(frozen=True)

    company_name: str = "DataPulse"
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = "#4F46E5"
    accent_color: str = "#D97706"
    font_family: str = "Inter"
    hide_datapulse_branding: bool = False
    custom_login_bg: str | None = None
