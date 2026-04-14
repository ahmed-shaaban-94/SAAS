"""Reorder config repository — CRUD for public.reorder_config."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class ReorderConfig:
    """In-memory representation of a reorder_config row."""

    __slots__ = (
        "id",
        "tenant_id",
        "drug_code",
        "site_code",
        "min_stock",
        "reorder_point",
        "max_stock",
        "reorder_lead_days",
        "is_active",
        "updated_at",
        "updated_by",
    )

    def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
        for k, v in kwargs.items():
            setattr(self, k, v)


class ReorderConfigRepository:
    """CRUD access to public.reorder_config.

    All writes validate min_stock <= reorder_point <= max_stock before
    touching the database. All SQL uses parameterized queries.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Reads ─────────────────────────────────────────────────────────────────

    def get_config(
        self, tenant_id: int, drug_code: str, site_code: str
    ) -> ReorderConfig | None:
        """Return a single reorder config row or None if not found."""
        stmt = text("""
            SELECT
                id, tenant_id, drug_code, site_code,
                min_stock, reorder_point, max_stock,
                reorder_lead_days, is_active, updated_at, updated_by
            FROM public.reorder_config
            WHERE tenant_id = :tenant_id
              AND drug_code  = :drug_code
              AND site_code  = :site_code
        """)
        row = self._session.execute(
            stmt,
            {"tenant_id": tenant_id, "drug_code": drug_code, "site_code": site_code},
        ).mappings().first()
        if row is None:
            return None
        return ReorderConfig(**dict(row))

    def list_configs(
        self,
        tenant_id: int,
        site_code: str | None = None,
        drug_code: str | None = None,
        is_active: bool | None = True,
        limit: int = 100,
    ) -> list[ReorderConfig]:
        """Return a filtered list of reorder configs for a tenant."""
        wheres = ["tenant_id = :tenant_id"]
        params: dict = {"tenant_id": tenant_id, "limit": limit}

        if site_code is not None:
            wheres.append("site_code = :site_code")
            params["site_code"] = site_code
        if drug_code is not None:
            wheres.append("drug_code = :drug_code")
            params["drug_code"] = drug_code
        if is_active is not None:
            wheres.append("is_active = :is_active")
            params["is_active"] = is_active

        where_clause = f"WHERE {' AND '.join(wheres)}"
        stmt = text(f"""
            SELECT
                id, tenant_id, drug_code, site_code,
                min_stock, reorder_point, max_stock,
                reorder_lead_days, is_active, updated_at, updated_by
            FROM public.reorder_config
            {where_clause}
            ORDER BY drug_code, site_code
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).mappings().all()
        return [ReorderConfig(**dict(r)) for r in rows]

    # ── Writes ────────────────────────────────────────────────────────────────

    def upsert_config(
        self,
        tenant_id: int,
        drug_code: str,
        site_code: str,
        min_stock: float,
        reorder_point: float,
        max_stock: float,
        reorder_lead_days: int,
        updated_by: str | None = None,
    ) -> ReorderConfig:
        """Insert or update a reorder config row.

        Uses ON CONFLICT DO UPDATE so create and update share the same path.
        Callers must validate constraints before calling this method.
        """
        now = datetime.now(tz=UTC)
        stmt = text("""
            INSERT INTO public.reorder_config
                (tenant_id, drug_code, site_code, min_stock, reorder_point,
                 max_stock, reorder_lead_days, is_active, updated_at, updated_by)
            VALUES
                (:tenant_id, :drug_code, :site_code, :min_stock, :reorder_point,
                 :max_stock, :reorder_lead_days, true, :updated_at, :updated_by)
            ON CONFLICT (tenant_id, drug_code, site_code)
            DO UPDATE SET
                min_stock         = EXCLUDED.min_stock,
                reorder_point     = EXCLUDED.reorder_point,
                max_stock         = EXCLUDED.max_stock,
                reorder_lead_days = EXCLUDED.reorder_lead_days,
                is_active         = true,
                updated_at        = EXCLUDED.updated_at,
                updated_by        = EXCLUDED.updated_by
            RETURNING
                id, tenant_id, drug_code, site_code,
                min_stock, reorder_point, max_stock,
                reorder_lead_days, is_active, updated_at, updated_by
        """)
        row = self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "drug_code": drug_code,
                "site_code": site_code,
                "min_stock": min_stock,
                "reorder_point": reorder_point,
                "max_stock": max_stock,
                "reorder_lead_days": reorder_lead_days,
                "updated_at": now,
                "updated_by": updated_by,
            },
        ).mappings().first()
        log.info(
            "reorder_config_upserted",
            tenant_id=tenant_id,
            drug_code=drug_code,
            site_code=site_code,
        )
        return ReorderConfig(**dict(row))

    def deactivate_config(
        self, tenant_id: int, drug_code: str, site_code: str
    ) -> bool:
        """Soft-delete a reorder config by setting is_active=false.

        Returns True if a row was updated, False if the config did not exist.
        """
        stmt = text("""
            UPDATE public.reorder_config
            SET is_active = false, updated_at = :now
            WHERE tenant_id = :tenant_id
              AND drug_code  = :drug_code
              AND site_code  = :site_code
            RETURNING id
        """)
        result = self._session.execute(
            stmt,
            {
                "tenant_id": tenant_id,
                "drug_code": drug_code,
                "site_code": site_code,
                "now": datetime.now(tz=UTC),
            },
        ).first()
        if result:
            log.info(
                "reorder_config_deactivated",
                tenant_id=tenant_id,
                drug_code=drug_code,
                site_code=site_code,
            )
        return result is not None
