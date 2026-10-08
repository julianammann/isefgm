"""Giftings: concrete uses of a gift idea with their own status (F-06). No HTTP in here.

A gifting has no owner_id; it belongs to the account of its gift idea. The Q-01 helpers
`owned()` and `get_owned()` need an owner_id (Protocol `Owned`), so this module scopes its
own queries through gift.owner_id. `paginate()` and `get_all_owned()` still apply.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Gifting, GiftingStatus

# TODO(F-06): Owner scope, used by every read below (README: never select(Gifting) unscoped):
#   def _owned_giftings(owner_id) -> Select[tuple[Gifting]]:
#       return select(Gifting).join(Gifting.gift).where(Gift.owner_id == owner_id)
#   Add it together with its first caller; pyright strict flags an unused private function.


async def list_giftings(
    session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Gifting], int]:
    """Return one page of the owner's giftings, newest first, and the total count."""
    # TODO(F-06): paginate(session, _owned_giftings(owner_id).order_by(...), ...).
    #   Order by created_at desc, then id desc: giftings saved in one transaction share
    #   created_at, the UUIDv7 breaks the tie (see list_gifts).
    raise NotImplementedError


async def get_gifting(session: AsyncSession, owner_id: uuid.UUID, gifting_id: uuid.UUID) -> Gifting:
    """Return the owner's gifting.

    Raises:
        NotFoundError: The gifting does not exist or belongs to another account.
    """
    # TODO(F-06): session.scalar(_owned_giftings(owner_id).where(Gifting.id == gifting_id));
    #   None -> raise NotFoundError("Gifting not found"). Same message for "missing" and
    #   "foreign" (Q-01, README rule 3).
    raise NotImplementedError


async def create_gifting(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gift_id: uuid.UUID,
    status: GiftingStatus,
    person_ids: list[uuid.UUID],
    occasion_id: uuid.UUID | None,
    occasion_date: date | None,
    given_on: date | None,
) -> Gifting:
    """Create a gifting of one of the owner's gift ideas, in one step (QZ-01).

    Raises:
        NotFoundError: The idea, a person or the occasion does not exist or belongs to
            another account.
    """
    # TODO(F-06): Three steps.
    #   1. Resolve everything the gifting refers to, before adding anything:
    #      gift = get_owned(session, Gift, owner_id, gift_id)
    #      people = get_all_owned(session, Person, owner_id, person_ids)
    #      occasion = get_owned(session, Occasion, owner_id, occasion_id) if one is given
    #   2. Gifting(gift=gift, status=..., people=people, occasion=occasion, ...),
    #      session.add, session.flush().
    #   3. session.refresh(gifting, ["people"]) so the recipients come back in the
    #      relationship's order (see _reload_links in services/gift.py).
    #   The completeness of `given` is already checked by GiftingIn.
    raise NotImplementedError


async def update_gifting(
    session: AsyncSession,
    owner_id: uuid.UUID,
    gifting_id: uuid.UUID,
    *,
    gift_id: uuid.UUID,
    status: GiftingStatus,
    person_ids: list[uuid.UUID],
    occasion_id: uuid.UUID | None,
    occasion_date: date | None,
    given_on: date | None,
) -> Gifting:
    """Replace all editable fields and recipients of the owner's gifting.

    Raises:
        NotFoundError: The gifting, the idea, a person or the occasion does not exist or
            belongs to another account.
    """
    # TODO(F-06): get_gifting first, then resolve gift, people and occasion like in
    #   create_gifting, and only then assign the fields. A foreign or unknown id must leave
    #   the gifting untouched (test_records_of_another_account_cannot_be_used[PUT-...]).
    #   flush, then refresh people.
    raise NotImplementedError


async def delete_gifting(session: AsyncSession, owner_id: uuid.UUID, gifting_id: uuid.UUID) -> None:
    """Delete the owner's gifting; the idea, people and occasion stay."""
    # TODO(F-06): get_gifting, session.delete, session.flush (like delete_gift).
    raise NotImplementedError


async def is_gift_in_use(session: AsyncSession, gift_id: uuid.UUID) -> bool:
    """Return whether any gifting uses the gift idea."""
    # TODO(F-06): bool(await session.scalar(select(exists().where(Gifting.gift_id == ...))))
    #   No owner filter needed: the caller already holds the owner's gift.
    #   Used by delete_gift (services/gift.py) for the 409.
    raise NotImplementedError


async def is_occasion_in_use(session: AsyncSession, occasion_id: uuid.UUID) -> bool:
    """Return whether any gifting refers to the occasion."""
    # TODO(F-06): Like is_gift_in_use, on Gifting.occasion_id. Used by delete_occasion and
    #   delete_birthday (services/occasion.py) and update_person (services/person.py).
    raise NotImplementedError
