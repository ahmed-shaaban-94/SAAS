"""Tests for Egyptian holiday calendar."""

from datetime import date

from datapulse.anomalies.calendar import (
    is_eid,
    is_fixed_holiday,
    is_holiday_or_event,
    is_ramadan,
)


class TestFixedHolidays:
    def test_new_year(self):
        is_h, name = is_fixed_holiday(date(2026, 1, 1))
        assert is_h is True
        assert name == "New Year"

    def test_revolution_day(self):
        is_h, name = is_fixed_holiday(date(2026, 1, 25))
        assert is_h is True
        assert "Revolution" in name

    def test_sinai_liberation(self):
        is_h, name = is_fixed_holiday(date(2026, 4, 25))
        assert is_h is True

    def test_regular_day(self):
        is_h, name = is_fixed_holiday(date(2026, 3, 15))
        assert is_h is False
        assert name is None


class TestRamadan:
    def test_during_ramadan_2026(self):
        assert is_ramadan(date(2026, 3, 1)) is True

    def test_before_ramadan_2026(self):
        assert is_ramadan(date(2026, 2, 1)) is False

    def test_after_ramadan_2026(self):
        assert is_ramadan(date(2026, 4, 1)) is False

    def test_unknown_year(self):
        assert is_ramadan(date(2035, 3, 1)) is False


class TestEid:
    def test_eid_al_adha_2026(self):
        is_e, name = is_eid(date(2026, 5, 27))
        assert is_e is True
        assert name == "Eid al-Adha"

    def test_regular_day(self):
        is_e, name = is_eid(date(2026, 7, 15))
        assert is_e is False


class TestHolidayOrEvent:
    def test_new_year(self):
        is_event, reason = is_holiday_or_event(date(2026, 1, 1))
        assert is_event is True
        assert reason == "New Year"

    def test_ramadan(self):
        is_event, reason = is_holiday_or_event(date(2026, 3, 1))
        assert is_event is True
        assert reason == "Ramadan"

    def test_regular_day(self):
        is_event, reason = is_holiday_or_event(date(2026, 6, 15))
        assert is_event is False
        assert reason is None
