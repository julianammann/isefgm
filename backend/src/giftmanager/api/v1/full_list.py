"""Complete list endpoint (F-15): the account's people, gift ideas and past gifts as HTML."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.models import Gift, GiftCategory
from giftmanager.schemas.common import problem_responses
from giftmanager.services import full_list as full_list_service

router = APIRouter(prefix="/full-list", tags=["full-list"])

CATEGORY_LABELS = {
    GiftCategory.BOOKS: "Bücher",
    GiftCategory.GAMES: "Spiele",
    GiftCategory.EXPERIENCE: "Erlebnis",
    GiftCategory.CLOTHING: "Kleidung",
    GiftCategory.TECH: "Technik",
    GiftCategory.FOOD: "Essen und Trinken",
    GiftCategory.HOME: "Wohnen",
    GiftCategory.VOUCHER: "Gutschein",
    GiftCategory.OTHER: "Sonstiges",
}


def german_date(value: date) -> str:
    """Format a date as 17.03.1994."""
    return value.strftime("%d.%m.%Y")


def _amount(value: Decimal) -> str:
    """Format an amount as 1234,50."""
    return f"{value:.2f}".replace(".", ",")


def price(gift: Gift) -> str:
    """Format the price range of a gift idea, empty without a price."""
    low, high, currency = gift.price_from, gift.price_to, gift.currency
    if low is not None and high is not None:
        if low == high:
            return f"{_amount(low)} {currency}"
        return f"{_amount(low)} bis {_amount(high)} {currency}"
    if low is not None:
        return f"ab {_amount(low)} {currency}"
    if high is not None:
        return f"bis {_amount(high)} {currency}"
    return ""


def category(value: GiftCategory) -> str:
    """German label of a gift category."""
    return CATEGORY_LABELS[value]


_templates = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[2] / "templates"),
    autoescape=select_autoescape(["html"]),
)
_templates.filters["german_date"] = german_date
_templates.filters["price"] = price
_templates.filters["category"] = category


@router.get(
    "",
    operation_id="getFullList",
    summary="Show complete list as HTML",
    description="Returns all people, gift ideas (with links and notes) and past gifts "
    "(giftings with status `given`) of the current account as one HTML page. All text is "
    "escaped; links are only http or https URLs. The page is meant to be shown in the "
    "browser or printed.",
    response_class=HTMLResponse,
    responses={
        200: {"content": {"text/html": {}}, "description": "Complete list as HTML."},
        **problem_responses(401),
    },
)
async def get_full_list(user: CurrentUser, session: SessionDep) -> HTMLResponse:
    """Render the current account's complete list as HTML."""
    full_list = await full_list_service.get_full_list(session, user.id)
    html = _templates.get_template("full_list.html").render(
        owner_name=full_list.owner_name,
        people=full_list.people,
        gifts=full_list.gifts,
        given=full_list.given,
    )
    return HTMLResponse(html)
