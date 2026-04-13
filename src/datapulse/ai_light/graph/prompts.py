"""Versioned prompts for AI-Light LangGraph nodes.

All LLM prompts are centralised here so they can be versioned, A/B tested,
and tuned without touching node logic.

``PROMPT_VERSION`` is embedded in the Redis cache key so a prompt upgrade
automatically invalidates stale cached responses.

Prompt inventory
----------------
``SYSTEM_SUMMARY``    — System prompt for the summary insight type.
``SYSTEM_ANOMALIES``  — System prompt for the anomalies insight type.
``SYSTEM_CHANGES``    — System prompt for the changes insight type.
``SYSTEM_DEEP_DIVE``  — System prompt for the deep_dive ReAct agent.
``USER_SUMMARY``      — User-turn template for summary (accepts ``{data}``).
``USER_ANOMALIES``    — User-turn template for anomalies (accepts ``{data}``).
``USER_CHANGES``      — User-turn template for changes (accepts ``{data}``).
``RETRY_SUFFIX``      — Appended to the user turn on validation-retry attempts.

Implementation note (Phase A-1): all prompt strings are empty placeholders.
Phase A will port the existing prompts from ``src/datapulse/ai_light/prompts.py``
and extend them for the graph validation contract.
"""

from __future__ import annotations

# Bump this constant whenever any prompt string changes.
# It is included in the Redis cache key to auto-invalidate stale responses.
PROMPT_VERSION: str = "v2.0-placeholder"

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_SUMMARY: str = ""
"""System prompt for the summary insight type. Defined in Phase A."""

SYSTEM_ANOMALIES: str = ""
"""System prompt for the anomalies insight type. Defined in Phase B."""

SYSTEM_CHANGES: str = ""
"""System prompt for the changes insight type. Defined in Phase B."""

SYSTEM_DEEP_DIVE: str = ""
"""System prompt for the deep_dive ReAct agent. Defined in Phase C."""

# ---------------------------------------------------------------------------
# User-turn templates
# ---------------------------------------------------------------------------

USER_SUMMARY: str = ""
"""User-turn template for summary. Accepts ``{data}`` placeholder. Defined in Phase A."""

USER_ANOMALIES: str = ""
"""User-turn template for anomalies. Accepts ``{data}`` placeholder. Defined in Phase B."""

USER_CHANGES: str = ""
"""User-turn template for changes. Accepts ``{data}`` placeholder. Defined in Phase B."""

# ---------------------------------------------------------------------------
# Retry suffix
# ---------------------------------------------------------------------------

RETRY_SUFFIX: str = (
    "\n\nYour previous response did not match the required JSON schema. "
    "Please return ONLY valid JSON conforming to the schema, with no prose."
)
"""Appended to the user turn on validation-retry attempts."""
