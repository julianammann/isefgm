"""Gift suggestions (F-16) from category, price band and counts of all accounts only (Q-04)."""

import uuid
from decimal import Decimal

from sqlalchemy import ColumnElement, case, delete, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.errors import ConflictError
from giftmanager.models import (
    Gift,
    GiftCategory,
    Gifting,
    Person,
    PriceBand,
    Suggestion,
    SuggestionStatus,
)
from giftmanager.services import gift as gift_service
from giftmanager.services.ownership import get_owned, owned, paginate

MAX_SUGGESTIONS = 5
MIN_ACCOUNTS = 3
BAND_PRICES: dict[PriceBand, tuple[Decimal, Decimal | None]] = {
    PriceBand.UNDER_20: (Decimal("0.00"), Decimal("20.00")),
    PriceBand.FROM_20_TO_50: (Decimal("20.00"), Decimal("50.00")),
    PriceBand.FROM_50_TO_100: (Decimal("50.00"), Decimal("100.00")),
    PriceBand.OVER_100: (Decimal("100.00"), None),
}

type Feature = tuple[GiftCategory, PriceBand | None]


def _price_band() -> ColumnElement[str | None]:
    """Price band of a gift idea from the lower end of its range; null without a EUR price."""
    price = func.coalesce(Gift.price_from, Gift.price_to)
    return case(
        (or_(price.is_(None), Gift.currency != "EUR"), None),
        (price < 20, PriceBand.UNDER_20.value),
        (price < 50, PriceBand.FROM_20_TO_50.value),
        (price <= 100, PriceBand.FROM_50_TO_100.value),
        else_=PriceBand.OVER_100.value,
    )


def _feature(category: str, band: str | None) -> Feature:
    """Turn a category and band read from SQL into enum members."""
    return GiftCategory(category), PriceBand(band) if band is not None else None


async def _features_of_person(
    session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID
) -> set[Feature]:
    """Features the person already has: their ideas and the ideas of giftings for them."""
    used = select(Gifting.gift_id).where(Gifting.people.any(Person.id == person_id))
    rows = await session.execute(
        select(Gift.category, _price_band())
        .where(Gift.owner_id == owner_id)
        .where(or_(Gift.people.any(Person.id == person_id), Gift.id.in_(used)))
        .distinct()
    )
    return {_feature(category, band) for category, band in rows}


async def _decided_features(
    session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID
) -> set[Feature]:
    """Features already accepted or dismissed for the person; they are never suggested again."""
    rows = await session.execute(
        select(Suggestion.category, Suggestion.price_band).where(
            Suggestion.owner_id == owner_id,
            Suggestion.target_person_id == person_id,
            Suggestion.status != SuggestionStatus.OPEN,
        )
    )
    return {(category, band) for category, band in rows}


async def suggest_for_person(
    session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID
) -> list[Suggestion]:
    """Replace the person's open suggestions with features shared by MIN_ACCOUNTS accounts."""
    await get_owned(session, Person, owner_id, person_id)
    features = (
        select(Gift.owner_id, Gift.category, _price_band().label("price_band"))
        .where(Gift.category != GiftCategory.OTHER)
        .subquery()
    )
    rows = await session.execute(
        select(features.c.category, features.c.price_band, func.count())
        .group_by(features.c.category, features.c.price_band)
        .having(func.count(distinct(features.c.owner_id)) >= MIN_ACCOUNTS)
    )
    excluded = await _features_of_person(session, owner_id, person_id)
    excluded |= await _decided_features(session, owner_id, person_id)
    counts = [
        (feature, count)
        for category, price_band, count in rows
        if (feature := _feature(category, price_band)) not in excluded
    ]
    counts.sort(key=lambda item: (-item[1], item[0][0].value, item[0][1] or ""))

    await session.execute(
        delete(Suggestion).where(
            Suggestion.owner_id == owner_id,
            Suggestion.target_person_id == person_id,
            Suggestion.status == SuggestionStatus.OPEN,
        )
    )
    suggestions = [
        Suggestion(
            owner_id=owner_id,
            target_person_id=person_id,
            category=category,
            price_band=price_band,
            gift_count=count,
        )
        for (category, price_band), count in counts[:MAX_SUGGESTIONS]
    ]
    session.add_all(suggestions)
    await session.flush()
    return suggestions


async def list_suggestions(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    person_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Suggestion], int]:
    """Return one page of the owner's open suggestions, most frequent first, and the total."""
    stmt = owned(Suggestion, owner_id).where(Suggestion.status == SuggestionStatus.OPEN)
    if person_id is not None:
        stmt = stmt.where(Suggestion.target_person_id == person_id)
    return await paginate(
        session,
        stmt.order_by(Suggestion.gift_count.desc(), Suggestion.id),
        limit=limit,
        offset=offset,
    )


async def get_suggestion(
    session: AsyncSession, owner_id: uuid.UUID, suggestion_id: uuid.UUID
) -> Suggestion:
    """Return the owner's suggestion in any status."""
    return await get_owned(session, Suggestion, owner_id, suggestion_id)


async def _open_suggestion(
    session: AsyncSession, owner_id: uuid.UUID, suggestion_id: uuid.UUID
) -> Suggestion:
    """Return the owner's open suggestion; 404 if foreign, 409 if already decided."""
    suggestion = await get_owned(session, Suggestion, owner_id, suggestion_id)
    if suggestion.status is not SuggestionStatus.OPEN:
        raise ConflictError(f"Suggestion is already {suggestion.status.value}")
    return suggestion


async def accept_suggestion(
    session: AsyncSession, owner_id: uuid.UUID, suggestion_id: uuid.UUID, *, title: str
) -> Gift:
    """Turn an open suggestion into a gift idea for its person, priced by its band."""
    suggestion = await _open_suggestion(session, owner_id, suggestion_id)
    price_from, price_to = (
        BAND_PRICES[suggestion.price_band] if suggestion.price_band else (None, None)
    )
    gift = await gift_service.create_gift(
        session,
        owner_id,
        title=title,
        description=None,
        price_from=price_from,
        price_to=price_to,
        currency="EUR" if suggestion.price_band else None,
        category=suggestion.category,
        person_ids=[suggestion.target_person_id],
        occasion_ids=[],
    )
    suggestion.status = SuggestionStatus.ACCEPTED
    await session.flush()
    return gift


async def dismiss_suggestion(
    session: AsyncSession, owner_id: uuid.UUID, suggestion_id: uuid.UUID
) -> Suggestion:
    """Dismiss an open suggestion; its feature is never suggested for the person again."""
    suggestion = await _open_suggestion(session, owner_id, suggestion_id)
    suggestion.status = SuggestionStatus.DISMISSED
    await session.flush()
    return suggestion
