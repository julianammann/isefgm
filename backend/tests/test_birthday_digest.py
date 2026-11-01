"""Monthly birthday digest (F-10)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.core.config import get_settings
from giftmanager.models.gifting import GiftingStatus
from giftmanager.scheduler import run_once
from giftmanager.services.birthday_digest import due
from tests.conftest import FixedClock
from tests.mail import RecordingMailer
from tests.notifications import (
    add_gift,
    add_gifting,
    add_given_gifting,
    add_person,
    make_committed_user,
    make_user,
    only,
)

pytestmark = pytest.mark.requirement("F-10", "QZ-01", "QZ-09")
NOV_1 = datetime(2026, 11, 1, 7, 0, tzinfo=UTC)  # 08:00 Berlin
ORIGIN = get_settings().origin


async def test_lists_exactly_next_month(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    for name, born in [
        ("Bernd", date(1985, 12, 31)),
        ("Anna", date(1990, 12, 3)),
        ("Clara", date(1990, 11, 30)),
        ("Dora", date(1990, 1, 1)),
        ("Emil", None),
    ]:
        await add_person(session, user, name, born)
    [mail] = only(user, await due(session, NOV_1))
    assert mail.subject == "Geburtstage im Dezember"
    assert "03.12. Anna" in mail.body and "31.12. Bernd" in mail.body
    assert mail.body.index("Anna") < mail.body.index("Bernd")
    assert not any(n in mail.body for n in ("Clara", "Dora", "Emil"))
    assert (mail.event_date, mail.scheduled_for, mail.expires_at) == (
        date(2026, 12, 1),
        NOV_1,
        datetime(2026, 12, 1, 7, 0, tzinfo=UTC),
    )


async def test_december_lists_january(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    await add_person(session, user, "Jan", date(2000, 1, 15))
    [mail] = only(user, await due(session, datetime(2026, 12, 1, 7, 0, tzinfo=UTC)))
    assert mail.subject == "Geburtstage im Januar"
    assert "15.01. Jan" in mail.body
    assert mail.event_date == date(2027, 1, 1)


async def test_lists_known_ideas_but_not_given_ones(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", date(1990, 12, 3))
    await add_person(session, user, "Bernd", date(1985, 12, 31))
    book = await add_gift(session, user, "Kochbuch", people=[anna])
    scarf = await add_gift(session, user, "Schal", people=[anna])
    await add_given_gifting(session, user, scarf, anna)
    [mail] = only(user, await due(session, NOV_1))
    assert f"- Kochbuch: {ORIGIN}/gifts/{book.id}" in mail.body
    assert "Schal" not in mail.body
    assert "31.12. Bernd\n- noch keine Ideen" in mail.body


async def test_before_eight_on_the_first_the_new_month_is_not_planned(
    session: AsyncSession,
) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    await add_person(session, user, "Anna", date(1990, 12, 3))
    await add_person(session, user, "Nina", date(1990, 11, 30))
    [mail] = only(user, await due(session, NOV_1 - timedelta(minutes=1)))
    assert "30.11. Nina" in mail.body and "Anna" not in mail.body
    assert (mail.event_date, mail.expires_at) == (date(2026, 11, 1), NOV_1)


async def test_caught_up_later_in_the_month(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    await add_person(session, user, "Anna", date(1990, 12, 3))
    [mail] = only(user, await due(session, datetime(2026, 11, 20, 10, 0, tzinfo=UTC)))
    assert (mail.event_date, mail.scheduled_for) == (date(2026, 12, 1), NOV_1)


async def test_no_mail_without_birthdays(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    await add_person(session, user, "Clara", date(1990, 11, 30))
    assert only(user, await due(session, NOV_1)) == []


async def test_feb_29_is_in_the_february_mail(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    await add_person(session, user, "Fritz", date(2000, 2, 29))
    [mail] = only(user, await due(session, datetime(2027, 1, 1, 7, 0, tzinfo=UTC)))
    assert "28.02. Fritz" in mail.body
    [leap] = only(user, await due(session, datetime(2028, 1, 1, 7, 0, tzinfo=UTC)))
    assert "29.02. Fritz" in leap.body


async def test_ideas_given_to_someone_else_stay_listed(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", date(1990, 12, 3))
    bernd = await add_person(session, user, "Bernd", date(1985, 12, 31))
    shared = await add_gift(session, user, "Tasse", people=[anna, bernd])
    await add_given_gifting(session, user, shared, bernd)
    [mail] = only(user, await due(session, NOV_1))
    anna_block = mail.body.split("31.12. Bernd")[0]
    assert f"- Tasse: {ORIGIN}/gifts/{shared.id}" in anna_block
    assert "Tasse" not in mail.body.split("31.12. Bernd")[1]


async def test_open_giftings_are_listed_once(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", date(1990, 12, 3))
    unlinked = await add_gift(session, user, "Buch")
    linked = await add_gift(session, user, "Tasse", people=[anna])
    await add_gifting(session, unlinked, [anna], GiftingStatus.PLANNED, None, None)
    await add_gifting(session, linked, [anna], GiftingStatus.PLANNED, None, None)
    [mail] = only(user, await due(session, NOV_1))
    assert mail.body.count(f"/gifts/{unlinked.id}") == 1
    assert mail.body.count(f"/gifts/{linked.id}") == 1


async def test_gift_only_given_to_the_person_is_not_listed(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    anna = await add_person(session, user, "Anna", date(1990, 12, 3))
    gift = await add_gift(session, user, "Buch")
    await add_given_gifting(session, user, gift, anna)
    [mail] = only(user, await due(session, NOV_1))
    assert "Buch" not in mail.body
    assert "03.12. Anna\n- noch keine Ideen" in mail.body


async def test_summer_time_send_hour(session: AsyncSession) -> None:
    user = await make_user(session, "konto@isefgm.localhost")
    await add_person(session, user, "Jul", date(1990, 7, 10))
    before = only(user, await due(session, datetime(2027, 6, 1, 5, 59, tzinfo=UTC)))
    assert all(m.event_date != date(2027, 7, 1) for m in before)
    [mail] = only(user, await due(session, datetime(2027, 6, 1, 6, 0, tzinfo=UTC)))
    assert mail.scheduled_for == datetime(2027, 6, 1, 6, 0, tzinfo=UTC)


@pytest.mark.requirement("F-10", "Q-01", "Q-04")
async def test_each_account_sees_only_its_own_people(session: AsyncSession) -> None:
    a = await make_user(session, "a@isefgm.localhost")
    b = await make_user(session, "b@isefgm.localhost")
    seed = await make_user(session, "test1@example.org")
    await add_person(session, a, "Anna", date(1990, 12, 3))
    await add_person(session, b, "Bernd", date(1990, 12, 4))
    await add_person(session, seed, "Sven", date(1990, 12, 5))
    mails = {m.recipient: m.body for m in await due(session, NOV_1)}
    assert {"a@isefgm.localhost", "b@isefgm.localhost"} <= set(mails)
    assert "test1@example.org" not in mails
    assert "Anna" in mails["a@isefgm.localhost"] and "Bernd" not in mails["a@isefgm.localhost"]


@pytest.mark.requirement("F-10", "QZ-05")
async def test_scheduler_sends_the_digest_once(
    committed_sessionmaker: async_sessionmaker[AsyncSession], clock: FixedClock
) -> None:
    user = await make_committed_user(committed_sessionmaker)
    async with committed_sessionmaker() as s, s.begin():
        await add_person(s, user, "Anna", date(1990, 12, 3))
    clock.current = NOV_1
    mailer = RecordingMailer()
    for _ in range(2):
        await run_once(clock=clock, sessionmaker=committed_sessionmaker, mailer=mailer)
    assert [m.subject for m in mailer.sent if m.to == user.email] == ["Geburtstage im Dezember"]
