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
from faker.providers import DynamicProvider
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
# de_DE has no product or catch-phrase data, so titles are curated per category and made
# unique with a Faker detail; the {{...}} placeholders are filled by Faker.parse. Each title
# carries its own descriptions, so a description always fits its title.
GIFT_IDEAS = {
    GiftCategory.BOOKS: {
        "Krimi von {{last_name}}": (
            "Den neuen Band gibt es erst seit Kurzem.",
            "Die Vorgänger sind alle schon gelesen.",
        ),
        "Roman von {{last_name}}": (
            "Als Taschenbuch reicht.",
            "Stand lange auf der Bestsellerliste.",
        ),
        "Biografie von {{last_name}}": (
            "Gebunden, mit Fotos.",
            "Großes Interesse an Zeitgeschichte.",
        ),
        "Gedichtband von {{last_name}}": ("Schöne Ausgabe mit Lesebändchen.", "Gern mit Widmung."),
        "Kochbuch von {{last_name}}": (
            "Am liebsten vegetarisch.",
            "Mit einfachen Rezepten für den Alltag.",
        ),
        "Sachbuch von {{last_name}}": (
            "Gibt es oft gebraucht im Antiquariat.",
            "Wurde im Podcast empfohlen.",
        ),
        "Hörbuch von {{last_name}}": (
            "Für lange Autofahrten.",
            "Als Download, einen CD-Spieler gibt es nicht mehr.",
        ),
        "Comic von {{last_name}}": ("Der erste Band einer Reihe.", "Gern die Sammelausgabe."),
    },
    GiftCategory.GAMES: {
        "Puzzle {{city}}, 1000 Teile": (
            "Puzzelt gern an Regentagen.",
            "Erinnert an den letzten Urlaub.",
        ),
        "Brettspiel „{{city}}“": ("Für Spieleabende zu viert.", "Spieldauer etwa eine Stunde."),
        "Kartenspiel „{{city}}“": ("Passt in jede Jackentasche.", "Geht auch zu zweit."),
        "Würfelspiel „{{city}}“": ("Schnell erklärt, auch für Kinder.", "Gut für zwischendurch."),
        "Kooperatives Spiel „{{city}}“": (
            "Alle gewinnen oder verlieren zusammen.",
            "Die Erweiterung kann später folgen.",
        ),
    },
    GiftCategory.EXPERIENCE: {
        "Kochkurs in {{city}}": (
            "Für zwei Personen, Termin frei wählbar.",
            "Am liebsten italienische Küche.",
        ),
        "Konzertkarten in {{city}}": (
            "Stehplätze reichen.",
            "Vorher nach freien Wochenenden fragen.",
        ),
        "Escape Room in {{city}}": (
            "Für eine Gruppe von vier Leuten.",
            "Lieber mittlere Schwierigkeit.",
        ),
        "Wellnesstag in {{city}}": ("Mit Massage.", "Gutschein ist drei Jahre gültig."),
        "Kletterkurs in {{city}}": (
            "Für Anfänger, Ausrüstung wird gestellt.",
            "Steht schon lange auf der Liste.",
        ),
        "Stadtführung in {{city}}": ("Gern die Abendführung.", "Anfahrt mit der Bahn einplanen."),
        "Theaterkarten in {{city}}": ("Lieber Komödie als Drama.", "Plätze im Parkett."),
        "Weinprobe in {{city}}": ("Mit kleinem Imbiss.", "Rückfahrt vorher klären."),
    },
    GiftCategory.CLOTHING: {
        "Strickpullover, Farbe {{color_name}}, Größe {{clothing_size}}": (
            "Bitte aus Baumwolle, Wolle kratzt.",
            "Weite Schnitte kommen gut an.",
        ),
        "Regenjacke, Farbe {{color_name}}, Größe {{clothing_size}}": (
            "Mit Kapuze.",
            "Leicht genug zum Wandern.",
        ),
        "Hoodie, Farbe {{color_name}}, Größe {{clothing_size}}": (
            "Gern nachhaltig produziert.",
            "Mit Reißverschluss.",
        ),
        "Schal, Farbe {{color_name}}": ("Lang genug zum zweimal Wickeln.", "Weich, nicht kratzig."),
        "Mütze, Farbe {{color_name}}": ("Ohne Bommel.", "Passend zum Schal vom letzten Jahr."),
        "Hausschuhe, Farbe {{color_name}}": ("Mit fester Sohle.", "Schuhgröße vorher nachfragen."),
        "Handschuhe, Farbe {{color_name}}": (
            "Mit Touchscreen-Fingerspitzen.",
            "Gefüttert für den Winter.",
        ),
    },
    GiftCategory.TECH: {
        "Kopfhörer, Farbe {{color_name}}": (
            "Mit Geräuschunterdrückung.",
            "Zum Joggen, also kabellos.",
        ),
        "Powerbank, Farbe {{color_name}}": (
            "Mit USB-C, das alte Kabel passt nicht mehr.",
            "Klein genug für die Hosentasche.",
        ),
        "Bluetooth-Lautsprecher, Farbe {{color_name}}": (
            "Wasserdicht, für den Garten.",
            "Der Akku sollte einen Tag halten.",
        ),
        "Handyhülle, Farbe {{color_name}}": (
            "Vorher das Handymodell nachsehen.",
            "Mit Fach für Karten.",
        ),
        "E-Reader-Hülle, Farbe {{color_name}}": (
            "Mit Standfunktion.",
            "Vorher das Modell nachsehen.",
        ),
        "Smartwatch-Armband, Farbe {{color_name}}": ("Aus Stoff, nicht Silikon.", "Für den Sport."),
    },
    GiftCategory.FOOD: {
        "Honig aus {{city}}": ("Gern regional.", "Lieber cremig als flüssig."),
        "Kaffee aus einer Rösterei in {{city}}": (
            "Ganze Bohnen, gemahlen wird selbst.",
            "Lieber mild als kräftig.",
        ),
        "Pralinen aus {{city}}": ("Keine Nüsse, Allergie.", "Gern mit Zartbitterschokolade."),
        "Gin aus {{city}}": ("Mit passendem Tonic.", "Lieber herb als süß."),
        "Weinpaket vom Weingut {{last_name}}": (
            "Rotwein, eher trocken.",
            "Hält sich ein paar Jahre.",
        ),
        "Feinkostkorb vom Hofladen {{last_name}}": (
            "Keine Nüsse, Allergie.",
            "Gern mit Käse und Chutney.",
        ),
    },
    GiftCategory.HOME: {
        "Kerzenhalter, Farbe {{color_name}}": ("Passt zur neuen Wohnung.", "Für Stabkerzen."),
        "Kuscheldecke, Farbe {{color_name}}": ("Groß genug fürs Sofa.", "Waschbar bei 40 Grad."),
        "Blumenvase, Farbe {{color_name}}": ("Zerbrechlich, gut einpacken.", "Für große Sträuße."),
        "Kissenbezug, Farbe {{color_name}}": ("Format 50 x 50.", "Lieber schlicht als verspielt."),
        "Teekanne, Farbe {{color_name}}": (
            "Mit Sieb für losen Tee.",
            "Für mindestens vier Tassen.",
        ),
        "Bilderrahmen, Farbe {{color_name}}": (
            "Für ein Foto im Format 13 x 18.",
            "Nach dem Umzug fehlt noch Deko.",
        ),
        "Keramiktasse, Farbe {{color_name}}": ("Spülmaschinenfest.", "Gern handgemacht."),
    },
    GiftCategory.VOUCHER: {
        "Gutschein Buchhandlung {{last_name}}": ("Betrag frei wählbar.", "Auch online einlösbar."),
        "Gutschein Café {{last_name}}": ("Für Frühstück zu zweit.", "Liegt direkt um die Ecke."),
        "Gutschein Restaurant {{last_name}}": (
            "Für ein Abendessen zu zweit.",
            "Gültig bis Ende nächsten Jahres.",
        ),
        "Gutschein Friseursalon {{last_name}}": (
            "Lieber ausgedruckt als per E-Mail.",
            "Termin wird selbst gebucht.",
        ),
        "Gutschein Gärtnerei {{last_name}}": (
            "Für den Balkon im Frühjahr.",
            "Betrag frei wählbar.",
        ),
        "Gutschein Kino in {{city}}": ("Für zwei Personen.", "Auch für 3D-Filme."),
        "Gutschein Therme {{city}}": ("Tageskarte mit Sauna.", "Gültig bis Ende nächsten Jahres."),
    },
    GiftCategory.OTHER: {
        "Fotobuch vom Urlaub in {{city}}": (
            "Selbst gestaltet, rechtzeitig anfangen.",
            "Braucht ein paar Wochen Vorlauf.",
        ),
        "Kalender mit Fotos aus {{city}}": ("Bis Ende November bestellen.", "Ein Foto pro Monat."),
        "Postkartenset aus {{city}}": ("Für Grüße aus dem Urlaub.", "Mit Briefmarken."),
        "Zimmerpflanze von der Gärtnerei {{last_name}}": (
            "Pflegeleicht, verträgt wenig Licht.",
            "Mit Übertopf.",
        ),
        "Spende an den Tierschutzverein {{city}}": (
            "Mit Urkunde zum Überreichen.",
            "Statt eines weiteren Gegenstands.",
        ),
    },
}
# Christmas is added on its own; the rest are drawn without repetition.
OCCASION_NAMES = (
    "Hochzeit",
    "Verlobung",
    "Polterabend",
    "Silberhochzeit",
    "Goldene Hochzeit",
    "Jahrestag",
    "Einweihung",
    "Umzug",
    "Taufe",
    "Geburt",
    "Einschulung",
    "Konfirmation",
    "Kommunion",
    "Abschlussfeier",
    "Führerschein bestanden",
    "Firmenjubiläum",
    "Ruhestand",
    "Abschied",
    "Sommerfest",
    "Jubiläum",
)
PERSON_NOTES = (
    "Trinkt keinen Kaffee, lieber Tee.",
    "Allergisch gegen Nüsse.",
    "Sammelt Schallplatten.",
    "Wandert gern.",
    "Spielt Gitarre.",
    "Kocht gern asiatisch.",
    "Liest viel, am liebsten Krimis.",
    "Fährt jeden Tag Rad.",
    "Mag keine Deko-Artikel.",
    "Hat gerade einen Garten.",
    "Reist gern in den Norden.",
    "Backt jedes Wochenende.",
)


async def _seed_account(
    session: AsyncSession, fake: Faker, *, email: str, display_name: str, password: str
) -> str:
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        await auth_service.delete_account(session, user)
    user = await auth_service.register(
        session, email=email, password=password, display_name=display_name
    )
    # Unique titles and occasion names per account, not across both.
    fake.unique.clear()

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
            notes=fake.random_element(PERSON_NOTES) if fake.boolean(30) else None,
        )
        person_ids.append(person.id)

    occasion_ids: list[uuid.UUID] = []
    for i in range(OCCASIONS):
        christmas = i == 0
        occasion = await occasion_service.create_occasion(
            session,
            user.id,
            name="Weihnachten" if christmas else fake.unique.random_element(OCCASION_NAMES),
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
        category = fake.random_element(list(GiftCategory))
        ideas = GIFT_IDEAS[category]
        template = fake.random_element(list(ideas))
        gift = await gift_service.create_gift(
            session,
            user.id,
            title=fake.unique.parse(template),
            description=fake.random_element(ideas[template]) if fake.boolean(50) else None,
            price_from=price_from,
            price_to=price_from + fake.random_int(0, 50) if price_from is not None else None,
            currency="EUR" if priced else None,
            category=category,
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
    fake.add_provider(DynamicProvider("clothing_size", ["S", "M", "L", "XL"]))
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
