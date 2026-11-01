import asyncio
import datetime as dt
import getpass
from collections.abc import Iterator

import pytest
from sqlalchemy import func, select

from giftmanager import seed
from giftmanager.core.config import get_settings
from giftmanager.core.db import get_engine, get_sessionmaker
from giftmanager.models import (
    Gift,
    GiftCategory,
    Gifting,
    GiftingStatus,
    Person,
    Task,
    User,
    gifting_person,
)
from giftmanager.services import auth as auth_service


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
def cli_database(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the command's own engine at the test database; what it writes is committed."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    # Small counts keep the test fast; the loops are the same.
    monkeypatch.setattr(seed, "PEOPLE", 5)
    monkeypatch.setattr(seed, "OCCASIONS", 3)
    monkeypatch.setattr(seed, "GIFTS", 10)
    monkeypatch.setattr(seed, "GIFTINGS", 12)
    _clear_caches()
    yield
    # Committed rows outlive the test; later tests count tasks across the whole database.
    asyncio.run(_delete_accounts())
    _clear_caches()


async def _delete_accounts() -> None:
    try:
        async with get_sessionmaker()() as session, session.begin():
            emails = [email for email, _ in seed.ACCOUNTS]
            for user in await session.scalars(select(User).where(User.email.in_(emails))):
                await auth_service.delete_account(session, user)
    finally:
        await get_engine().dispose()


def _passwords(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    prompts = iter(answers)
    monkeypatch.setattr(getpass, "getpass", lambda _prompt="": next(prompts))


async def _counts() -> list[tuple[str, int, int, int]]:
    try:
        async with get_sessionmaker()() as session:
            rows = await session.execute(
                select(
                    User.email,
                    select(func.count()).where(Person.owner_id == User.id).scalar_subquery(),
                    select(func.count()).where(Gift.owner_id == User.id).scalar_subquery(),
                    select(func.count())
                    .select_from(Gifting)
                    .join(Gift, Gift.id == Gifting.gift_id)
                    .where(Gift.owner_id == User.id)
                    .scalar_subquery(),
                )
                .where(User.email.in_([email for email, _ in seed.ACCOUNTS]))
                .order_by(User.email)
            )
            return [tuple(row) for row in rows]
    finally:
        await get_engine().dispose()


async def _given() -> tuple[int, int]:
    """Given giftings of the test accounts, and those without a recipient (F-06: none)."""
    has_recipient = select(gifting_person).where(gifting_person.c.gifting_id == Gifting.id).exists()
    try:
        async with get_sessionmaker()() as session:
            given, without_recipient = (
                await session.execute(
                    select(func.count(), func.count().filter(~has_recipient))
                    .select_from(Gifting)
                    .join(Gift, Gift.id == Gifting.gift_id)
                    .join(User, User.id == Gift.owner_id)
                    .where(
                        Gifting.status == GiftingStatus.GIVEN,
                        User.email.in_([email for email, _ in seed.ACCOUNTS]),
                    )
                )
            ).one()
            return given, without_recipient
    finally:
        await get_engine().dispose()


async def _gifts() -> list[tuple[str, GiftCategory, str, str | None]]:
    """Owner email, category, title and description of every gift of the test accounts."""
    try:
        async with get_sessionmaker()() as session:
            rows = await session.execute(
                select(User.email, Gift.category, Gift.title, Gift.description)
                .join(User, User.id == Gift.owner_id)
                .where(User.email.in_([email for email, _ in seed.ACCOUNTS]))
            )
            return [tuple(row) for row in rows]
    finally:
        await get_engine().dispose()


async def _tasks() -> list[tuple[str, dt.date | None, dt.date | None]]:
    """Title, due date and the gifting's occasion date of every task of the test accounts."""
    try:
        async with get_sessionmaker()() as session:
            rows = await session.execute(
                select(Task.title, Task.due_on, Gifting.occasion_date)
                .join(Gifting, Gifting.id == Task.gifting_id)
                .join(Gift, Gift.id == Gifting.gift_id)
                .join(User, User.id == Gift.owner_id)
                .where(User.email.in_([email for email, _ in seed.ACCOUNTS]))
            )
            return [tuple(row) for row in rows]
    finally:
        await get_engine().dispose()


@pytest.mark.requirement("Q-04", "Q-05")
@pytest.mark.usefixtures("cli_database")
def test_seeds_every_account_and_can_run_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    expected = [(email, 5, 10, 12) for email, _ in seed.ACCOUNTS]

    _passwords(monkeypatch, "correct-horse-battery", "correct-horse-battery")
    assert seed.main() == 0
    assert asyncio.run(_counts()) == expected
    given, without_recipient = asyncio.run(_given())
    assert given > 0
    assert without_recipient == 0
    gifts = asyncio.run(_gifts())
    # Unique per account, each title from its category, each description from its title.
    assert len({(email, title) for email, _, title, _ in gifts}) == len(gifts)
    for _, category, title, description in gifts:
        ideas = seed.GIFT_IDEAS[category]
        (template,) = [t for t in ideas if title.startswith(t.split("{{")[0])]
        assert description is None or description in ideas[template]
    tasks = asyncio.run(_tasks())
    assert tasks
    for title, due_on, occasion_date in tasks:
        assert title in seed.TASK_TITLES
        # 1 to 14 days before the gifting's date; no date, no due date.
        if occasion_date is None:
            assert due_on is None
        else:
            assert due_on is not None and 1 <= (occasion_date - due_on).days <= 14
    # The summary counts the rows, the three rule occasions included, not the configured
    # numbers.
    out = capsys.readouterr().out
    for email, _ in seed.ACCOUNTS:
        assert f"Seeded {email}: 5 people, 6 occasions, 10 gift ideas, 12 giftings, " in out
    assert "birthdays" not in out

    # The second run replaces the accounts instead of failing or doubling the data.
    _passwords(monkeypatch, "correct-horse-battery", "correct-horse-battery")
    assert seed.main() == 0
    assert asyncio.run(_counts()) == expected


@pytest.mark.requirement("Q-03")
@pytest.mark.usefixtures("cli_database")
def test_rejects_a_weak_password(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _passwords(monkeypatch, "short", "short")
    assert seed.main() == 1
    assert "password" in capsys.readouterr().err
