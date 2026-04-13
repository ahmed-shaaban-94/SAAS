"""Pure, deterministic validation engine for Control Center drafts.

``validate_draft()`` has no I/O side effects — it operates on plain dicts
and returns a ``ValidationReport``. This makes it 100% unit-testable without
any database or file access.

Checks (8 total, per plan §8):
  1. Required canonical fields covered by mapping
  2. Type compatibility (source cast → canonical type with coercion rules)
  3. No duplicate / conflicting canonical targets in mapping
  4. Null ratio threshold (from profile quality_thresholds)
  5. Row-count delta vs prior release (warn if >20% shrink)
  6. Key uniqueness — profile-declared keys must appear in mapping
  7. Output contract adherence (every canonical required field present)
  8. Tenant isolation (no embedded tenant_id literals in mapping config)
"""

from __future__ import annotations

import json
from typing import Any

from datapulse.control_center.models import ValidationIssue, ValidationReport

# ── Type coercion rules ───────────────────────────────────────
# Maps a declared cast type to the set of canonical types it can produce.
# A source value with cast X can satisfy a canonical column of type Y
# only if Y is in _COERCIBLE[X].
_COERCIBLE: dict[str, frozenset[str]] = {
    "integer": frozenset({"integer", "numeric", "string"}),
    "numeric": frozenset({"numeric", "string"}),
    "date": frozenset({"date", "string"}),
    "timestamp": frozenset({"timestamp", "date", "string"}),
    "boolean": frozenset({"boolean", "string"}),
    "string": frozenset({"string"}),
}


def _is_coercible(source_cast: str, canonical_type: str) -> bool:
    allowed = _COERCIBLE.get(source_cast.lower(), frozenset({"string"}))
    return canonical_type.lower() in allowed


# ── Public API ────────────────────────────────────────────────


def validate_draft(
    *,
    mapping_columns: list[dict[str, Any]],
    profile_config: dict[str, Any],
    canonical_schema: dict[str, Any],
    source_preview: dict[str, Any] | None = None,
    prior_release_snapshot: dict[str, Any] | None = None,
    tenant_id: int,
) -> ValidationReport:
    """Run all validation checks and return a ``ValidationReport``.

    Args:
        mapping_columns:        List of ``{source, canonical, cast}`` dicts from
                                the mapping template's ``mapping_json.columns``.
        profile_config:         Full ``config_json`` of the pipeline profile.
                                Expected keys: ``quality_thresholds`` (dict),
                                ``keys`` (list[str]).
        canonical_schema:       ``json_schema`` blob from ``canonical_domains``.
                                Expected keys: ``required_fields`` (list[str]),
                                ``types`` (dict[str, str]).
        source_preview:         Preview result from ``preview_connection()`` or
                                ``preview_draft()``.  When ``None``, checks 4 & 5
                                are skipped.
        prior_release_snapshot: ``snapshot_json`` of the most recent published
                                release.  When ``None``, check 5 is skipped.
        tenant_id:              Current tenant's integer id.

    Returns:
        ``ValidationReport`` with ``ok=True`` when there are no errors.
        Warnings do not affect ``ok``.
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    # Build lookup: canonical_name → full column dict
    canonical_map: dict[str, dict[str, Any]] = {}
    for col in mapping_columns:
        c_name = col.get("canonical", "")
        if c_name:
            canonical_map[c_name] = col

    # ── Check 1 & 7: Required fields covered ─────────────────
    required_fields: list[str] = canonical_schema.get("required_fields", [])
    for field in required_fields:
        if field not in canonical_map:
            errors.append(
                ValidationIssue(
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Required canonical field '{field}' is not mapped",
                    field=field,
                )
            )

    # ── Check 3: Duplicate canonical targets ──────────────────
    seen: dict[str, int] = {}
    for col in mapping_columns:
        c_name = col.get("canonical", "")
        if c_name:
            seen[c_name] = seen.get(c_name, 0) + 1
    for c_name, count in seen.items():
        if count > 1:
            errors.append(
                ValidationIssue(
                    code="DUPLICATE_MAPPING",
                    message=(f"Canonical field '{c_name}' is targeted by {count} source columns"),
                    field=c_name,
                )
            )

    # ── Check 2: Type compatibility ───────────────────────────
    canonical_types: dict[str, str] = canonical_schema.get("types", {})
    for col in mapping_columns:
        c_name = col.get("canonical", "")
        declared_cast = (col.get("cast") or "string").lower()
        expected_type = canonical_types.get(c_name, "string").lower()
        if not _is_coercible(declared_cast, expected_type):
            errors.append(
                ValidationIssue(
                    code="TYPE_INCOMPATIBLE",
                    message=(
                        f"Cast '{declared_cast}' for '{c_name}' cannot produce "
                        f"canonical type '{expected_type}'"
                    ),
                    field=c_name,
                )
            )

    # ── Check 4: Null ratio threshold ────────────────────────
    if source_preview is not None:
        null_ratios: dict[str, float] = source_preview.get("null_ratios", {})
        thresholds: dict[str, Any] = profile_config.get("quality_thresholds", {})
        global_threshold: float = float(thresholds.get("max_null_ratio", 0.20))
        for col in mapping_columns:
            c_name = col.get("canonical", "")
            src_name = col.get("source", "")
            ratio = null_ratios.get(src_name, null_ratios.get(c_name, 0.0))
            field_threshold = float(thresholds.get(f"max_null_ratio.{c_name}", global_threshold))
            if ratio > field_threshold:
                warnings.append(
                    ValidationIssue(
                        code="HIGH_NULL_RATIO",
                        message=(
                            f"Column '{c_name}' has {ratio:.1%} nulls "
                            f"(threshold: {field_threshold:.1%})"
                        ),
                        field=c_name,
                    )
                )

    # ── Check 5: Row-count delta vs prior release ────────────
    if source_preview is not None and prior_release_snapshot is not None:
        current_count = int(source_preview.get("row_count_estimate", 0))
        prior_count = int(prior_release_snapshot.get("row_count_estimate", 0))
        if prior_count > 0 and current_count < int(prior_count * 0.80):
            pct = (1.0 - current_count / prior_count) * 100
            warnings.append(
                ValidationIssue(
                    code="ROW_COUNT_SHRINK",
                    message=(
                        f"Row count decreased by {pct:.1f}% vs prior release "
                        f"({current_count:,} vs {prior_count:,})"
                    ),
                    field=None,
                )
            )

    # ── Check 6: Profile-declared keys are mapped ────────────
    declared_keys: list[str] = profile_config.get("keys", [])
    for key in declared_keys:
        if key not in canonical_map:
            errors.append(
                ValidationIssue(
                    code="KEY_NOT_MAPPED",
                    message=(
                        f"Profile key '{key}' must appear as a canonical target in the mapping"
                    ),
                    field=key,
                )
            )

    # ── Check 8: Tenant isolation ────────────────────────────
    # Heuristic: the mapping config must never embed a tenant_id literal,
    # which could create accidental cross-tenant filtering.
    mapping_str = json.dumps(mapping_columns)
    if '"tenant_id"' in mapping_str:
        warnings.append(
            ValidationIssue(
                code="TENANT_ISOLATION_RISK",
                message=(
                    "Mapping contains embedded 'tenant_id' key — "
                    "verify no cross-tenant references exist"
                ),
                field=None,
            )
        )

    return ValidationReport(ok=len(errors) == 0, errors=errors, warnings=warnings)
