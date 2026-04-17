"""Encrypted credential storage for the Control Center.

Uses pgcrypto pgp_sym_encrypt / pgp_sym_decrypt to store connector
passwords at rest in the source_credentials table.

Security rules (non-negotiable):
  - The plain-text credential value is NEVER logged — not even truncated.
  - The encrypted_value column is NEVER included in any Pydantic response model.
  - If settings.control_center_creds_key is empty, all credential operations
    raise ValueError immediately — fail-fast behaviour.
  - All SQL uses parameterized queries (SQLAlchemy text() with :params).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.core.config import get_settings
from datapulse.logging import get_logger

log = get_logger(__name__)


def _get_key() -> str:
    """Return the symmetric encryption key from settings.

    Raises:
        ValueError: When CONTROL_CENTER_CREDS_KEY is empty.
    """
    key = get_settings().control_center_creds_key
    if not key:
        raise ValueError(
            "CONTROL_CENTER_CREDS_KEY is not set. "
            "Set this environment variable before using credential operations."
        )
    return key


def store_credential(
    session: Session,
    *,
    connection_id: int,
    tenant_id: int,
    cred_type: str,
    plain_value: str,
) -> int:
    """Encrypt and persist a credential. Returns the source_credentials row id.

    If a credential of the same (connection_id, cred_type) already exists,
    it is updated in-place (UPSERT via ON CONFLICT).

    Args:
        session:       SQLAlchemy session (tenant-scoped for RLS).
        connection_id: The source_connections row this credential belongs to.
        tenant_id:     The owning tenant (enforces RLS boundary).
        cred_type:     Credential kind: 'password', 'service_account', etc.
        plain_value:   The plain-text secret to encrypt. NEVER logged.

    Returns:
        The integer primary key of the stored row.

    Raises:
        ValueError: When CONTROL_CENTER_CREDS_KEY is not configured.
    """
    key = _get_key()

    stmt = text("""
        INSERT INTO public.source_credentials
            (tenant_id, connection_id, credential_type, encrypted_value)
        VALUES (
            :tenant_id,
            :connection_id,
            :cred_type,
            pgp_sym_encrypt(:plain_value, :key)
        )
        ON CONFLICT (connection_id, credential_type)
        DO UPDATE SET
            encrypted_value = pgp_sym_encrypt(:plain_value, :key),
            updated_at = now()
        RETURNING id
    """)

    row = session.execute(
        stmt,
        {
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "cred_type": cred_type,
            "plain_value": plain_value,
            "key": key,
        },
    ).fetchone()

    if row is None:
        raise RuntimeError("store_credential: INSERT RETURNING returned no row")

    cred_id: int = row[0]
    log.info(
        "credential_stored",
        connection_id=connection_id,
        tenant_id=tenant_id,
        cred_type=cred_type,
        cred_id=cred_id,
        # plain_value deliberately excluded from log
    )
    return cred_id


def load_credential(
    session: Session,
    *,
    connection_id: int,
    tenant_id: int,
    cred_type: str = "password",
) -> str | None:
    """Decrypt and return the plain-text credential, or None if not stored.

    Args:
        session:       SQLAlchemy session (tenant-scoped for RLS).
        connection_id: The source_connections row to load credentials for.
        tenant_id:     The owning tenant (enforces RLS boundary).
        cred_type:     Credential kind to load (default 'password').

    Returns:
        The decrypted plain-text secret, or None when not found.
        NEVER logged — callers must treat the return value as a secret.

    Raises:
        ValueError: When CONTROL_CENTER_CREDS_KEY is not configured.
    """
    key = _get_key()

    stmt = text("""
        SELECT pgp_sym_decrypt(encrypted_value::bytea, :key) AS plain_value
        FROM public.source_credentials
        WHERE connection_id = :connection_id
          AND tenant_id = :tenant_id
          AND credential_type = :cred_type
        LIMIT 1
    """)

    row = session.execute(
        stmt,
        {
            "connection_id": connection_id,
            "tenant_id": tenant_id,
            "cred_type": cred_type,
            "key": key,
        },
    ).fetchone()

    if row is None:
        return None

    # plain_value is intentionally not logged
    return row[0]
