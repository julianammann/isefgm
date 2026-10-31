import asyncio
import datetime as dt
import uuid
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from httpx import AsyncClient
from sqlalchemy import func, make_url, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from giftmanager.core.clock import local_today
from giftmanager.core.config import get_settings
from giftmanager.models import (
    BIRTHDAY_TYPE_ID,
    CHRISTMAS_TYPE_ID,
    EASTER_TYPE_ID,
    Occasion,
    OccasionRule,
    Recurrence,
    User,
)
from giftmanager.services import occasion as occasion_service
from giftmanager.services.occasion import easter_sunday, rule_date
from tests.accounts import log_in_new_user
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


# --- Rule occasions per account (F-03) ------------------------------------------

REGISTER = "/api/v1/auth/register"
ACCOUNT = "/api/v1/auth/account"
PEOPLE = "/api/v1/people"
ANNA = {"email": "anna@example.org", "password": "correct-horse-battery", "display_name": "Anna"}
RULE_ROWS = [
    ("Geburtstag", None, Recurrence.YEARLY, BIRTHDAY_TYPE_ID),
    ("Ostern", None, Recurrence.YEARLY, EASTER_TYPE_ID),
    ("Weihnachten", None, Recurrence.YEARLY, CHRISTMAS_TYPE_ID),
]


@pytest.fixture
def _registration_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "registration_enabled", True)


async def occasion_rows(session: AsyncSession, owner_id: uuid.UUID) -> list[tuple[Any, ...]]:
    rows = await session.execute(
        select(Occasion.name, Occasion.date, Occasion.recurrence, Occasion.occasion_type_id)
        .where(Occasion.owner_id == owner_id)
        .order_by(Occasion.name)
    )
    return [tuple(row) for row in rows]


@pytest.mark.requirement("F-03")
@pytest.mark.usefixtures("_registration_open")
async def test_registration_creates_the_rule_occasions(
    client: AsyncClient, session: AsyncSession
) -> None:
    r = await client.post(REGISTER, json=ANNA)
    assert r.status_code == 201

    assert await occasion_rows(session, uuid.UUID(r.json()["id"])) == RULE_ROWS


@pytest.mark.requirement("F-03", "F-04")
async def test_birthday_does_not_create_occasions(
    client: AsyncClient, session: AsyncSession
) -> None:
    anna = await log_in_new_user(client, session, "anna@example.org")

    r = await client.post(PEOPLE, json={"name": "Lena", "birthday": "1990-05-01"})
    assert r.status_code == 201

    assert await occasion_rows(session, anna.id) == []


@pytest.mark.requirement("F-01", "F-03")
@pytest.mark.usefixtures("_registration_open")
async def test_failed_registration_leaves_no_rule_occasions(
    client: AsyncClient, session: AsyncSession
) -> None:
    assert (await client.post(REGISTER, json=ANNA)).status_code == 201
    # Production rolls the failed request back; the savepoint does that here.
    async with session.begin_nested():
        assert (await client.post(REGISTER, json=ANNA)).status_code == 409

    count = (
        select(func.count())
        .select_from(Occasion)
        .join(User, User.id == Occasion.owner_id)
        .where(User.email == ANNA["email"], Occasion.date.is_(None))
    )
    assert await session.scalar(count) == 3


@pytest.mark.requirement("F-03", "F-17")
@pytest.mark.usefixtures("_registration_open")
async def test_deleting_the_account_deletes_its_rule_occasions(
    client: AsyncClient, session: AsyncSession
) -> None:
    owner_id = uuid.UUID((await client.post(REGISTER, json=ANNA)).json()["id"])
    count = select(func.count()).select_from(Occasion).where(Occasion.owner_id == owner_id)
    assert await session.scalar(count) == 3

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(count) == 0


@pytest.mark.requirement("F-03")
async def test_a_second_rule_occasion_of_a_type_is_rejected(session: AsyncSession) -> None:
    user = User(email="anna@example.org", password_hash="x", display_name="Anna")
    session.add(user)
    await session.flush()
    await occasion_service.create_rule_occasions(session, user.id)

    with pytest.raises(IntegrityError, match="uq_occasion_owner_rule_type"):
        async with session.begin_nested():
            await occasion_service.create_rule_occasions(session, user.id)


# --- Data migration for existing rows -------------------------------------------

BEFORE_RULES = "da408c6d1db0"


async def _run_sql(url: str, statements: list[str], params: dict[str, Any]) -> list[Any]:
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    results: list[Any] = []
    async with engine.connect() as conn:
        for statement in statements:
            result = await conn.execute(text(statement), params)
            results.append(result.all() if result.returns_rows else None)
    await engine.dispose()
    return results


@contextmanager
def _database_before_rules(
    database_url: str,
) -> Generator[tuple[str, Config, dict[str, uuid.UUID]]]:
    """A database of its own at BEFORE_RULES, with rows the migration has to fold."""
    name = f"migration_{uuid.uuid4().hex}"
    asyncio.run(_run_sql(database_url, [f"CREATE DATABASE {name}"], {}))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    keys = ["anna", "bob", "lena", "anton", "lena_bd", "anton_bd", "xmas", "easter", "idea"]
    ids = {key: uuid.uuid7() for key in [*keys, "at_birthday", "at_xmas"]}
    try:
        command.upgrade(cfg, BEFORE_RULES)
        asyncio.run(
            _run_sql(
                url,
                [
                    (
                        "INSERT INTO user_account (id, email, password_hash, display_name) VALUES "
                        "(:anna, 'anna@example.org', 'x', 'Anna'), "
                        "(:bob, 'bob@example.org', 'x', 'Bob')"
                    ),
                    (
                        "INSERT INTO person (id, owner_id, name, birthday) VALUES "
                        "(:lena, :anna, 'Lena', '1990-05-01'), "
                        "(:anton, :anna, 'Anton', '1985-12-24')"
                    ),
                    (
                        "INSERT INTO occasion "
                        "(id, owner_id, occasion_type_id, name, date, recurrence) VALUES "
                        "(:lena_bd, :anna, :birthday, 'Geburtstag Lena', '1990-05-01', 'yearly'), "
                        "(:anton_bd, :anna, :birthday, 'Geburtstag Anton', '1985-12-24', "
                        "'yearly'), "
                        "(:xmas, :anna, :christmas, 'Weihnachten', '2026-12-24', 'yearly'), "
                        "(:easter, :anna, NULL, 'Ostern', '2026-04-05', 'none')"
                    ),
                    (
                        "INSERT INTO person_occasion (person_id, occasion_id) VALUES "
                        "(:lena, :lena_bd), (:anton, :anton_bd), (:lena, :easter)"
                    ),
                    "INSERT INTO gift (id, owner_id, title) VALUES (:idea, :anna, 'Buch')",
                    (
                        "INSERT INTO gift_occasion (gift_id, occasion_id) VALUES "
                        "(:idea, :lena_bd), (:idea, :anton_bd)"
                    ),
                    (
                        "INSERT INTO gifting (id, gift_id, occasion_id) VALUES "
                        "(:at_birthday, :idea, :lena_bd), (:at_xmas, :idea, :xmas)"
                    ),
                    "INSERT INTO gifting_person (gifting_id, person_id) VALUES (:at_birthday, :lena)",
                ],
                {**ids, "birthday": BIRTHDAY_TYPE_ID, "christmas": CHRISTMAS_TYPE_ID},
            )
        )
        yield url, cfg, ids
    finally:
        asyncio.run(_run_sql(database_url, [f"DROP DATABASE {name} WITH (FORCE)"], {}))


@pytest.mark.requirement("F-03", "F-04")
def test_migration_folds_birthdays_and_christmas_into_rule_occasions(database_url: str) -> None:
    with _database_before_rules(database_url) as (url, cfg, ids):
        command.upgrade(cfg, "head")

        [occasions, ideas, giftings, links, easter_type] = asyncio.run(
            _run_sql(
                url,
                [
                    "SELECT id, owner_id, name, date, recurrence, occasion_type_id FROM occasion",
                    "SELECT gift_id, occasion_id FROM gift_occasion",
                    "SELECT id, occasion_id, occasion_date FROM gifting",
                    "SELECT person_id, occasion_id FROM person_occasion",
                    (
                        "SELECT id, owner_id, name, default_recurrence FROM occasion_type "
                        "WHERE name = 'Ostern'"
                    ),
                ],
                {},
            )
        )

    rules = [(name, None, "yearly", type_id) for name, _, _, type_id in RULE_ROWS]
    own_easter = ("Ostern", dt.date(2026, 4, 5), "none", None)

    def rows_of(owner: str) -> Counter[tuple[Any, ...]]:
        return Counter(tuple(row[2:]) for row in occasions if row[1] == ids[owner])

    assert rows_of("anna") == Counter([*rules, own_easter])
    assert rows_of("bob") == Counter(rules)
    assert (ids["easter"], ids["anna"], *own_easter) in occasions

    rule = {(row[1], row[5]): row[0] for row in occasions if row[3] is None}
    anna_birthday = rule[(ids["anna"], BIRTHDAY_TYPE_ID)]
    assert ideas == [(ids["idea"], anna_birthday)]
    assert {row[0]: row[1:] for row in giftings} == {
        ids["at_birthday"]: (anna_birthday, None),
        ids["at_xmas"]: (rule[(ids["anna"], CHRISTMAS_TYPE_ID)], None),
    }
    # The folded birthday occasions took their person links with them.
    assert links == [(ids["lena"], ids["easter"])]
    assert easter_type == [(EASTER_TYPE_ID, None, "Ostern", "yearly")]


@pytest.mark.requirement("F-03", "F-04")
def test_migration_downgrade_restores_birthdays_per_person(database_url: str) -> None:
    with _database_before_rules(database_url) as (url, cfg, ids):
        command.upgrade(cfg, "head")
        command.downgrade(cfg, BEFORE_RULES)

        [birthdays, giftings, easter_types] = asyncio.run(
            _run_sql(
                url,
                [
                    (
                        "SELECT o.id, o.name, o.date, po.person_id FROM occasion o "
                        "LEFT JOIN person_occasion po ON po.occasion_id = o.id "
                        "WHERE o.occasion_type_id = :birthday ORDER BY o.name"
                    ),
                    "SELECT id, occasion_id FROM gifting WHERE id = :at_birthday",
                    "SELECT id FROM occasion_type WHERE id = :easter_type",
                ],
                {
                    "birthday": BIRTHDAY_TYPE_ID,
                    "at_birthday": ids["at_birthday"],
                    "easter_type": EASTER_TYPE_ID,
                },
            )
        )

    [anton, lena] = birthdays
    assert lena[0] != ids["lena_bd"]  # created by the downgrade, not left over
    assert anton[1:] == ("Geburtstag Anton", dt.date(1985, 12, 24), ids["anton"])
    assert lena[1:] == ("Geburtstag Lena", dt.date(1990, 5, 1), ids["lena"])
    assert giftings == [(ids["at_birthday"], lena[0])]
    assert easter_types == []
