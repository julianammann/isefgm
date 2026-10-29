"""Seed synthetic test accounts with the test dataset for QZ-02 (Q-04: synthetic data only).

Usage: ``python -m giftmanager.seed``, locally via ``mise run seed``, on a server via
``docker compose exec api python -m giftmanager.seed``. Prompts once for the password of
all test accounts. Repeatable: existing test accounts are deleted with all their data and
created again, in one transaction. Faker is seeded, so every run produces the same data.
"""

import asyncio
import getpass
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.db import get_engine, get_sessionmaker
from giftmanager.models import (
    BIRTHDAY_TYPE_ID,
    CHRISTMAS_TYPE_ID,
    Gift,
    GiftCategory,
    Gifting,
    GiftingStatus,
    Occasion,
    Person,
    Recurrence,
    Task,
    TaskStatus,
    User,
)
from giftmanager.schemas.auth import RegisterIn
from giftmanager.services import auth as auth_service
from giftmanager.services import gift as gift_service
from giftmanager.services import gifting as gifting_service
from giftmanager.services import occasion as occasion_service
from giftmanager.services import person as person_service
from giftmanager.services import task as task_service

# example.org is reserved (RFC 2606), so no real mailbox can be hit.
ACCOUNTS = (("test1@example.org", "Testkonto 1"), ("test2@example.org", "Testkonto 2"))
PEOPLE = 100
OCCASIONS = 20
GIFTS = 1000
GIFTINGS = 1000
TASK_TITLES = ("Bestellen", "Abholen", "Einpacken", "Karte schreiben", "Größe klären")


async def _seed_account(
    session: AsyncSession, fake: Faker, *, email: str, display_name: str, password: str
) -> str:
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        await auth_service.delete_account(session, user)
    user = await auth_service.register(
        session, email=email, password=password, display_name=display_name
    )

    person_ids: list[uuid.UUID] = []
    for _ in range(PEOPLE):
        person = await person_service.create_person(
            session,
            user.id,
            name=fake.name(),
            birthday=fake.date_of_birth(minimum_age=1, maximum_age=90)
            if fake.boolean(80)
            else None,
            relationship=fake.random_element(
                ["Schwester", "Bruder", "Mutter", "Vater", "Freundin", "Freund", "Kollegin"]
            ),
            notes=fake.sentence() if fake.boolean(30) else None,
        )
        person_ids.append(person.id)

    occasion_ids: list[uuid.UUID] = []
    for i in range(OCCASIONS):
        christmas = i == 0
        occasion = await occasion_service.create_occasion(
            session,
            user.id,
            name="Weihnachten" if christmas else fake.catch_phrase()[:100],
            date=fake.date_this_decade(after_today=True),
            recurrence=Recurrence.YEARLY if christmas or fake.boolean() else Recurrence.NONE,
            occasion_type_id=CHRISTMAS_TYPE_ID if christmas else None,
            person_ids=list(fake.random_sample(person_ids, length=fake.random_int(1, 5))),
        )
        occasion_ids.append(occasion.id)

    gift_ids: list[uuid.UUID] = []
    for _ in range(GIFTS):
        priced = fake.boolean(70)
        price_from = Decimal(fake.random_int(5, 150)) if priced else None
        gift = await gift_service.create_gift(
            session,
            user.id,
            title=fake.catch_phrase()[:200],
            description=fake.paragraph() if fake.boolean(50) else None,
            price_from=price_from,
            price_to=price_from + fake.random_int(0, 50) if price_from is not None else None,
            currency="EUR" if priced else None,
            category=fake.random_element(list(GiftCategory)),
            person_ids=list(fake.random_sample(person_ids, length=fake.random_int(0, 3))),
            occasion_ids=list(fake.random_sample(occasion_ids, length=fake.random_int(0, 2))),
        )
        gift_ids.append(gift.id)

    # Every status in about equal parts. A given gifting needs recipients, an occasion and
    # its dates (F-06); open ones mostly have an upcoming occasion date.
    # shortcut: occasion_date ignores the occasion's own date, as the occasion dates above
    # are random too; align both if demos need it.
    for _ in range(GIFTINGS):
        status = fake.random_element(list(GiftingStatus))
        occasion_date: date | None = None
        if status is GiftingStatus.GIVEN:
            occasion_date = fake.date_between(start_date="-5y", end_date="today")
        elif fake.boolean(70):
            occasion_date = fake.date_between(start_date="today", end_date="+1y")
        gifting = await gifting_service.create_gifting(
            session,
            user.id,
            gift_id=fake.random_element(gift_ids),
            status=status,
            # Mostly one recipient; a joint gift has two.
            person_ids=list(fake.random_sample(person_ids, length=1 if fake.boolean(80) else 2)),
            occasion_id=fake.random_element(occasion_ids) if occasion_date else None,
            occasion_date=occasion_date,
            given_on=occasion_date if status is GiftingStatus.GIVEN else None,
        )
        for _ in range(fake.random_int(0, 3)):
            await task_service.create_task(
                session,
                user.id,
                gifting_id=gifting.id,
                title=fake.random_element(TASK_TITLES),
                status=fake.random_element(list(TaskStatus)),
                due_on=occasion_date - timedelta(days=fake.random_int(1, 14))
                if occasion_date
                else None,
            )

    # Counted, not the constants: create_person adds a birthday occasion per known birthday.
    is_birthday = Occasion.occasion_type_id == BIRTHDAY_TYPE_ID
    people, occasions, birthdays, gifts, giftings, tasks = (
        await session.execute(
            select(
                select(func.count()).where(Person.owner_id == user.id).scalar_subquery(),
                select(func.count()).where(Occasion.owner_id == user.id).scalar_subquery(),
                select(func.count())
                .where(Occasion.owner_id == user.id, is_birthday)
                .scalar_subquery(),
                select(func.count()).where(Gift.owner_id == user.id).scalar_subquery(),
                select(func.count())
                .select_from(Gifting)
                .join(Gift, Gift.id == Gifting.gift_id)
                .where(Gift.owner_id == user.id)
                .scalar_subquery(),
                select(func.count())
                .select_from(Task)
                .join(Gifting, Gifting.id == Task.gifting_id)
                .join(Gift, Gift.id == Gifting.gift_id)
                .where(Gift.owner_id == user.id)
                .scalar_subquery(),
            )
        )
    ).one()
    return (
        f"Seeded {email}: {people} people, {occasions} occasions "
        f"({birthdays} birthdays), {gifts} gift ideas, {giftings} giftings, {tasks} tasks."
    )


async def _seed(password: str) -> list[str]:
    Faker.seed(51)
    fake = Faker("de_DE")
    try:
        async with get_sessionmaker()() as session, session.begin():
            return [
                await _seed_account(
                    session, fake, email=email, display_name=display_name, password=password
                )
                for email, display_name in ACCOUNTS
            ]
    finally:
        await get_engine().dispose()


def main() -> int:
    """Prompt for the password, seed every test account and return the exit code."""
    password = getpass.getpass("Password for the test accounts: ")
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    try:
        RegisterIn(email=ACCOUNTS[0][0], password=password, display_name=ACCOUNTS[0][1])
    except ValidationError as exc:
        for error in exc.errors():
            print(f"{error['loc'][0]}: {error['msg']}", file=sys.stderr)
        return 1

    for summary in asyncio.run(_seed(password)):
        print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
