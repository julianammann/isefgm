"""A person's birthday occasion is derived from person.birthday (F-03, F-04)."""

import asyncio
import datetime as dt
import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from httpx import AsyncClient
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from giftmanager.models import BIRTHDAY_TYPE_ID, CHRISTMAS_TYPE_ID, User
from tests.accounts import log_in_new_user

PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_person(client: AsyncClient, body: dict[str, Any]) -> str:
    return (await client.post(PEOPLE, json=body)).json()["id"]


async def list_occasions(client: AsyncClient) -> list[dict[str, Any]]:
    return (await client.get(OCCASIONS)).json()["items"]


@pytest.mark.requirement("F-03", "F-04")
async def test_birthday_creates_the_birthday_occasion(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, {"name": "Lena", "birthday": "1990-05-01"})

    [birthday] = await list_occasions(client)
    assert birthday["name"] == "Geburtstag Lena"
    assert birthday["date"] == "1990-05-01"
    assert birthday["recurrence"] == "yearly"
    assert birthday["occasion_type_id"] == str(BIRTHDAY_TYPE_ID)
    assert birthday["people"] == [{"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-03", "F-04")
async def test_person_without_birthday_has_no_birthday_occasion(
    client: AsyncClient, anna: User
) -> None:
    await create_person(client, {"name": "Lena"})

    assert await list_occasions(client) == []


@pytest.mark.requirement("F-03", "F-04")
async def test_birthday_occasion_follows_the_person(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, {"name": "Lena", "birthday": "1990-05-01"})
    [before] = await list_occasions(client)

    r = await client.put(f"{PEOPLE}/{lena}", json={"name": "Lena M.", "birthday": "1991-06-02"})
    assert r.status_code == 200

    [after] = await list_occasions(client)
    assert after["id"] == before["id"]
    assert after["name"] == "Geburtstag Lena M."
    assert after["date"] == "1991-06-02"
    assert after["people"] == [{"id": lena, "name": "Lena M."}]


@pytest.mark.requirement("F-03", "F-04")
async def test_each_person_has_their_own_birthday_occasion(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, {"name": "Lena", "birthday": "1990-05-01"})
    anton = await create_person(client, {"name": "Anton", "birthday": "1985-12-24"})

    await client.put(f"{PEOPLE}/{lena}", json={"name": "Lena", "birthday": "1990-05-02"})

    by_name = {o["name"]: o for o in await list_occasions(client)}
    assert by_name.keys() == {"Geburtstag Lena", "Geburtstag Anton"}
    assert by_name["Geburtstag Lena"]["date"] == "1990-05-02"
    assert by_name["Geburtstag Anton"]["date"] == "1985-12-24"
    assert by_name["Geburtstag Anton"]["people"] == [{"id": anton, "name": "Anton"}]


@pytest.mark.requirement("F-03", "F-04")
async def test_adding_a_birthday_later_creates_the_occasion(
    client: AsyncClient, anna: User
) -> None:
    lena = await create_person(client, {"name": "Lena"})

    await client.put(f"{PEOPLE}/{lena}", json={"name": "Lena", "birthday": "1990-05-01"})

    [birthday] = await list_occasions(client)
    assert birthday["date"] == "1990-05-01"
    assert birthday["people"] == [{"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-03", "F-04")
async def test_removing_the_birthday_deletes_the_occasion(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, {"name": "Lena", "birthday": "1990-05-01"})
    other = (await client.post(OCCASIONS, json={"name": "Abifeier", "date": "2026-07-03"})).json()

    await client.put(f"{PEOPLE}/{lena}", json={"name": "Lena"})

    assert await list_occasions(client) == [other]


@pytest.mark.requirement("F-03", "F-04")
async def test_deleting_the_person_deletes_the_birthday_occasion(
    client: AsyncClient, anna: User
) -> None:
    lena = await create_person(client, {"name": "Lena", "birthday": "1990-05-01"})

    assert (await client.delete(f"{PEOPLE}/{lena}")).status_code == 204

    assert await list_occasions(client) == []


@pytest.mark.requirement("F-03", "F-04")
async def test_long_name_is_cut_to_fit_the_occasion_name(client: AsyncClient, anna: User) -> None:
    name = "L" * 100
    await create_person(client, {"name": name, "birthday": "1990-05-01"})

    [birthday] = await list_occasions(client)
    assert birthday["name"] == "Geburtstag " + "L" * 89


@pytest.mark.requirement("F-03", "F-04")
async def test_birthday_type_cannot_be_chosen_by_hand(client: AsyncClient, anna: User) -> None:
    birthday_type = {"occasion_type_id": str(BIRTHDAY_TYPE_ID)}
    party = {"name": "Party", "date": "2026-07-03"}

    r = await client.post(OCCASIONS, json={**party, **birthday_type})
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", "occasion_type_id"]

    created = (await client.post(OCCASIONS, json=party)).json()
    r = await client.put(f"{OCCASIONS}/{created['id']}", json={**party, **birthday_type})
    assert r.status_code == 422
    assert await list_occasions(client) == [created]


@pytest.mark.requirement("F-03", "F-04")
async def test_birthday_occasion_cannot_be_changed_or_deleted_by_hand(
    client: AsyncClient, anna: User
) -> None:
    await create_person(client, {"name": "Lena", "birthday": "1990-05-01"})
    [birthday] = await list_occasions(client)
    url = f"{OCCASIONS}/{birthday['id']}"

    r = await client.put(url, json={"name": "Umbenannt", "date": "2000-01-01"})
    assert r.status_code == 409
    assert (await client.delete(url)).status_code == 409

    assert await list_occasions(client) == [birthday]


# --- Data migration for existing rows -------------------------------------------

BEFORE_DERIVATION = "cbd3c5c4acbd"


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

        command.upgrade(cfg, "head")

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
