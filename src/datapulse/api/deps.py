"""FastAPI dependency injection for database sessions and services."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from datapulse.expiry.service import ExpiryService
    from datapulse.inventory.service import InventoryService

import structlog
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from datapulse.ai_light.service import AILightService
from datapulse.analytics.advanced_repository import AdvancedRepository
from datapulse.analytics.affinity_repository import AffinityRepository
from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.churn_repository import ChurnRepository
from datapulse.analytics.comparison_repository import ComparisonRepository
from datapulse.analytics.customer_health import CustomerHealthRepository
from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.diagnostics import DiagnosticsRepository
from datapulse.analytics.feature_store_repository import FeatureStoreRepository
from datapulse.analytics.hierarchy_repository import HierarchyRepository
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.analytics.search_service import SearchService
from datapulse.analytics.service import AnalyticsService

# Service imports for newly added factory functions
from datapulse.annotations.service import AnnotationService
from datapulse.api.auth import UserClaims, get_current_user, require_api_key
from datapulse.billing.plans import PlanLimits, get_plan_limits
from datapulse.billing.repository import BillingRepository
from datapulse.billing.service import BillingService
from datapulse.billing.stripe_client import StripeClient
from datapulse.cache import current_tenant_id
from datapulse.config import get_settings
from datapulse.core.db import (  # noqa: F401 (get_engine re-exported for health.py)
    get_engine,
    get_session_factory,
)
from datapulse.forecasting.repository import ForecastingRepository
from datapulse.forecasting.service import ForecastingService
from datapulse.pipeline.executor import PipelineExecutor
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.quality_service import QualityService
from datapulse.pipeline.repository import PipelineRepository
from datapulse.pipeline.service import PipelineService
from datapulse.purchase_orders.repository import PurchaseOrderRepository
from datapulse.purchase_orders.service import PurchaseOrderService
from datapulse.reports.schedule_service import ScheduleService
from datapulse.suppliers.repository import SuppliersRepository
from datapulse.suppliers.service import SuppliersService

logger = structlog.get_logger()


def get_plain_session() -> Generator[Session, None, None]:
    """Create a plain DB session with no tenant scoping.

    Intended for public endpoints that do not require authentication or
    row-level security (e.g. lead capture).  Does NOT set app.tenant_id.
    """
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        yield session
        session.commit()
    except SQLAlchemyError:
        logger.exception("db_session_error", session_type="plain")
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """Create a DB session with tenant_id='1' (legacy, for non-authenticated use).

    .. deprecated::
        Use ``get_tenant_session`` instead.  This function bypasses authentication
        and hardcodes tenant_id='1', which is unsafe for multi-tenant deployments.
        It is kept only for backward compatibility in test overrides.
    """
    import warnings

    settings = get_settings()
    env = settings.sentry_environment
    if env not in ("development", "test"):
        logger.error(
            "get_db_session_called_in_production",
            environment=env,
            detail="get_db_session bypasses auth and hardcodes tenant_id='1' "
            "— use get_tenant_session instead",
        )
        raise RuntimeError("get_db_session is not allowed in production — use get_tenant_session")
    warnings.warn(
        "get_db_session() is deprecated — use get_tenant_session() for auth-scoped access",
        DeprecationWarning,
        stacklevel=2,
    )

    structlog.contextvars.bind_contextvars(tenant_id="1")
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": "1"})
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        yield session
        session.commit()
    except SQLAlchemyError:
        logger.exception("db_session_error", session_type="legacy")
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")


def get_tenant_session(
    user: Annotated[UserClaims, Depends(get_current_user)],
) -> Generator[Session, None, None]:
    """Create a DB session scoped to the authenticated user's tenant.

    Extracts tenant_id from the JWT claims and sets it via SET LOCAL
    so that PostgreSQL RLS policies filter data automatically.
    """
    tenant_id = user.get("tenant_id") or "1"
    current_tenant_id.set(str(tenant_id))
    structlog.contextvars.bind_contextvars(tenant_id=str(tenant_id))
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        session.execute(text("SET LOCAL statement_timeout = '30s'"))
        yield session
        session.commit()
    except SQLAlchemyError:
        logger.exception("db_session_error", session_type="tenant", tenant_id=str(tenant_id))
        session.rollback()
        raise
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        structlog.contextvars.unbind_contextvars("tenant_id")


# Type aliases for FastAPI dependency injection
SessionDep = Annotated[Session, Depends(get_tenant_session)]
CurrentUser = Annotated[UserClaims, Depends(get_current_user)]


def get_analytics_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AnalyticsService:
    repo = AnalyticsRepository(session)
    detail_repo = DetailRepository(session)
    breakdown_repo = BreakdownRepository(session)
    comparison_repo = ComparisonRepository(session)
    hierarchy_repo = HierarchyRepository(session)
    advanced_repo = AdvancedRepository(session)
    diagnostics_repo = DiagnosticsRepository(session)
    customer_health_repo = CustomerHealthRepository(session)
    feature_store_repo = FeatureStoreRepository(session)
    churn_repo = ChurnRepository(session)
    affinity_repo = AffinityRepository(session)
    return AnalyticsService(
        repo,
        detail_repo,
        breakdown_repo,
        comparison_repo,
        hierarchy_repo,
        advanced_repo,
        diagnostics_repo,
        customer_health_repo,
        feature_store_repo,
        churn_repo=churn_repo,
        affinity_repo=affinity_repo,
    )


def get_pipeline_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> PipelineService:
    repo = PipelineRepository(session)
    quality_repo = QualityRepository(session)
    return PipelineService(repo, quality_repo=quality_repo)


def get_pipeline_executor() -> PipelineExecutor:
    settings = get_settings()
    return PipelineExecutor(settings=settings)


def get_quality_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> QualityService:
    repo = QualityRepository(session)
    settings = get_settings()
    return QualityService(repo, session, settings)


def get_forecasting_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ForecastingService:
    """Factory for forecasting service with feature store + forecast repository."""
    repo = ForecastingRepository(session)
    return ForecastingService(repo)


def get_ai_light_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AILightService:
    """Factory for AI-Light service.

    Returns AILightGraphService when AI_LIGHT_USE_LANGGRAPH=true,
    otherwise falls back to the legacy AILightService.
    """
    settings = get_settings()
    if settings.ai_light_use_langgraph:
        from datapulse.ai_light.graph_service import AILightGraphService  # lazy import

        return AILightGraphService(settings=settings, session=session)  # type: ignore[return-value]
    return AILightService(settings=settings, session=session)


def get_billing_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> BillingService:
    settings = get_settings()
    repo = BillingRepository(session)
    client = StripeClient(settings.stripe_secret_key)
    return BillingService(
        repo,
        client,
        price_to_plan=settings.stripe_price_to_plan_map,
        base_url=settings.billing_base_url,
    )


def get_tenant_plan_limits(
    user: CurrentUser,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> PlanLimits:
    """Dependency that returns the current tenant's plan limits.

    Inject into routes that need to enforce plan limits (e.g. pipeline trigger,
    data source creation). Raises HTTP 403 with a clear message when a limit
    would be exceeded.
    """
    tenant_id = int(user.get("tenant_id", "1"))
    repo = BillingRepository(session)
    plan = repo.get_tenant_plan(tenant_id)
    return get_plan_limits(plan)


# Alias for backwards compatibility — analytics.py and ai_light.py import this name
verify_api_key = require_api_key


def get_annotation_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AnnotationService:
    from datapulse.annotations.repository import AnnotationRepository

    return AnnotationService(AnnotationRepository(session))


def get_schedule_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ScheduleService:
    from datapulse.reports.schedule_repository import ScheduleRepository

    return ScheduleService(ScheduleRepository(session))


def get_search_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> SearchService:
    from datapulse.analytics.search_repository import SearchRepository

    return SearchService(SearchRepository(session))


def get_po_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> PurchaseOrderService:
    """Factory for PurchaseOrderService — wires repository to service."""
    return PurchaseOrderService(PurchaseOrderRepository(session))


def get_supplier_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> SuppliersService:
    """Factory for SuppliersService — wires repository to service."""
    return SuppliersService(SuppliersRepository(session))


def get_inventory_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> InventoryService:
    from datapulse.inventory.repository import InventoryRepository
    from datapulse.inventory.service import InventoryService

    repo = InventoryRepository(session)
    return InventoryService(repo)


def get_expiry_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ExpiryService:
    from datapulse.expiry.repository import ExpiryRepository
    from datapulse.expiry.service import ExpiryService

    repo = ExpiryRepository(session)
    return ExpiryService(repo)


def get_dispensing_service(
    session: Annotated[Session, Depends(get_tenant_session)],
):
    from datapulse.dispensing.repository import DispensingRepository
    from datapulse.dispensing.service import DispensingService

    repo = DispensingRepository(session)
    return DispensingService(repo)


def get_reorder_config_service(
    session: Annotated[Session, Depends(get_tenant_session)],
):
    from datapulse.inventory.reorder_repository import ReorderConfigRepository
    from datapulse.inventory.reorder_service import ReorderConfigService

    repo = ReorderConfigRepository(session)
    return ReorderConfigService(repo)


def get_pos_service(
    session: Annotated[Session, Depends(get_tenant_session)],
):
    """Factory for :class:`PosService` — wires repo + inventory + pharmacist verifier.

    Uses :class:`InventoryAdapter` to bridge the real :class:`InventoryService`
    and :class:`ExpiryService` (Plan A) to the async POS protocol, so stock
    checks, FEFO batch selection and movement persistence are real — no
    longer ``MockInventoryService``.

    The :class:`PharmacistVerifier` uses the repo's pin-lookup closure and
    the application secret key so the service stays dependency-free.
    """
    from datapulse.expiry.repository import ExpiryRepository
    from datapulse.expiry.service import ExpiryService
    from datapulse.inventory.repository import InventoryRepository
    from datapulse.inventory.service import InventoryService
    from datapulse.pos.inventory_adapter import InventoryAdapter
    from datapulse.pos.pharmacist_verifier import PharmacistVerifier
    from datapulse.pos.promotion_repository import PromotionRepository
    from datapulse.pos.repository import PosRepository
    from datapulse.pos.service import PosService
    from datapulse.pos.voucher_repository import VoucherRepository

    settings = get_settings()
    repo = PosRepository(session)
    inventory = InventoryAdapter(
        inventory_service=InventoryService(InventoryRepository(session)),
        expiry_service=ExpiryService(ExpiryRepository(session)),
    )
    # Use pipeline_webhook_secret as the HMAC signing key for pharmacist tokens.
    # Falls back to a non-empty dev stub so that dev mode still works.
    signing_secret = settings.pipeline_webhook_secret or "dev-pos-pharmacist-secret"
    verifier = PharmacistVerifier(
        secret_key=signing_secret,
        pin_lookup=repo.get_pharmacist_pin_hash,
    )
    voucher_repo = VoucherRepository(session)
    promotion_repo = PromotionRepository(session)
    return PosService(
        repo,
        inventory,
        verifier,
        voucher_repo=voucher_repo,
        promotion_repo=promotion_repo,
    )


def get_promotion_service(
    session: Annotated[Session, Depends(get_tenant_session)],
):
    """Factory for :class:`PromotionService` — wires the repo to the RLS session."""
    from datapulse.pos.promotion_repository import PromotionRepository
    from datapulse.pos.promotion_service import PromotionService

    return PromotionService(PromotionRepository(session))


def get_voucher_service(
    session: Annotated[Session, Depends(get_tenant_session)],
):
    """Factory for :class:`VoucherService` — wires a repository bound to the RLS session."""
    from datapulse.pos.voucher_repository import VoucherRepository
    from datapulse.pos.voucher_service import VoucherService

    return VoucherService(VoucherRepository(session))
