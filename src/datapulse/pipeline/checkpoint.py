"""Checkpoint management for pipeline runs.

Reads and writes checkpoint data in the pipeline_runs.metadata JSONB column,
enabling runs to resume from the last successful stage.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from datapulse.logging import get_logger

log = get_logger(__name__)


def build_empty_checkpoint() -> dict[str, Any]:
    """Return an empty checkpoint structure."""
    return {
        "last_successful_stage": None,
        "completed_stages": [],
        "stage_timings": {},
        "retry_history": [],
    }


def mark_stage_complete(
    metadata: dict[str, Any],
    stage: str,
    duration_seconds: float,
) -> dict[str, Any]:
    """Record a stage as successfully completed in the checkpoint.

    Returns a new metadata dict (does not mutate the input).
    """
    meta = {**metadata}
    checkpoint = {**meta.get("checkpoint", build_empty_checkpoint())}
    completed = list(checkpoint.get("completed_stages", []))
    timings = dict(checkpoint.get("stage_timings", {}))

    if stage not in completed:
        completed.append(stage)

    timings[stage] = {
        "completed_at": datetime.now(UTC).isoformat(),
        "duration_s": round(duration_seconds, 2),
    }

    checkpoint["last_successful_stage"] = stage
    checkpoint["completed_stages"] = completed
    checkpoint["stage_timings"] = timings
    meta["checkpoint"] = checkpoint
    return meta


def record_retry(
    metadata: dict[str, Any],
    stage: str,
    attempt: int,
    error: str,
) -> dict[str, Any]:
    """Record a retry attempt in the checkpoint.

    Returns a new metadata dict (does not mutate the input).
    """
    meta = {**metadata}
    checkpoint = {**meta.get("checkpoint", build_empty_checkpoint())}
    history = list(checkpoint.get("retry_history", []))

    history.append(
        {
            "stage": stage,
            "attempt": attempt,
            "error": error[:200],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

    checkpoint["retry_history"] = history
    meta["checkpoint"] = checkpoint
    return meta


def get_last_successful_stage(metadata: dict[str, Any]) -> str | None:
    """Extract the last successfully completed stage from metadata."""
    checkpoint = metadata.get("checkpoint", {})
    return checkpoint.get("last_successful_stage")


def get_completed_stages(metadata: dict[str, Any]) -> list[str]:
    """Extract the list of completed stages from metadata."""
    checkpoint = metadata.get("checkpoint", {})
    return list(checkpoint.get("completed_stages", []))
