"""Tests for the pure validation engine (control_center/validation.py).

All tests run without a database — pure logic only.
Target: 100% branch coverage.
"""

from __future__ import annotations

from datapulse.control_center.models import ValidationReport
from datapulse.control_center.validation import _is_coercible, validate_draft

# ── Helper fixtures ───────────────────────────────────────────

CANONICAL_SCHEMA = {
    "required_fields": ["order_id", "customer_id", "gross_amount", "order_date"],
    "types": {
        "order_id": "integer",
        "customer_id": "integer",
        "gross_amount": "numeric",
        "order_date": "date",
        "product_id": "integer",
    },
}

VALID_COLUMNS = [
    {"source": "id", "canonical": "order_id", "cast": "integer"},
    {"source": "cust", "canonical": "customer_id", "cast": "integer"},
    {"source": "total_rev", "canonical": "gross_amount", "cast": "numeric"},
    {"source": "sale_date", "canonical": "order_date", "cast": "date"},
]

PROFILE_CONFIG: dict = {"keys": ["order_id"], "quality_thresholds": {"max_null_ratio": 0.10}}


def _run(**kwargs) -> ValidationReport:
    defaults = dict(
        mapping_columns=VALID_COLUMNS,
        profile_config=PROFILE_CONFIG,
        canonical_schema=CANONICAL_SCHEMA,
        source_preview=None,
        prior_release_snapshot=None,
        tenant_id=1,
    )
    defaults.update(kwargs)
    return validate_draft(**defaults)


# ── Check 1 & 7: Required fields ──────────────────────────────


def test_all_required_fields_mapped():
    result = _run()
    assert result.ok is True
    assert result.errors == []


def test_missing_required_field():
    cols = [c for c in VALID_COLUMNS if c["canonical"] != "order_id"]
    result = _run(mapping_columns=cols)
    assert result.ok is False
    codes = [e.code for e in result.errors]
    assert "MISSING_REQUIRED_FIELD" in codes
    assert any(e.field == "order_id" for e in result.errors)


def test_all_required_fields_missing():
    result = _run(mapping_columns=[])
    assert result.ok is False
    # One error per required field
    assert len(result.errors) >= len(CANONICAL_SCHEMA["required_fields"])


# ── Check 3: Duplicate canonical targets ──────────────────────


def test_no_duplicates_ok():
    result = _run()
    assert result.ok is True


def test_duplicate_canonical_target():
    cols = VALID_COLUMNS + [{"source": "order_num", "canonical": "order_id", "cast": "integer"}]
    result = _run(mapping_columns=cols)
    assert result.ok is False
    codes = [e.code for e in result.errors]
    assert "DUPLICATE_MAPPING" in codes


# ── Check 2: Type compatibility ───────────────────────────────


def test_type_compatible_ok():
    result = _run()
    assert result.ok is True


def test_type_incompatible():
    bad_cols = [
        {"source": "id", "canonical": "order_id", "cast": "boolean"},  # not allowed
        {"source": "cust", "canonical": "customer_id", "cast": "integer"},
        {"source": "total_rev", "canonical": "gross_amount", "cast": "numeric"},
        {"source": "sale_date", "canonical": "order_date", "cast": "date"},
    ]
    result = _run(mapping_columns=bad_cols)
    assert result.ok is False
    codes = [e.code for e in result.errors]
    assert "TYPE_INCOMPATIBLE" in codes


def test_string_cast_always_coercible_to_string():
    # string → string is always valid; use empty profile_config to avoid key checks
    cols = [{"source": "x", "canonical": "order_date", "cast": "string"}]
    schema = {"required_fields": [], "types": {"order_date": "string"}}
    result = _run(mapping_columns=cols, canonical_schema=schema, profile_config={})
    assert result.ok is True  # string→string ok


def test_numeric_cast_to_string_is_coercible():
    # numeric can produce string
    assert _is_coercible("numeric", "string") is True


def test_boolean_to_integer_not_coercible():
    assert _is_coercible("boolean", "integer") is False


def test_timestamp_to_date_is_coercible():
    assert _is_coercible("timestamp", "date") is True


def test_unknown_cast_falls_back_to_string_allowed():
    # Unknown source cast → string allowed, anything else fails
    assert _is_coercible("unknown_type", "string") is True
    assert _is_coercible("unknown_type", "integer") is False


# ── Check 4: Null ratio threshold ─────────────────────────────


def test_null_ratio_below_threshold():
    preview = {"null_ratios": {"id": 0.05, "cust": 0.03}, "row_count_estimate": 1000}
    result = _run(source_preview=preview)
    assert result.ok is True
    assert not any(w.code == "HIGH_NULL_RATIO" for w in result.warnings)


def test_null_ratio_above_threshold_is_warning():
    preview = {"null_ratios": {"id": 0.50}, "row_count_estimate": 1000}
    result = _run(source_preview=preview)
    assert result.ok is True  # warnings don't fail validation
    assert any(w.code == "HIGH_NULL_RATIO" for w in result.warnings)


def test_null_ratio_uses_canonical_name_fallback():
    # If source name not in null_ratios, tries canonical name
    cols = [
        {"source": "src_order_id", "canonical": "order_id", "cast": "integer"},
        {"source": "cust", "canonical": "customer_id", "cast": "integer"},
        {"source": "total_rev", "canonical": "gross_amount", "cast": "numeric"},
        {"source": "sale_date", "canonical": "order_date", "cast": "date"},
    ]
    preview = {"null_ratios": {"order_id": 0.80}, "row_count_estimate": 500}
    result = _run(mapping_columns=cols, source_preview=preview)
    assert any(w.code == "HIGH_NULL_RATIO" for w in result.warnings)


def test_preview_none_skips_null_check():
    result = _run(source_preview=None)
    assert not any(w.code == "HIGH_NULL_RATIO" for w in result.warnings)


# ── Check 5: Row-count delta ──────────────────────────────────


def test_row_count_no_shrink():
    preview = {"null_ratios": {}, "row_count_estimate": 1000}
    prior = {"row_count_estimate": 900}
    result = _run(source_preview=preview, prior_release_snapshot=prior)
    assert not any(w.code == "ROW_COUNT_SHRINK" for w in result.warnings)


def test_row_count_shrink_over_20_pct():
    preview = {"null_ratios": {}, "row_count_estimate": 500}
    prior = {"row_count_estimate": 1000}  # 50% shrink
    result = _run(source_preview=preview, prior_release_snapshot=prior)
    assert any(w.code == "ROW_COUNT_SHRINK" for w in result.warnings)


def test_row_count_no_prior_skips_check():
    preview = {"null_ratios": {}, "row_count_estimate": 100}
    result = _run(source_preview=preview, prior_release_snapshot=None)
    assert not any(w.code == "ROW_COUNT_SHRINK" for w in result.warnings)


def test_row_count_prior_zero_skips_check():
    preview = {"null_ratios": {}, "row_count_estimate": 100}
    prior = {"row_count_estimate": 0}
    result = _run(source_preview=preview, prior_release_snapshot=prior)
    assert not any(w.code == "ROW_COUNT_SHRINK" for w in result.warnings)


# ── Check 6: Key fields mapped ────────────────────────────────


def test_declared_key_is_mapped():
    result = _run()
    assert not any(e.code == "KEY_NOT_MAPPED" for e in result.errors)


def test_declared_key_not_in_mapping():
    profile = {**PROFILE_CONFIG, "keys": ["product_id"]}  # product_id not in VALID_COLUMNS
    result = _run(profile_config=profile)
    assert result.ok is False
    assert any(e.code == "KEY_NOT_MAPPED" and e.field == "product_id" for e in result.errors)


def test_no_declared_keys_ok():
    profile = {**PROFILE_CONFIG, "keys": []}
    result = _run(profile_config=profile)
    assert not any(e.code == "KEY_NOT_MAPPED" for e in result.errors)


# ── Check 8: Tenant isolation ─────────────────────────────────


def test_no_tenant_id_embedding():
    result = _run()
    assert not any(w.code == "TENANT_ISOLATION_RISK" for w in result.warnings)


def test_embedded_tenant_id_warns():
    cols = VALID_COLUMNS + [{"source": "t_id", "canonical": "tenant_id", "cast": "integer"}]
    result = _run(mapping_columns=cols)
    assert any(w.code == "TENANT_ISOLATION_RISK" for w in result.warnings)


# ── Report shape ──────────────────────────────────────────────


def test_report_ok_when_no_errors():
    result = _run()
    assert result.ok is True
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_report_not_ok_when_errors():
    result = _run(mapping_columns=[])
    assert result.ok is False


def test_empty_canonical_schema_passes_trivially():
    result = validate_draft(
        mapping_columns=[],
        profile_config={},
        canonical_schema={},
        tenant_id=1,
    )
    assert result.ok is True  # no required fields → nothing to fail
