"""The old migration that derived one birthday occasion per person from person.birthday (F-03,
F-04). The rule occasions replaced that derivation (#132)."""

import asyncio
import datetime as dt
import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from giftmanager.models import BIRTHDAY_TYPE_ID, CHRISTMAS_TYPE_ID

# --- Data migration for existing rows -------------------------------------------

BEFORE_DERIVATION = "cbd3c5c4acbd"
DERIVATION = "13c2f34b196e"


async def _run_sql(url: str, statements: list[str], params: dict[str, Any]) -> list[Any]:
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    results: list[Any] = []
    async with engine.connect() as conn:
        for statement in statements:
            result = await conn.execute(text(statement), params)
            results.append(result.all() if result.returns_rows else None)
    await engine.dispose()
    return results


@pytest.mark.requirement("F-03", "F-04")
def test_migration_derives_birthday_occasions_of_existing_people(database_url: str) -> None:
    # A database of its own, so the migration runs on rows that exist before it.
    name = f"migration_{uuid.uuid4().hex}"
    asyncio.run(_run_sql(database_url, [f"CREATE DATABASE {name}"], {}))
    url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    ids = {key: uuid.uuid7() for key in ["user", "lena", "anton", "manual", "xmas"]}
    try:
        command.upgrade(cfg, BEFORE_DERIVATION)
        asyncio.run(
            _run_sql(
                url,
                [
                    (
                        "INSERT INTO user_account (id, email, password_hash, display_name) "
                        "VALUES (:user, 'anna@example.org', 'x', 'Anna')"
                    ),
                    (
                        "INSERT INTO person (id, owner_id, name, birthday) VALUES "
                        "(:lena, :user, 'Lena', '1990-05-01'), (:anton, :user, 'Anton', NULL)"
                    ),
                    # Created by hand before birthdays were derived, without a person.
                    (
                        "INSERT INTO occasion "
                        "(id, owner_id, occasion_type_id, name, date, recurrence) VALUES "
                        "(:manual, :user, :birthday_type, 'Geburtstag Oma', '1940-02-03', "
                        "'yearly'), "
                        "(:xmas, :user, :christmas_type, 'Weihnachten', '2026-12-24', 'yearly')"
                    ),
                ],
                {**ids, "birthday_type": BIRTHDAY_TYPE_ID, "christmas_type": CHRISTMAS_TYPE_ID},
            )
        )

        command.upgrade(cfg, DERIVATION)

        [occasions, links] = asyncio.run(
            _run_sql(
                url,
                [
                    (
                        "SELECT id, owner_id, occasion_type_id, name, date, recurrence "
                        "FROM occasion ORDER BY date"
                    ),
                    "SELECT person_id, occasion_id FROM person_occasion",
                ],
                {},
            )
        )
    finally:
        asyncio.run(_run_sql(database_url, [f"DROP DATABASE {name} WITH (FORCE)"], {}))

    [manual, derived, xmas] = occasions
    # The hand-made one keeps its data but loses the type, so it stays editable.
    assert manual == (
        ids["manual"],
        ids["user"],
        None,
        "Geburtstag Oma",
        dt.date(1940, 2, 3),
        "yearly",
    )
    assert derived[1:] == (
        ids["user"],
        BIRTHDAY_TYPE_ID,
        "Geburtstag Lena",
        dt.date(1990, 5, 1),
        "yearly",
    )
    assert xmas[0] == ids["xmas"]
    assert xmas[2] == CHRISTMAS_TYPE_ID
    assert links == [(ids["lena"], derived[0])]
