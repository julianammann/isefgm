import datetime as dt
from datetime import UTC, datetime

import pytest

from giftmanager.core.clock import local_today
from giftmanager.models import OccasionRule
from giftmanager.services.occasion import easter_sunday, rule_date
from tests.conftest import FixedClock


@pytest.mark.requirement("F-03")
@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (2024, "2024-03-31"),
        (2025, "2025-04-20"),
        (2026, "2026-04-05"),
        (2027, "2027-03-28"),
        (2038, "2038-04-25"),
        (2285, "2285-03-22"),
    ],
)
def test_easter_sunday(year: int, expected: str) -> None:
    assert easter_sunday(year) == dt.date.fromisoformat(expected)


@pytest.mark.requirement("F-03")
@pytest.mark.parametrize(
    ("rule", "today", "expected"),
    [
        (OccasionRule.BIRTHDAY, "2026-10-31", None),
        (OccasionRule.CHRISTMAS, "2026-10-31", "2026-12-24"),
        (OccasionRule.CHRISTMAS, "2026-12-24", "2026-12-24"),
        (OccasionRule.CHRISTMAS, "2026-12-25", "2027-12-24"),
        (OccasionRule.EASTER, "2026-04-05", "2026-04-05"),
        (OccasionRule.EASTER, "2026-04-06", "2027-03-28"),
        (OccasionRule.EASTER, "2026-01-01", "2026-04-05"),
    ],
)
def test_rule_date(rule: OccasionRule, today: str, expected: str | None) -> None:
    want = None if expected is None else dt.date.fromisoformat(expected)
    assert rule_date(rule, dt.date.fromisoformat(today)) == want


@pytest.mark.requirement("F-03")
def test_local_today_uses_the_app_time_zone() -> None:
    # 2026-12-23T23:30Z is 2026-12-24 00:30 in Europe/Berlin
    clock = FixedClock(datetime(2026, 12, 23, 23, 30, tzinfo=UTC))
    assert local_today(clock) == dt.date(2026, 12, 24)
