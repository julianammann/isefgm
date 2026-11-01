"""Christmas and Easter status overview: send days and open window (F-11)."""

from datetime import UTC, date, datetime

import pytest

from giftmanager.services.season_overview import open_send, send_dates

pytestmark = pytest.mark.requirement("F-11", "QZ-09")
XMAS = date(2026, 12, 24)
EASTER = date(2027, 3, 28)


def test_send_dates_christmas_2026() -> None:
    assert send_dates(XMAS) == [
        date(2026, 11, 12),
        date(2026, 11, 16),
        date(2026, 11, 23),
        date(2026, 11, 30),
        date(2026, 12, 7),
        date(2026, 12, 14),
        date(2026, 12, 21),
    ]


def test_send_dates_easter_2027() -> None:
    assert send_dates(EASTER) == [
        date(2027, 2, 14),
        date(2027, 2, 15),
        date(2027, 2, 22),
        date(2027, 3, 1),
        date(2027, 3, 8),
        date(2027, 3, 15),
        date(2027, 3, 22),
    ]


def test_send_dates_start_on_a_monday_is_not_doubled() -> None:
    assert send_dates(date(2029, 12, 24)) == [
        date(2029, 11, 12),
        date(2029, 11, 19),
        date(2029, 11, 26),
        date(2029, 12, 3),
        date(2029, 12, 10),
        date(2029, 12, 17),
    ]


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 11, 12, 6, 59, tzinfo=UTC), None),
        (
            datetime(2026, 11, 12, 7, 0, tzinfo=UTC),
            (
                date(2026, 11, 12),
                datetime(2026, 11, 12, 7, 0, tzinfo=UTC),
                datetime(2026, 11, 16, 7, 0, tzinfo=UTC),
            ),
        ),
        (
            datetime(2026, 11, 17, 10, 0, tzinfo=UTC),
            (
                date(2026, 11, 16),
                datetime(2026, 11, 16, 7, 0, tzinfo=UTC),
                datetime(2026, 11, 23, 7, 0, tzinfo=UTC),
            ),
        ),
        (
            datetime(2026, 12, 23, 22, 59, tzinfo=UTC),
            (
                date(2026, 12, 21),
                datetime(2026, 12, 21, 7, 0, tzinfo=UTC),
                datetime(2026, 12, 23, 23, 0, tzinfo=UTC),
            ),
        ),
        (datetime(2026, 12, 23, 23, 0, tzinfo=UTC), None),
    ],
)
def test_open_send_christmas(
    now: datetime, expected: tuple[date, datetime, datetime] | None
) -> None:
    assert open_send(XMAS, now) == expected


def test_open_send_easter_starts_on_sunday() -> None:
    assert open_send(EASTER, datetime(2027, 2, 14, 7, 0, tzinfo=UTC)) == (
        date(2027, 2, 14),
        datetime(2027, 2, 14, 7, 0, tzinfo=UTC),
        datetime(2027, 2, 15, 7, 0, tzinfo=UTC),
    )
