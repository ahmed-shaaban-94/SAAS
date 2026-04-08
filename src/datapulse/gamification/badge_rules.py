"""Badge evaluation rules — checks if staff members qualify for badges."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StaffMetrics:
    """Aggregated metrics for badge evaluation."""

    staff_key: int
    total_sales_count: int = 0
    monthly_txn_count: int = 0
    monthly_revenue: Decimal = Decimal("0")
    monthly_customers: int = 0
    monthly_returns: int = 0
    mom_growth_pct: Decimal = Decimal("0")
    current_streak_days: int = 0
    consecutive_100pct_months: int = 0
    rank_in_competition: int | None = None


# Each rule: (badge_key, check_function)
def _check_first_sale(m: StaffMetrics) -> bool:
    return m.total_sales_count >= 1


def _check_century_club(m: StaffMetrics) -> bool:
    return m.monthly_txn_count >= 100


def _check_quarter_million(m: StaffMetrics) -> bool:
    return m.monthly_revenue >= Decimal("250000")


def _check_million_maker(m: StaffMetrics) -> bool:
    return m.monthly_revenue >= Decimal("1000000")


def _check_streak_7(m: StaffMetrics) -> bool:
    return m.current_streak_days >= 7


def _check_streak_30(m: StaffMetrics) -> bool:
    return m.current_streak_days >= 30


def _check_streak_90(m: StaffMetrics) -> bool:
    return m.current_streak_days >= 90


def _check_customer_magnet(m: StaffMetrics) -> bool:
    return m.monthly_customers >= 50


def _check_comeback_king(m: StaffMetrics) -> bool:
    return m.mom_growth_pct >= Decimal("50")


def _check_perfect_quarter(m: StaffMetrics) -> bool:
    return m.consecutive_100pct_months >= 3


def _check_top_performer(m: StaffMetrics) -> bool:
    return m.rank_in_competition == 1


def _check_zero_returns(m: StaffMetrics) -> bool:
    return m.monthly_returns == 0 and m.monthly_txn_count > 0


BADGE_RULES: dict[str, callable] = {
    "first_sale": _check_first_sale,
    "century_club": _check_century_club,
    "quarter_million": _check_quarter_million,
    "million_maker": _check_million_maker,
    "streak_7": _check_streak_7,
    "streak_30": _check_streak_30,
    "streak_90": _check_streak_90,
    "customer_magnet": _check_customer_magnet,
    "comeback_king": _check_comeback_king,
    "perfect_quarter": _check_perfect_quarter,
    "top_performer": _check_top_performer,
    "zero_returns": _check_zero_returns,
}


def evaluate_badges(metrics: StaffMetrics, already_earned: set[str]) -> list[str]:
    """Return list of badge_keys the staff member newly qualifies for."""
    newly_earned = []
    for badge_key, check_fn in BADGE_RULES.items():
        if badge_key not in already_earned and check_fn(metrics):
            newly_earned.append(badge_key)
    return newly_earned
