"""Prompt templates for AI-Light OpenRouter calls."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a business analytics assistant for DataPulse, a pharma/sales analytics platform. "
    "You analyze sales data and provide concise, actionable insights in English. "
    "Keep responses short and data-driven. Use bullet points for highlights. "
    "Currency is EGP (Egyptian Pounds). All numbers should be formatted clearly."
)

SUMMARY_PROMPT = """\
Analyze the following sales data and write a brief executive summary (3-5 sentences) \
with 3-5 bullet-point highlights.

**KPI Snapshot:**
- Today's Net Sales: {today_net} EGP
- Month-to-Date: {mtd_net} EGP
- Year-to-Date: {ytd_net} EGP
- MoM Growth: {mom_growth}%
- YoY Growth: {yoy_growth}%
- Daily Transactions: {daily_transactions}
- Daily Customers: {daily_customers}

**Top 5 Products by Revenue:**
{top_products}

**Top 5 Customers by Revenue:**
{top_customers}

Write a concise summary and highlights. Do NOT use markdown headers."""

ANOMALY_PROMPT = """\
Analyze the following daily sales time series and identify any anomalies \
(unusual spikes, drops, or pattern breaks). For each anomaly, provide the date, \
what was unusual, and severity (low/medium/high).

**Daily Sales Data (last 30 days):**
{daily_data}

**Statistics:**
- Average: {avg} EGP
- Std Dev: {std_dev} EGP
- Min: {min_val} EGP
- Max: {max_val} EGP

Return a JSON array of anomalies. Each object must have: \
"date", "description", "severity". Return empty array [] if no anomalies found.
Only return the JSON array, no other text."""

CHANGES_PROMPT = """\
Compare these two periods and explain the key changes in business performance.

**Current Period ({current_period}):**
- Net Sales: {current_net} EGP
- Transactions: {current_txns}
- Customers: {current_customers}

**Previous Period ({previous_period}):**
- Net Sales: {previous_net} EGP
- Transactions: {previous_txns}
- Customers: {previous_customers}

**Top Movers (products with biggest change):**
{top_movers}

Write a concise narrative (3-4 sentences) explaining what changed and why. \
Focus on the most impactful changes."""
