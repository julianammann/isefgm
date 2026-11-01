"""Reminder two weeks before an own occasion (F-12)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.models.gifting import GiftingStatus
from giftmanager.models.occasion import Recurrence
from giftmanager.services.occasion_reminder import due
from tests.notifications import add_gift, add_gifting, add_occasion, add_person, make_user, only

pytestmark = pytest.mark.requirement("F-12", "QZ-09")
ORIGIN = get_settings().origin
EVENT = date(2026, 11, 20)
OPEN = datetime(2026, 11, 6, 7, 0, tzinfo=UTC)  # 08:00 Berlin, 14 days before


async def test_reminds_person_without_gifting(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    occasion = await add_occasion(session, user, "Hochzeitstag", EVENT, people=[anna])
    [mail] = only(user, await due(session, OPEN))
    assert mail.subject == "Erinnerung: Hochzeitstag am 20.11."
    assert "Noch ohne Beschenkung:\n- Anna" in mail.body
    assert (mail.reference_id, mail.event_date, mail.scheduled_for, mail.expires_at) == (
        occasion.id,
        EVENT,
        OPEN,
        datetime(2026, 11, 19, 23, 0, tzinfo=UTC),
    )


async def test_acquired_gift_does_not_suppress_the_rest(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    bernd = await add_person(session, user, "Bernd", None)
    occasion = await add_occasion(session, user, "Hochzeitstag", EVENT, people=[anna, bernd])
    vase = await add_gift(session, user, "Vase")
    await add_gifting(session, vase, [anna], GiftingStatus.ACQUIRED, occasion, EVENT)
    book = await add_gift(session, user, "Kochbuch")
    await add_gifting(session, book, [anna], GiftingStatus.PLANNED, occasion, None)
    [mail] = only(user, await due(session, OPEN))
    assert "Noch ohne Beschenkung:\n- Bernd" in mail.body
    assert f"- Kochbuch für Anna (Geplant): {ORIGIN}/gifts/{book.id}" in mail.body
    assert "Vase" not in mail.body


async def test_no_mail_when_everything_is_acquired_or_given(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    occasion = await add_occasion(session, user, "Hochzeitstag", EVENT, people=[anna])
    vase = await add_gift(session, user, "Vase")
    await add_gifting(session, vase, [anna], GiftingStatus.ACQUIRED, occasion, EVENT)
    assert only(user, await due(session, OPEN)) == []


async def test_gifting_for_another_year_does_not_count(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    occasion = await add_occasion(
        session, user, "Hochzeitstag", date(2020, 11, 20), Recurrence.YEARLY, people=[anna]
    )
    vase = await add_gift(session, user, "Vase")
    await add_gifting(session, vase, [anna], GiftingStatus.ACQUIRED, occasion, date(2025, 11, 20))
    [mail] = only(user, await due(session, OPEN))
    assert mail.event_date == EVENT
    assert "Noch ohne Beschenkung:\n- Anna" in mail.body


async def test_window_opens_at_eight_and_closes_at_midnight(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    await add_occasion(session, user, "Hochzeitstag", EVENT, people=[anna])
    assert only(user, await due(session, OPEN - timedelta(minutes=1))) == []
    assert len(only(user, await due(session, datetime(2026, 11, 19, 22, 59, tzinfo=UTC)))) == 1
    assert only(user, await due(session, datetime(2026, 11, 19, 23, 0, tzinfo=UTC))) == []


async def test_late_occasion_is_reminded_right_away(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    await add_occasion(session, user, "Feier", date(2026, 11, 16), people=[anna])
    [mail] = only(user, await due(session, OPEN))
    assert mail.scheduled_for == datetime(2026, 11, 2, 7, 0, tzinfo=UTC)


async def test_window_on_dst_change_day(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", None)
    await add_occasion(session, user, "Feier", date(2026, 11, 8), people=[anna])
    assert only(user, await due(session, datetime(2026, 10, 25, 6, 59, tzinfo=UTC))) == []
    assert len(only(user, await due(session, datetime(2026, 10, 25, 7, 0, tzinfo=UTC)))) == 1


async def test_occasion_without_people_needs_an_open_gifting(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    occasion = await add_occasion(session, user, "Feier", EVENT)
    assert only(user, await due(session, OPEN)) == []
    candle = await add_gift(session, user, "Kerze")
    await add_gifting(session, candle, [], GiftingStatus.IDEA, occasion, EVENT)
    [mail] = only(user, await due(session, OPEN))
    assert "- Kerze für ohne Empfänger (Idee)" in mail.body
