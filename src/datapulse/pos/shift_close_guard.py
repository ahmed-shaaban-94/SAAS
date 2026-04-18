"""Server-enforced shift-close guard — dual-side check.

Close is a joint client + server invariant:

* **Client claim check:** request body carries
  ``local_unresolved = { count, digest }``; non-zero count → 409.
* **Server-side check:** `pos.transactions.commit_confirmed_at IS NULL`
  count for the shift must be zero; non-zero → 409 regardless of what the
  client claimed.

Every outcome (accepted/rejected_client/rejected_server) is recorded in
``pos.shifts_close_attempts`` for forensic audit.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §3.6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

GuardOutcome = Literal["accepted", "rejected_client", "rejected_server"]


@dataclass(frozen=True)
class GuardResult:
    outcome: GuardOutcome
    server_incomplete_count: int = 0


def enforce_close_guard(
    session: Session,
    *,
    shift_id: int,
    tenant_id: int,
    terminal_id: int,
    claim_count: int,
    claim_digest: str,
) -> GuardResult:
    """Apply client + server checks. Records a forensic row on every outcome.

    Raises ``HTTPException(409)`` on rejection with detail either
    ``provisional_work_pending`` or ``server_side_incomplete_transactions``.
    Returns an accepted ``GuardResult`` on pass.
    """
    # Client claim check
    if claim_count > 0:
        session.execute(
            text(
                """INSERT INTO pos.shifts_close_attempts
                     (shift_id, tenant_id, terminal_id, outcome,
                      claimed_unresolved_count, claimed_unresolved_digest, rejection_reason)
                   VALUES (:s, :t, :term, 'rejected_client', :c, :d, 'provisional_work_pending')"""
            ),
            {
                "s": shift_id,
                "t": tenant_id,
                "term": terminal_id,
                "c": claim_count,
                "d": claim_digest,
            },
        )
        raise HTTPException(status_code=409, detail="provisional_work_pending")

    # Server-side incomplete-transaction check
    incomplete = (
        session.execute(
            text(
                """SELECT count(*) FROM pos.transactions
                    WHERE shift_id = :s AND tenant_id = :t
                      AND terminal_id = :term AND commit_confirmed_at IS NULL"""
            ),
            {"s": shift_id, "t": tenant_id, "term": terminal_id},
        ).scalar()
        or 0
    )

    if incomplete > 0:
        session.execute(
            text(
                """INSERT INTO pos.shifts_close_attempts
                     (shift_id, tenant_id, terminal_id, outcome,
                      claimed_unresolved_count, claimed_unresolved_digest,
                      server_incomplete_count, rejection_reason)
                   VALUES (:s, :t, :term, 'rejected_server', :c, :d, :inc,
                           'server_side_incomplete_transactions')"""
            ),
            {
                "s": shift_id,
                "t": tenant_id,
                "term": terminal_id,
                "c": claim_count,
                "d": claim_digest,
                "inc": int(incomplete),
            },
        )
        raise HTTPException(status_code=409, detail="server_side_incomplete_transactions")

    session.execute(
        text(
            """INSERT INTO pos.shifts_close_attempts
                 (shift_id, tenant_id, terminal_id, outcome,
                  claimed_unresolved_count, claimed_unresolved_digest)
               VALUES (:s, :t, :term, 'accepted', :c, :d)"""
        ),
        {"s": shift_id, "t": tenant_id, "term": terminal_id, "c": claim_count, "d": claim_digest},
    )
    return GuardResult(outcome="accepted", server_incomplete_count=0)
