"""Christmas and Easter status overview: send days and open window (F-11)."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gifting import GiftingStatus
from giftmanager.models.notification import NotificationType
from giftmanager.models.occasion import Occasion, OccasionRule
from giftmanager.models.user import User
from giftmanager.services.notification import dedup_key
from giftmanager.services.season_overview import due, open_send, send_dates
from tests.notifications import (
    add_gift,
    add_gifting,
    add_person,
    add_rule_occasions,
    make_user,
    only,
)

pytestmark = pytest.mark.requirement("F-11", "QZ-09")
XMAS = date(2026, 12, 24)
EASTER = date(2027, 3, 28)
ORIGIN = get_settings().origin
START = datetime(2026, 11, 12, 7, 0, tzinfo=UTC)


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


async def setup_account(session: AsyncSession) -> tuple[User, Occasion]:
    user = await make_user(session, "konto@isefgm.localhost")
    rules = await add_rule_occasions(session, user)
    return user, rules[OccasionRule.CHRISTMAS]


async def test_lists_recipients_with_status_and_idea_people(session: AsyncSession) -> None:
    user, xmas = await setup_account(session)
    anna, bernd = (
        await add_person(session, user, "Anna", None),
        await add_person(session, user, "Bernd", None),
    )
    book = await add_gift(session, user, "Kochbuch")
    await add_gifting(session, book, [anna], GiftingStatus.ACQUIRED, xmas, XMAS)
    await add_gift(session, user, "Puzzle", people=[bernd], occasions=[xmas])
    [mail] = only(user, await due(session, START))
    assert mail.subject == "Weihnachten 2026: Stand der Geschenke"
    assert f"Anna\n- Kochbuch (Besorgt): {ORIGIN}/gifts/{book.id}" in mail.body
    assert "Bernd\n- noch keine Beschenkung, Ideen: Puzzle" in mail.body
    assert (mail.type, mail.reference_id, mail.event_date, mail.interval) == (
        NotificationType.CHRISTMAS,
        xmas.id,
        XMAS,
        "2026-11-12",
    )


async def test_idea_given_to_someone_else_still_adds_person(session: AsyncSession) -> None:
    user, xmas = await setup_account(session)
    anna, bernd = (
        await add_person(session, user, "Anna", None),
        await add_person(session, user, "Bernd", None),
    )
    voucher = await add_gift(session, user, "Kinogutschein", people=[anna, bernd], occasions=[xmas])
    await add_gifting(session, voucher, [bernd], GiftingStatus.GIVEN, xmas, date(2025, 12, 24))
    [mail] = only(user, await due(session, START))
    assert "Anna\n- noch keine Beschenkung, Ideen: Kinogutschein" in mail.body
    assert "Bernd" not in mail.body


async def test_given_idea_does_not_add_person(session: AsyncSession) -> None:
    user, xmas = await setup_account(session)
    clara = await add_person(session, user, "Clara", None)
    vase = await add_gift(session, user, "Vase", people=[clara], occasions=[xmas])
    await add_gifting(session, vase, [clara], GiftingStatus.GIVEN, xmas, date(2025, 12, 24))
    assert only(user, await due(session, START)) == []


async def test_last_years_gifting_does_not_count(session: AsyncSession) -> None:
    user, xmas = await setup_account(session)
    anna = await add_person(session, user, "Anna", None)
    await add_gifting(
        session,
        await add_gift(session, user, "Schal"),
        [anna],
        GiftingStatus.ACQUIRED,
        xmas,
        date(2025, 12, 24),
    )
    assert only(user, await due(session, START)) == []


async def test_gifting_without_date_counts_and_without_recipient_is_listed(
    session: AsyncSession,
) -> None:
    user, xmas = await setup_account(session)
    cookies = await add_gift(session, user, "Plätzchen")
    await add_gifting(session, cookies, [], GiftingStatus.IDEA, xmas, None)
    [mail] = only(user, await due(session, START))
    assert f"Ohne Empfänger\n- Plätzchen (Idee): {ORIGIN}/gifts/{cookies.id}" in mail.body


async def test_easter_overview(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    easter = (await add_rule_occasions(session, user))[OccasionRule.EASTER]
    anna = await add_person(session, user, "Anna", None)
    await add_gifting(
        session,
        await add_gift(session, user, "Schokohase"),
        [anna],
        GiftingStatus.PLANNED,
        easter,
        EASTER,
    )
    [mail] = only(user, await due(session, datetime(2027, 2, 14, 7, 0, tzinfo=UTC)))
    assert mail.subject == "Ostern 2027: Stand der Geschenke"
    assert "Stand für Ostern am 28.03.2027:" in mail.body
    assert mail.type is NotificationType.EASTER


async def test_weekly_mails_have_their_own_keys(session: AsyncSession) -> None:
    user, xmas = await setup_account(session)
    await add_gifting(
        session, await add_gift(session, user, "Kerze"), [], GiftingStatus.IDEA, xmas, XMAS
    )
    [first] = only(user, await due(session, START))
    [second] = only(user, await due(session, datetime(2026, 11, 16, 7, 0, tzinfo=UTC)))
    assert dedup_key(first) != dedup_key(second)
