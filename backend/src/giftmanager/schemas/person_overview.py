"""Response body of the person view (F-09)."""

from pydantic import BaseModel, Field

from giftmanager.schemas.common import Page
from giftmanager.schemas.gift import GiftOut
from giftmanager.schemas.gifting import GiftingOut
from giftmanager.schemas.occasion import OccasionOut
from giftmanager.schemas.task import TaskOut

_EMPTY_PAGE: dict[str, object] = {"items": [], "total": 0, "limit": 50, "offset": 0}


class OverviewGifting(GiftingOut):
    """A gifting in the person view, together with its tasks."""

    tasks: list[TaskOut] = Field(
        description="Tasks of the gifting, earliest due date first, tasks without one last.",
        examples=[
            [
                {
                    "id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a75",
                    "gifting_id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a73",
                    "title": "Karte schreiben",
                    "status": "open",
                    "due_on": "2026-12-20",
                    "created_at": "2026-10-04T09:30:00Z",
                }
            ]
        ],
    )


class PersonOverviewOut(BaseModel):
    """The person view (F-09). Every list is one page with the same `limit` and `offset`."""

    given: Page[OverviewGifting] = Field(
        description="Past gifts: giftings with status `given` the person received, latest "
        "`given_on` first.",
        examples=[_EMPTY_PAGE],
    )
    giftings: Page[OverviewGifting] = Field(
        description="Giftings for the person not given yet; `status` is the procurement "
        "state (`idea`, `planned` or `acquired`). Next occasion date first, those without "
        "one last.",
        examples=[_EMPTY_PAGE],
    )
    ideas: Page[GiftOut] = Field(
        description="Gift ideas meant for the person (possible recipient) without a gifting "
        "for them yet, newest first.",
        examples=[_EMPTY_PAGE],
    )
    occasions: Page[OccasionOut] = Field(
        description="Occasions that concern the person, sorted by date.",
        examples=[_EMPTY_PAGE],
    )
