import asyncio
import getpass
from collections.abc import Iterator

import pytest
from sqlalchemy import func, select

from giftmanager import seed
from giftmanager.core.config import get_settings
from giftmanager.core.db import get_engine, get_sessionmaker
from giftmanager.models import Gift, Person, User


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
    _clear_caches()
    yield
    _clear_caches()


def _passwords(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    prompts = iter(answers)
    monkeypatch.setattr(getpass, "getpass", lambda _prompt="": next(prompts))


async def _counts() -> list[tuple[str, int, int]]:
    try:
        async with get_sessionmaker()() as session:
            rows = await session.execute(
                select(
                    User.email,
                    select(func.count()).where(Person.owner_id == User.id).scalar_subquery(),
                    select(func.count()).where(Gift.owner_id == User.id).scalar_subquery(),
                )
                .where(User.email.in_([email for email, _ in seed.ACCOUNTS]))
                .order_by(User.email)
            )
            return [(email, people, gifts) for email, people, gifts in rows]
    finally:
        await get_engine().dispose()


@pytest.mark.requirement("Q-04", "Q-05")
@pytest.mark.usefixtures("cli_database")
def test_seeds_every_account_and_can_run_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    expected = [(email, 5, 10) for email, _ in seed.ACCOUNTS]

    _passwords(monkeypatch, "correct-horse-battery", "correct-horse-battery")
    assert seed.main() == 0
    assert asyncio.run(_counts()) == expected
    # The summary counts the rows, birthday occasions included, not the configured numbers.
    out = capsys.readouterr().out
    for email, _ in seed.ACCOUNTS:
        assert f"Seeded {email}: 5 people, " in out
    assert "birthdays), 10 gift ideas." in out

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
