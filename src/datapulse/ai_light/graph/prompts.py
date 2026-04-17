"""V2 prompt templates for LangGraph AI-Light nodes.

Extends the V1 prompts in ai_light/prompts.py with structured JSON output
requirements and prompt versioning for A/B capability.
"""

from __future__ import annotations

import re as _re

PROMPT_VERSION = "v2.0"

# Reuse sanitize from parent module — kept here to avoid circular imports.
_CONTROL_CHARS_RE = _re.compile(r"[\x00-\x1f\x7f-\x9f]")
_INJECTION_DELIMITERS_RE = _re.compile(r"[<>\[\]{}|\\`]")
_INJECTION_PREFIXES_RE = _re.compile(
    r"(?i)(ignore\s+(previous|above)|system\s*:|<\s*/?\s*system|you\s+are\s+now)"
)


def _sanitize_for_prompt(text: str, max_len: int = 100) -> str:
    """Strip control chars, prompt injection markers, and truncate user-controlled text."""
    cleaned = _CONTROL_CHARS_RE.sub(" ", text)
    cleaned = _INJECTION_DELIMITERS_RE.sub("", cleaned)
    cleaned = _INJECTION_PREFIXES_RE.sub("", cleaned)
    return cleaned.strip()[:max_len]


SYSTEM_PROMPT_V2 = (
    "You are a business analytics assistant for DataPulse, a pharma/sales analytics platform. "
    "Analyze sales data and provide concise, actionable insights in English. "
    "Keep responses data-driven. Currency is EGP (Egyptian Pounds). "
    "When asked for JSON, return ONLY the JSON object — no markdown, no extra text."
)

SUMMARY_PROMPT = """\
Analyze the following sales data and return a JSON object with exactly two keys:
- "narrative": a concise executive summary paragraph (3-5 sentences, no markdown headers)
- "highlights": an array of 3-5 short bullet-point strings

**KPI Snapshot (prompt_version={prompt_version}):**
- Today's Gross Sales: {today_gross} EGP
- Month-to-Date: {mtd_gross} EGP
- Year-to-Date: {ytd_gross} EGP
- MoM Growth: {mom_growth}%
- YoY Growth: {yoy_growth}%
- Daily Transactions: {daily_transactions}
- Daily Customers: {daily_customers}

**Top 5 Products by Revenue:**
{top_products}

**Top 5 Customers by Revenue:**
{top_customers}

Return ONLY the JSON object. Example:
{{"narrative": "...", "highlights": ["...", "..."]}}"""
