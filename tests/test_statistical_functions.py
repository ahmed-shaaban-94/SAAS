"""Tests for statistical functions in analytics.queries module."""

from decimal import Decimal

import pytest

from datapulse.analytics.queries import (
    coefficient_of_variation,
    compute_z_score,
    significance_level,
)


class TestComputeZScore:
    def test_returns_none_for_short_series(self):
        assert compute_z_score(Decimal("10"), [Decimal("5"), Decimal("15")]) is None

    def test_returns_none_for_zero_stdev(self):
        values = [Decimal("10")] * 5
        assert compute_z_score(Decimal("10"), values) is None

    def test_positive_z_score(self):
        values = [Decimal("10"), Decimal("12"), Decimal("11"), Decimal("13"), Decimal("10")]
        z = compute_z_score(Decimal("20"), values)
        assert z is not None
        assert z > Decimal("0")

    def test_negative_z_score(self):
        values = [Decimal("10"), Decimal("12"), Decimal("11"), Decimal("13"), Decimal("10")]
        z = compute_z_score(Decimal("1"), values)
        assert z is not None
        assert z < Decimal("0")

    def test_z_score_precision(self):
        values = [Decimal("100"), Decimal("110"), Decimal("105"), Decimal("108"), Decimal("103")]
        z = compute_z_score(Decimal("105"), values)
        assert z is not None
        # z-score should be close to 0 for a value near the mean
        assert abs(z) < Decimal("1")


class TestCoefficientOfVariation:
    def test_returns_none_for_short_series(self):
        assert coefficient_of_variation([Decimal("5"), Decimal("10")]) is None

    def test_returns_none_for_zero_mean(self):
        values = [Decimal("-5"), Decimal("5"), Decimal("0")]
        result = coefficient_of_variation(values)
        # Mean is 0, so CV is undefined
        assert result is None

    def test_positive_cv(self):
        values = [Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105")]
        cv = coefficient_of_variation(values)
        assert cv is not None
        assert cv > Decimal("0")

    def test_low_cv_for_stable_series(self):
        values = [Decimal("100"), Decimal("100.1"), Decimal("99.9"), Decimal("100.2")]
        cv = coefficient_of_variation(values)
        assert cv is not None
        assert cv < Decimal("1")  # Very low variability


class TestSignificanceLevel:
    def test_significant_positive(self):
        assert significance_level(Decimal("2.5")) == "significant"

    def test_significant_negative(self):
        assert significance_level(Decimal("-2.0")) == "significant"

    def test_inconclusive(self):
        assert significance_level(Decimal("1.5")) == "inconclusive"

    def test_noise_low_z(self):
        assert significance_level(Decimal("0.5")) == "noise"

    def test_noise_for_none(self):
        assert significance_level(None) == "noise"

    def test_boundary_significant(self):
        assert significance_level(Decimal("1.96")) == "significant"

    def test_boundary_inconclusive(self):
        assert significance_level(Decimal("1.28")) == "inconclusive"

    def test_just_below_inconclusive(self):
        assert significance_level(Decimal("1.27")) == "noise"
