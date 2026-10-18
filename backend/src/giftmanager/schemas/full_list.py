"""Response body of the complete list endpoint (F-15)."""

from pydantic import BaseModel, Field

from giftmanager.schemas.gift import GiftOut
from giftmanager.schemas.gifting import GiftingOut
from giftmanager.schemas.link import LinkOut
from giftmanager.schemas.note import NoteOut
from giftmanager.schemas.person import PersonOut


class FullListGift(GiftOut):
    """A gift idea in the complete list, together with its links and notes."""

    links: list[LinkOut] = Field(
        description="Web links on the idea, oldest first.",
        examples=[
            [
                {
                    "id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a75",
                    "gift_id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70",
                    "label": "Thalia",
                    "url": "https://www.thalia.de/shop/home/artikeldetails/A1234",
                }
            ]
        ],
    )
    notes: list[NoteOut] = Field(
        description="Notes on the idea, oldest first.",
        examples=[
            [
                {
                    "id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a74",
                    "gift_id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70",
                    "label": "Größe",
                    "text": "M, eher weit",
                }
            ]
        ],
    )


class FullListOut(BaseModel):
    """The complete list of an account: people, gift ideas and past gifts (F-15)."""

    people: list[PersonOut] = Field(
        description="All people of the account, sorted by name.",
        examples=[
            [
                {
                    "id": "0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71",
                    "name": "Lena",
                    "birthday": "1994-03-17",
                    "relationship": "Schwester",
                    "notes": None,
                    "created_at": "2026-10-04T09:30:00Z",
                }
            ]
        ],
    )
    gifts: list[FullListGift] = Field(
        description="All gift ideas of the account with their links and notes, sorted by title.",
        examples=[[]],
    )
    given: list[GiftingOut] = Field(
        description="Past gifts: all giftings with status `given`, most recently given first.",
        examples=[[]],
    )
