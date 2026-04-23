"""Exception handlers — registered in specificity order.

Handlers dispatch by the exception MRO (most specific match first), so the
*registration* order shown here mirrors specificity for readability even
though FastAPI doesn't require it. POS-specific handlers MUST be listed
before the generic ``DataPulseError`` catch-all so 409 / 403 responses are
not shadowed by the 400 fallback.
"""

import traceback

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from datapulse.core.exceptions import (
    DataPulseError,
    QuotaExceededError,
    TenantError,
    ValidationError,
)

logger = structlog.get_logger()


def install_exception_handlers(app: FastAPI) -> None:
    """Register every exception handler used by the app."""
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(QuotaExceededError)
    async def quota_exceeded_handler(request: Request, exc: QuotaExceededError) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": exc.message})

    @app.exception_handler(TenantError)
    async def tenant_error_handler(request: Request, exc: TenantError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    # POS-specific exception handlers — must be registered BEFORE the generic
    # DataPulseError handler so they take precedence over the catch-all 400.
    from datapulse.pos.exceptions import (
        InsufficientStockError,
        PharmacistVerificationRequiredError,
        ShiftNotOpenError,
        TerminalNotActiveError,
        VoidNotAllowedError,
        WhatsAppDeliveryFailedError,
        WhatsAppDisabledError,
    )

    @app.exception_handler(InsufficientStockError)
    async def pos_insufficient_stock_handler(
        request: Request, exc: InsufficientStockError
    ) -> JSONResponse:
        logger.info("pos.insufficient_stock", detail=exc.detail)
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(TerminalNotActiveError)
    async def pos_terminal_not_active_handler(
        request: Request, exc: TerminalNotActiveError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(PharmacistVerificationRequiredError)
    async def pos_pharmacist_required_handler(
        request: Request, exc: PharmacistVerificationRequiredError
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.message})

    @app.exception_handler(VoidNotAllowedError)
    async def pos_void_not_allowed_handler(
        request: Request, exc: VoidNotAllowedError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(ShiftNotOpenError)
    async def pos_shift_not_open_handler(request: Request, exc: ShiftNotOpenError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(WhatsAppDisabledError)
    async def pos_whatsapp_disabled_handler(
        request: Request, exc: WhatsAppDisabledError
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @app.exception_handler(WhatsAppDeliveryFailedError)
    async def pos_whatsapp_delivery_failed_handler(
        request: Request, exc: WhatsAppDeliveryFailedError
    ) -> JSONResponse:
        logger.warning("pos.whatsapp.delivery_failed", detail=exc.detail)
        return JSONResponse(status_code=502, content={"detail": exc.message})

    @app.exception_handler(DataPulseError)
    async def datapulse_error_handler(request: Request, exc: DataPulseError) -> JSONResponse:
        logger.warning("datapulse_error", error=exc.message, detail=exc.detail)
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            raise exc
        logger.error(
            "unhandled_exception",
            method=request.method,
            path=request.url.path,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
