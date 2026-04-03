"""Egyptian holiday calendar for anomaly suppression.

Anomalies detected on holidays or during Ramadan are suppressed (flagged
but not alerted) because sales patterns naturally deviate during these periods.
"""

from __future__ import annotations

from datetime import date

# Fixed Egyptian public holidays (month, day)
EGYPTIAN_HOLIDAYS: dict[str, list[tuple[int, int]]] = {
    "New Year": [(1, 1)],
    "January 25 Revolution": [(1, 25)],
    "Sinai Liberation Day": [(4, 25)],
    "Labour Day": [(5, 1)],
    "June 30 Revolution": [(6, 30)],
    "July 23 Revolution": [(7, 23)],
    "Armed Forces Day": [(10, 6)],
}

# Approximate Ramadan start/end dates by Gregorian year
# (Islamic calendar shifts ~11 days/year)
RAMADAN_DATES: dict[int, tuple[date, date]] = {
    2023: (date(2023, 3, 22), date(2023, 4, 21)),
    2024: (date(2024, 3, 11), date(2024, 4, 9)),
    2025: (date(2025, 2, 28), date(2025, 3, 30)),
    2026: (date(2026, 2, 17), date(2026, 3, 19)),
    2027: (date(2027, 2, 7), date(2027, 3, 8)),
    2028: (date(2028, 1, 27), date(2028, 2, 25)),
}

# Eid al-Fitr (3 days after Ramadan) and Eid al-Adha approximate dates
EID_ADHA_DATES: dict[int, tuple[date, date]] = {
    2023: (date(2023, 6, 28), date(2023, 6, 30)),
    2024: (date(2024, 6, 16), date(2024, 6, 18)),
    2025: (date(2025, 6, 6), date(2025, 6, 8)),
    2026: (date(2026, 5, 26), date(2026, 5, 28)),
    2027: (date(2027, 5, 16), date(2027, 5, 18)),
    2028: (date(2028, 5, 4), date(2028, 5, 6)),
}


def is_fixed_holiday(d: date) -> tuple[bool, str | None]:
    """Check if a date falls on a fixed Egyptian public holiday."""
    for name, dates in EGYPTIAN_HOLIDAYS.items():
        for month, day in dates:
            if d.month == month and d.day == day:
                return True, name
    return False, None


def is_ramadan(d: date) -> bool:
    """Check if a date falls within Ramadan."""
    ram = RAMADAN_DATES.get(d.year)
    if ram is None:
        return False
    return ram[0] <= d <= ram[1]


def is_eid(d: date) -> tuple[bool, str | None]:
    """Check if a date falls during Eid al-Fitr or Eid al-Adha."""
    # Eid al-Fitr: 3 days after Ramadan
    ram = RAMADAN_DATES.get(d.year)
    if ram is not None:
        from datetime import timedelta

        fitr_start = ram[1] + timedelta(days=1)
        fitr_end = ram[1] + timedelta(days=3)
        if fitr_start <= d <= fitr_end:
            return True, "Eid al-Fitr"

    # Eid al-Adha
    adha = EID_ADHA_DATES.get(d.year)
    if adha is not None and adha[0] <= d <= adha[1]:
        return True, "Eid al-Adha"

    return False, None


def is_holiday_or_event(d: date) -> tuple[bool, str | None]:
    """Check if date is a holiday, Ramadan, or Eid.

    Returns (is_event, reason_string).
    """
    is_h, name = is_fixed_holiday(d)
    if is_h:
        return True, name

    if is_ramadan(d):
        return True, "Ramadan"

    is_e, eid_name = is_eid(d)
    if is_e:
        return True, eid_name

    return False, None
