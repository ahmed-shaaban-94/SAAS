"""Pharmacist PIN-verification flow for controlled-substance dispensing."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PharmacistVerifyRequest(BaseModel):
    """Request body to verify a pharmacist for controlled substance dispensing."""

    model_config = ConfigDict(frozen=True)

    pharmacist_id: str
    # PIN or credential used for verification (not stored, checked in-memory)
    credential: str = Field(min_length=4, max_length=128)
    drug_code: str


class PharmacistVerifyResponse(BaseModel):
    """Response from a successful pharmacist PIN verification.

    The ``token`` is a short-lived HMAC-signed bearer that must be passed
    as ``pharmacist_id`` in subsequent ``add_item`` calls for the same
    ``drug_code``.  Tokens expire after ``TOKEN_TTL_SECONDS`` (5 minutes).
    """

    model_config = ConfigDict(frozen=True)

    token: str
    pharmacist_id: str
    drug_code: str
    expires_at: datetime
