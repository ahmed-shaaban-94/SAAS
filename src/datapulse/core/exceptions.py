"""Business exception hierarchy for DataPulse.

All domain-level errors inherit from ``DataPulseError``.  FastAPI exception
handlers registered in ``api/app.py`` map each subclass to an appropriate
HTTP status code and user-facing message.

Usage::

    from datapulse.core.exceptions import QuotaExceededError
    raise QuotaExceededError("Monthly upload limit reached")
"""

from __future__ import annotations


class DataPulseError(Exception):
    """Base class for all DataPulse business exceptions.

    Attributes:
        message: Human-readable description of the error.
        detail:  Optional extra context (not exposed to end-users).
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class ValidationError(DataPulseError):
    """Raised when input data fails business-rule validation.

    Maps to HTTP 422 Unprocessable Entity.
    Distinct from Pydantic's ValidationError (schema validation) — this
    covers semantic validation (e.g. end_date before start_date).
    """


class QuotaExceededError(DataPulseError):
    """Raised when a tenant exceeds a plan-level resource quota.

    Maps to HTTP 429 Too Many Requests.
    Examples: monthly upload limit, API call rate, row count threshold.
    """


class TenantError(DataPulseError):
    """Raised for tenant-isolation or multi-tenancy configuration errors.

    Maps to HTTP 403 Forbidden.
    Examples: tenant not found, tenant suspended, cross-tenant access attempt.
    """
