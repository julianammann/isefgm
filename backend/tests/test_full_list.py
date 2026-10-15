"""Complete list as HTML (F-15, QZ-03)."""

from decimal import Decimal
from html.parser import HTMLParser

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.api.v1.full_list import price
from giftmanager.models import Gift, User
from tests.accounts import log_in_new_user

FULL_LIST = "/api/v1/full-list"
PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
GIFTS = "/api/v1/gifts"
GIFTINGS = "/api/v1/giftings"
LINKS = "/api/v1/links"
NOTES = "/api/v1/notes"
THALIA = "https://www.thalia.de/shop/home/artikeldetails/A1234?ref=liste&x=1"

VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    }
)


class StructureCheck(HTMLParser):
    """Collect what a well-formed HTML5 document must have and every nesting error."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doctype = ""
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []

    def handle_decl(self, decl: str) -> None:
        self.doctype = decl

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.errors.append(f"self-closing <{tag}/>")
        self.tags.append((tag, dict(attrs)))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            self.errors.append(f"end tag for void element </{tag}>")
        elif not self.stack or self.stack[-1] != tag:
            self.errors.append(f"</{tag}> closes {self.stack[-1] if self.stack else 'nothing'}")
        else:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def check_structure(html: str) -> StructureCheck:
    """Parse the page and assert the rules the W3C validator checks first."""
    check = StructureCheck()
    check.feed(html)
    check.close()
    assert html.startswith("<!DOCTYPE html>")
    assert check.doctype == "DOCTYPE html"
    assert check.errors == []
    assert check.stack == []
    names = [tag for tag, _ in check.tags]
    assert names[:2] == ["html", "head"]
    assert check.tags[0][1] == {"lang": "de"}
    assert names.count("title") == 1
    assert ("meta", {"charset": "utf-8"}) in check.tags
    assert names.count("body") == 1
    ids = [attrs["id"] for _, attrs in check.tags if "id" in attrs]
    assert len(ids) == len(set(ids))
    return check


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def post(client: AsyncClient, url: str, body: dict[str, object]) -> str:
    r = await client.post(url, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.requirement("F-15", "QZ-03")
async def test_empty_list_is_valid_html(client: AsyncClient, anna: User) -> None:
    r = await client.get(FULL_LIST)
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/html; charset=utf-8"

    check = check_structure(r.text)
    text = " ".join(check.text)
    assert "Geschenkliste von anna@example.org" in text
    assert "Keine Personen." in text
    assert "Keine Geschenkideen." in text
    assert "Keine vergangenen Geschenke." in text


@pytest.mark.requirement("F-15", "QZ-03")
async def test_list_shows_people_ideas_and_past_gifts(client: AsyncClient, anna: User) -> None:
    lena = await post(
        client,
        PEOPLE,
        {"name": "Lena", "birthday": "1994-03-17", "relationship": "Schwester", "notes": "Größe M"},
    )
    max_ = await post(client, PEOPLE, {"name": "Max"})
    xmas = await post(
        client, OCCASIONS, {"name": "Weihnachten 2025", "date": "2025-12-24", "recurrence": "none"}
    )
    pi = await post(
        client,
        GIFTS,
        {
            "title": "Raspberry Pi",
            "description": "Technik",
            "price_from": "10",
            "price_to": "100",
            "category": "tech",
            "person_ids": [lena, max_],
            "occasion_ids": [xmas],
        },
    )
    book = await post(client, GIFTS, {"title": "Buch", "price_from": "15", "currency": "EUR"})
    await post(client, LINKS, {"gift_id": book, "label": "Thalia", "url": THALIA})
    await post(client, NOTES, {"gift_id": book, "label": "Größe", "text": "Taschenbuch"})
    await post(
        client,
        GIFTINGS,
        {
            "gift_id": pi,
            "status": "given",
            "person_ids": [lena],
            "occasion_id": xmas,
            "occasion_date": "2025-12-24",
            "given_on": "2025-12-24",
        },
    )
    await post(client, GIFTINGS, {"gift_id": book, "status": "planned", "person_ids": [max_]})

    r = await client.get(FULL_LIST)
    assert r.status_code == 200
    html = r.text
    check_structure(html)

    people = html[html.index('id="personen"') : html.index('id="geschenkideen"')]
    assert people.index("Lena") < people.index("Max")
    assert '<time datetime="1994-03-17">17.03.1994</time>' in people
    assert "Schwester" in people
    assert "Größe M" in people

    ideas = html[html.index('id="geschenkideen"') : html.index('id="vergangene-geschenke"')]
    assert ideas.index("Buch") < ideas.index("Raspberry Pi")
    assert "10,00 bis 100,00 EUR" in ideas
    assert "ab 15,00 EUR" in ideas
    assert "Technik" in ideas
    assert "Sonstiges" in ideas
    assert "Lena, Max" in ideas
    assert "Weihnachten 2025" in ideas
    assert f'<a href="{THALIA.replace("&", "&amp;")}" rel="noopener noreferrer">Thalia</a>' in ideas
    assert "Größe: Taschenbuch" in ideas

    past = html[html.index('id="vergangene-geschenke"') :]
    assert '<time datetime="2025-12-24">24.12.2025</time>' in past
    assert past.count("<tr>") == 2
    assert "Raspberry Pi" in past
    assert "Buch" not in past
    assert "Max" not in past
    assert "1 vergangene Geschenke" in html


@pytest.mark.requirement("F-15", "Q-03")
async def test_user_input_is_escaped(client: AsyncClient, anna: User) -> None:
    script = "<script>alert(1)</script>"
    lena = await post(client, PEOPLE, {"name": script, "notes": '"><img src=x onerror=alert(1)>'})
    gift = await post(client, GIFTS, {"title": "<b>fett</b>", "person_ids": [lena]})
    await post(client, LINKS, {"gift_id": gift, "label": "</a><script>x</script>", "url": THALIA})

    r = await client.get(FULL_LIST)
    check = check_structure(r.text)
    assert "<script>" not in r.text
    assert "<b>" not in r.text
    assert "<img" not in r.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in r.text
    assert script in "".join(check.text)
    assert [tag for tag, _ in check.tags].count("a") == 1


@pytest.mark.requirement("F-15", "Q-01")
async def test_list_shows_only_the_own_account(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena von Anna"})
    gift = await post(client, GIFTS, {"title": "Annas Idee", "person_ids": [lena]})
    await post(client, LINKS, {"gift_id": gift, "label": "Annas Link", "url": THALIA})
    await post(client, NOTES, {"gift_id": gift, "label": "Annas Notiz", "text": "geheim"})

    await log_in_new_user(client, session, "peter@example.com")
    r = await client.get(FULL_LIST)
    assert r.status_code == 200
    check_structure(r.text)
    for foreign in ("Lena von Anna", "Annas Idee", "Annas Link", "Annas Notiz", "anna@example.org"):
        assert foreign not in r.text
    assert "Geschenkliste von peter@example.com" in r.text


@pytest.mark.requirement("F-15", "Q-01")
async def test_list_requires_login(client: AsyncClient) -> None:
    r = await client.get(FULL_LIST)
    assert r.status_code == 401
    assert r.json()["title"] == "Not authenticated"


@pytest.mark.requirement("F-15")
@pytest.mark.parametrize(
    ("price_from", "price_to", "expected"),
    [
        ("10", "100", "10,00 bis 100,00 EUR"),
        ("25", "25", "25,00 EUR"),
        ("15", None, "ab 15,00 EUR"),
        (None, "1234.5", "bis 1234,50 EUR"),
        (None, None, ""),
    ],
)
def test_price_range_is_written_the_german_way(
    price_from: str | None, price_to: str | None, expected: str
) -> None:
    gift = Gift(
        title="Buch",
        price_from=None if price_from is None else Decimal(price_from),
        price_to=None if price_to is None else Decimal(price_to),
        currency=None if price_from is None and price_to is None else "EUR",
    )
    assert price(gift) == expected
