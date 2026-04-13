"""Pydantic output schemas for AI-Light LangGraph validation node.

The ``validate`` node checks ``llm_parsed_output`` against the schema for the
active ``insight_type``.  A validation failure increments ``validation_retries``
and routes back to ``analyze`` (max 2 retries) before falling back to the
stats-only narrative.

Schemas
-------
``SummaryOutput``   — validated output for the ``summary`` insight type.
``AnomalyOutput``   — validated output for the ``anomalies`` insight type.
``ChangesOutput``   — validated output for the ``changes`` insight type.
``DeepDiveOutput``  — validated output for the ``deep_dive`` composite endpoint.

Implementation note (Phase A-1): field definitions are placeholders.
Phase A will define the full field set matching the existing ``AISummary``,
``AnomalyReport``, and ``ChangeNarrative`` response shapes so the contract
tests can verify backward compatibility.
"""

from __future__ import annotations

from pydantic import BaseModel


class SummaryOutput(BaseModel):
    """Validated LLM output for the summary insight type.

    Fields TBD in Phase A — must match the existing ``AISummary`` response shape.
    """


class AnomalyOutput(BaseModel):
    """Validated LLM output for the anomalies insight type.

    Fields TBD in Phase B — must match the existing ``AnomalyReport`` response shape.
    """


class ChangesOutput(BaseModel):
    """Validated LLM output for the changes insight type.

    Fields TBD in Phase B — must match the existing ``ChangeNarrative`` response shape.
    """


class DeepDiveOutput(BaseModel):
    """Validated LLM output for the deep_dive composite endpoint.

    Fields TBD in Phase C — composite of narrative, highlights, anomalies,
    forecast deltas, and degraded flag.
    """
